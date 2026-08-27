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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from workbench.config import load_config
from workbench.ai.llm import LLMClient
from workbench.ai.engine import AIEngine
from workbench.ai.agents import ClassifierAgent, ReviewerAgent, CoachAgent
from workbench.knowledge.vault import VaultStore
from workbench.knowledge.vector import VectorStore

cfg = load_config()
llm = LLMClient(cfg.llm_base_url, cfg.llm_api_key, cfg.llm_model)
engine = AIEngine(llm)
vector = VectorStore(cfg.chroma_dir)
vault = VaultStore(cfg.vault_path)
classifier = ClassifierAgent(engine)
reviewer = ReviewerAgent(engine)
coach = CoachAgent(engine, vector)

app = FastAPI(title="workbench-bridge", version="0.1.0")
# 前端 Console 运行在 http://127.0.0.1:8212，跨端口需要 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.post("/api/search_knowledge")
def api_search(req: SearchReq):
    """对应 MCP 工具 search_knowledge。"""
    return {"results": vector.search(req.query, req.top_k)}


@app.post("/api/create_note")
def api_create_note(req: NoteReq):
    """对应 MCP 工具 create_note（写入 VAULT_PATH 白名单目录）。"""
    path = vault.create_note(req.folder, req.title, req.content)
    return {"path": str(path)}


@app.post("/api/classify_text")
def api_classify(req: TextReq):
    """对应 MCP 工具 classify_text（真实 LLM 分类）。"""
    return {"label": classifier.classify(req.text)}


@app.post("/api/scan_decision_closed_loop")
def api_scan():
    """对应 MCP 工具 scan_decision_closed_loop。"""
    return {"missing": reviewer.scan_closed_loop(vault)}


@app.post("/api/reopen_task")
def api_reopen(req: TaskReq):
    """对应 MCP 工具 reopen_task（Coach 递送历史经验）。"""
    return {"results": coach.recall_for_task(req.task, req.top_k)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8213)
