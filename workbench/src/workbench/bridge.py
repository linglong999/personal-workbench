"""HTTP Bridge：把 workbench 的 5 个 MCP 工具暴露给前端 Console（LIVE 模式）。

浏览器无法直连 MCP（stdio 协议），本模块以 FastAPI 提供同构的 HTTP 端点：
端点与 mcp_server.create_server 中的 5 个工具一一对应，业务逻辑完全复用
同一套组件（vault / vector / classifier / reviewer / coach），不改后端本身。

启动（cwd=workbench）：
    set PYTHONPATH=src
    python -m uvicorn workbench.bridge:app --port 8213
或：
    python -m workbench.bridge
"""

import json
import os
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from workbench import usage
from workbench.ai.agents import ClassifierAgent, CoachAgent, ReviewerAgent
from workbench.ai.engine import AIEngine
from workbench.ai.llm import LLMClient
from workbench.auth.service import AuthService
from workbench.config import load_config
from workbench.knowledge.vault import VaultStore
from workbench.knowledge.vector import VectorStore

cfg = load_config()
llm = LLMClient(
    cfg.llm_base_url,
    cfg.llm_api_key,
    cfg.llm_model,
    cfg.llm_price_in_per_m,
    cfg.llm_price_out_per_m,
)
engine = AIEngine(llm)
vector = VectorStore(cfg.chroma_dir)
vault = VaultStore(cfg.vault_path)
classifier = ClassifierAgent(engine)
reviewer = ReviewerAgent(engine)
coach = CoachAgent(engine, vector)

# JWT secret：优先复用 LLM key（本地单用户）；无 key 用固定开发 secret（仅本地自用形态，
# 见 ADR-0001 D2/D3）。短 key（<32B，如 CI 的 sk-test）拼接补足，避免 InsecureKeyLengthWarning。
_FALLBACK_SECRET = b"dev-secret-change-me-local-only-000000"
_key = cfg.llm_api_key.encode("utf-8")[:64]
_AUTH_SECRET = _key if len(_key) >= 32 else (_key + _FALLBACK_SECRET)[:64]
auth_service = AuthService(db_path=str(Path(".data/app.db").resolve()), secret=_AUTH_SECRET)

bearer = HTTPBearer(auto_error=False)


def require_auth(cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    """业务端点统一鉴权：校验走 auth_service（secret 单源，可被测试替换）。"""
    if cred is None:
        raise HTTPException(status_code=401, detail="missing token")
    try:
        payload = auth_service.verify_token(cred.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid token")
    return {"sub": payload["sub"]}


app = FastAPI(title="workbench-bridge", version="0.1.0")
# 前端 Console 运行在 http://127.0.0.1:8212，跨端口需要 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observe_calls(request: Request, call_next):
    """每次 /api/* 调用都记录：工具名、输入摘要、耗时、本次触发的 LLM token 增量。"""
    path = request.url.path
    # usage 查询与 auth 端点不记观测：前者是观测本身，后者非业务调用（避免噪音）
    skip = path == "/api/usage" or path.startswith("/api/auth/")
    body_head = ""
    if path.startswith("/api/") and not skip and request.method == "POST":
        raw = await request.body()
        body_head = raw.decode("utf-8", errors="replace")[:120]
    before = usage.snapshot()
    start = time.time()
    response = await call_next(request)
    if path.startswith("/api/") and not skip:
        usage.record_tool(
            path.replace("/api/", ""),
            body_head,
            before,
            usage.snapshot(),
            int((time.time() - start) * 1000),
            response.status_code < 400,
        )
    return response


class SearchReq(BaseModel):
    query: str
    top_k: int = 5


class NoteReq(BaseModel):
    folder: str
    title: str
    content: str


class TextReq(BaseModel):
    text: str


class TaskReq(BaseModel):
    task: str
    top_k: int = 5


@app.get("/api/health")
def health():
    return {"ok": True, "model": cfg.llm_model}


def _obsidian_uri(abs_path: str) -> str:
    """Obsidian 官方 URI：obsidian://open?vault=库名&file=库内相对路径。
    前端点击即唤起 Obsidian 打开该笔记。"""
    if not abs_path:
        return ""
    try:
        p = Path(abs_path).resolve()
        reg = _registered_vault_for(p)
        if reg:
            name, root = reg
            rel = p.relative_to(root.resolve()).as_posix()
            return f"obsidian://open?vault={quote(name)}&file={quote(rel)}"
        # 回退：VAULT_PATH 自身即库根（未注册/注册表不可读时）
        rel = p.relative_to(vault.root.resolve()).as_posix()
        return f"obsidian://open?vault={quote(vault.root.name)}&file={quote(rel)}"
    except ValueError:
        return ""


def _registry_path() -> Path:
    """Obsidian 全局注册表 obsidian.json 位置（win / mac / linux）。"""
    import sys

    if sys.platform == "win32" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "obsidian" / "obsidian.json"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/obsidian/obsidian.json"
    return Path.home() / ".config/obsidian/obsidian.json"


_vault_registry = None


def _registered_vault_for(p: Path) -> tuple[str, Path] | None:
    """在 Obsidian 注册的 vault 中找包含 p 的那个 → (库名, 库根)。
    关键：VAULT_PATH 可能只是库内子目录（如 Obsidian Vault/玲珑de知识库），
    URI 的 vault= 参数必须是注册表里的真库名，否则 Obsidian 报 vault not found。"""
    global _vault_registry
    if _vault_registry is None:
        entries: list[tuple[str, Path]] = []
        try:
            data = json.loads(_registry_path().read_text(encoding="utf-8"))
            for meta in data.get("vaults", {}).values():
                vp = meta.get("path", "")
                if vp:
                    entries.append((Path(vp).name, Path(vp)))
        except (OSError, json.JSONDecodeError, ValueError):
            pass
        _vault_registry = entries
    for name, root in _vault_registry:
        try:
            p.relative_to(root.resolve())
            return name, root
        except ValueError:
            continue
    return None


@app.post("/api/search_knowledge")
def api_search(req: SearchReq, _: dict = Depends(require_auth)):
    """对应 MCP 工具 search_knowledge（每条结果附 obsidian_uri，可点开原笔记）。"""
    results = []
    for r in vector.search(req.query, req.top_k):
        r["obsidian_uri"] = _obsidian_uri(r.get("path", ""))
        results.append(r)
    return {"results": results}


@app.post("/api/list_tags")
def api_list_tags(_: dict = Depends(require_auth)):
    """聚合 Vault 知识卡片的 frontmatter tags → {tag: [{title, path, obsidian_uri}]}。"""
    tags = vault.list_tags()
    for entries in tags.values():
        for e in entries:
            e["obsidian_uri"] = _obsidian_uri(e["path"])
    return {"tags": tags}


@app.get("/api/usage")
def api_usage(_: dict = Depends(require_auth)):
    """调用观测：工具调用 + LLM token 用量 + 成本估算（前端「用量」页）。"""
    return usage.report()


@app.post("/api/create_note")
def api_create_note(req: NoteReq, _: dict = Depends(require_auth)):
    """对应 MCP 工具 create_note（写入 VAULT_PATH 白名单目录，并同步向量库）。"""
    path = vault.create_note(req.folder, req.title, req.content)
    vector.add(f"note-{path.stem}", req.title, req.content, path=str(path))
    return {"path": str(path), "indexed": True, "obsidian_uri": _obsidian_uri(str(path))}


@app.post("/api/classify_text")
def api_classify(req: TextReq, _: dict = Depends(require_auth)):
    """对应 MCP 工具 classify_text（真实 LLM 分类）。"""
    return {"label": classifier.classify(req.text)}


@app.post("/api/scan_decision_closed_loop")
def api_scan(_: dict = Depends(require_auth)):
    """对应 MCP 工具 scan_decision_closed_loop。"""
    return {"missing": reviewer.scan_closed_loop(vault)}


@app.post("/api/reopen_task")
def api_reopen(req: TaskReq, _: dict = Depends(require_auth)):
    """对应 MCP 工具 reopen_task（Coach 递送历史经验）。"""
    return {"results": coach.recall_for_task(req.task, req.top_k)}


class AuthReq(BaseModel):
    username: str
    password: str


@app.post("/api/auth/register")
def api_register(req: AuthReq):
    try:
        token = auth_service.register(req.username, req.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"token": token}


@app.post("/api/auth/login")
def api_login(req: AuthReq):
    try:
        token = auth_service.login(req.username, req.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"token": token}


@app.get("/api/auth/me")
def api_me(user: dict = Depends(require_auth)):
    return {"username": user["sub"]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8213)
