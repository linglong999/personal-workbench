# 个人工作台 · 全面迭代实施计划（M0 → M4）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将个人工作台从「可运行脚本」升级为「可构建、可鉴权、可扩展、可部署的规范化工程」，并完成 M0–M4 的既定功能迭代。

**架构：** 分层 + 模块边界范式。Python 后端（FastAPI Bridge + MCP）与 React/Vite 前端分离，各自通过定义良好的接口通信，CI 全门禁保证「提交即可信」。

**Tech Stack：** Python 3.10 · FastAPI · FastMCP · ChromaDB · SQLite(JWT, 方案A) · React · Vite · GridStack.js

**计划纪律：** 本文档为**唯一统一计划文件**。M0–M4 各里程碑计划全部收敛在此文件，按里程碑分节。**只在全部里程碑（M0–M4）计划都讨论定稿后统一执行，执行时逐任务 TDD + 频繁提交。**

> 关联 spec：`docs/superpowers/specs/2026-09-01-workbench-m0-engineering-design.md`

***

## 执行次序总览

按里程碑推进，每个里程碑内部按批次顺序做，**每批独立 commit、独立验收，不做完下一批**：

```
B0 后端规范 → B1 后端认证 → B2 React 化 → B3 外壳 → B4 前端认证 → B5 Widget 壳
───────────────────────── M0 ─────────────────────────
→ M1 → M2 → M3 → M4（各里程碑计划在下方对应分节，讨论定稿后填充）
```

> 依赖说明：B1（后端认证）先于 B4（前端认证入口）——先有后端端点，前端才能接。B3/B5 依赖 B2（React 工程）。B1 的鉴权加在业务端点上，会**先于**前端 B4，因此在 B2 React 迁移期间，`request()` 尚未带 token；B2 的 MOCK 模式不受影响，LIVE 模式在 B4 完成前访问受保护端点会 401——**这是预期**，B4 补齐 token 后闭合。

***

## M0 · 工程化 + React 重写

### M0 · 范围界定与已登记排除项（通读封板补录，防止丢失）

**M0 本版做：** B0–B5 六批（规范/认证/React 化/外壳/前端认证/widget 壳）。

**M0 明确不做、但已登记待后续（不在 M0，也不丢弃）：**

- [ ] **Docker 部署**：已取消"公网/Docker"规划（用户拍板：开源后用户下载源码自用、走本地流程，不做公网形态）。Docker Desktop 用户仍可 Self-host，但**本计划不为公网/Docker 做交付物**；如需本地容器化演示另立任务。

- [ ] **服务健康灯 widget**：早期候选（homelab-dashboard 印象），M0-B5 只搭 widget 容器接口，健康灯数据源留后续。

- [ ] **Web 终端 widget**：homelab-dashboard 印象，M0 排除，留后续。

- [ ] L1「常驻观察代理(主动 watch)」：主动预警机制，M0/M1 排除，见 M2/M3 决策（实际落为 M3 决策辅助的参照来源思考，主动预警仍列为扩展）。

- [ ] Widget 真实数据源（天气/日历/RSS/行情/服务健康）：M0-B5 只搭壳，数据源接入留 M4 以后（外部数据在 M4-B 登记为候选 2）。

- [ ] 运行型指标 / 更重观测栈：见 M4 末尾"M4 · 已登记扩展"。

> 这些"已排除但登记"项确保：当初与用户讨论过的扩展（Docker、公网、Web 终端、健康灯、外部数据源、主动观察、运行型指标）**全部留有记录，不因 M0 未包含而丢失**。

### M0-B0 · 后端工程规范（ruff / mypy / coverage / CI / ADR）

**Files:**

- Modify: `workbench/pyproject.toml`

- Create: `workbench/pyproject.toml`（更新 dev 依赖）

- Create: `.github/workflows/ci.yml`

- Create: `docs/ADRs/2026-09-01-0001-layered-architecture.md`

- Create: `docs/architecture/index.md`

- Create: `CHANGELOG.md`

- [ ] **Step 1: 更新 pyproject.toml，加入 dev 工具**

编辑 `workbench/pyproject.toml`，将 `[project.optional-dependencies].dev` 与新增 `[tool.ruff]`、`[tool.mypy]`、`[tool.coverage]` 配置补齐：

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.1",
    "ruff>=0.5",
    "mypy>=1.10",
]

[tool.ruff]
line-length = 100
target-version = "py310"
src = ["src"]

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.10"
mypy_path = "src"
warn_unused_ignores = true
follow_imports = "normal"
# src 主路径严格检查，test 目录放宽
[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
ignore_errors = true

[tool.coverage.run]
source = ["src/workbench"]
omit = ["src/workbench/__main__.py"]

[tool.coverage.report]
fail_under = 85
```

- [ ] **Step 2: 安装并运行 ruff 验证基线**

Run（cwd=workbench）:

```
pip install -e ".[dev]"
ruff check src tests
ruff format --check src tests
```

Expected: ruff 若报现有风格问题，先格式化。目标通过（或记录已知豁免）。

- [ ] **Step 3: 运行 mypy 验证基线**

Run（cwd=workbench）:

```
mypy src
```

Expected: 无阻塞错误。若有小问题，修正类型标注。

- [ ] **Step 4: 运行覆盖率并确认 ≥85%**

Run（cwd=workbench）:

```
pytest --cov --cov-report=term-missing
```

Expected: Total coverage ≥85%。

- [ ] **Step 5: 创建 GitHub Actions CI 工作流**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: workbench
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - name: Install
        run: pip install -e ".[dev]"
      - name: Lint
        run: ruff check src tests
      - name: Type check
        run: mypy src
      - name: Test + Coverage
        run: pytest --cov --cov-report=term-missing
        env:
          VAULT_PATH: "."
          LLM_BASE_URL: "http://localhost:1/v1"
          LLM_API_KEY: "sk-test"
          LLM_MODEL: "test"
  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: workbench-console
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Install
        run: npm ci
      - name: Build
        run: npm run build
      - name: Lint
        run: npm run lint
```

> 注：frontend job 依赖 B2 完成的 package.json；若先跑，此 job 暂可置 `comment` 或待 B2 后生效。

- [ ] **Step 6: 创建 ADR-0001 分层架构**

Create `docs/ADRs/2026-09-01-0001-layered-architecture.md`，记录：分层范式（backend/frontend/模块边界）、JWT 方案 A、取消公网/Docker 的决策与理由、SQLite 选型。

- [ ] **Step 7: 创建架构 index 与 CHANGELOG**

Create `docs/architecture/index.md`（含分层图，与 spec 一致）。
Create `CHANGELOG.md`（起始条目：`## [0.2.0] - 2026-09-01`，新增 M0 工程规范）。

- [ ] **Step 8: Commit**

```bash
git add workbench/pyproject.toml .github docs CHANGELOG.md
git commit -m "build(workbench): M0-B0 工程规范——ruff/mypy/coverage85%/CI/ADR"
```

### M0-B1 · 后端认证（SQLite + JWT 方案 A）

**Files:**

- Create: `workbench/src/workbench/auth/repository.py`

- Create: `workbench/src/workbench/auth/service.py`

- Create: `workbench/src/workbench/auth/schemas.py`

- Create: `workbench/src/workbench/auth/__init__.py`

- Create: `workbench/tests/test_auth.py`

- Modify: `workbench/pyproject.toml`（加 `pyjwt`、`bcrypt`）

- Modify: `workbench/src/workbench/bridge.py`（挂载 auth 路由 + 鉴权依赖）

- Modify: `workbench/tests/test_bridge.py`（新增鉴权保护测试）

- [ ] **Step 1: 更新依赖**

Add to `workbench/pyproject.toml` `[project].dependencies`:

```
"PyJWT>=2.8",
"bcrypt>=4.0",
```

- [ ] **Step 2: Write failing test — 用户仓储 CRUD**

Create `workbench/tests/test_auth.py`:

```python
import pytest
from pathlib import Path
from workbench.auth.repository import UserRepository
from workbench.auth.service import AuthService, hash_password, verify_password


@pytest.fixture()
def db(tmp_path):
    return str(tmp_path / "auth.db")


def test_hash_and_verify():
    h = hash_password("secret123")
    assert h != "secret123"
    assert verify_password("secret123", h)
    assert not verify_password("wrong", h)


def test_repo_create_get(db):
    repo = UserRepository(db)
    repo.create_user("alice", hash_password("pw"))
    u = repo.get_by_username("alice")
    assert u is not None and u.username == "alice"
    assert u.password_hash != "pw"


def test_repo_duplicate_username(db):
    repo = UserRepository(db)
    repo.create_user("bob", hash_password("pw"))
    with pytest.raises(ValueError):
        repo.create_user("bob", hash_password("pw2"))


def test_auth_register_login(db):
    svc = AuthService(db, secret=b"test-secret", ttl_seconds=3600)
    token = svc.register("carol", "pw12345")
    assert isinstance(token, str) and token
    me = svc.authenticate("carol", "pw12345")
    assert me.username == "carol"


def test_auth_wrong_password(db):
    svc = AuthService(db, secret=b"test-secret")
    svc.register("dave", "pw12345")
    with pytest.raises(ValueError):
        svc.authenticate("dave", "badpw")
```

- [ ] **Step 3: Run to verify fail**

Run（cwd=workbench）: `python -m pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'workbench.auth'`

- [ ] **Step 4: Write minimal implementation**

Create `workbench/src/workbench/auth/__init__.py`:

```python
"""认证子系统：SQLite 用户存储 + JWT（方案 A）。"""
```

Create `workbench/src/workbench/auth/repository.py`:

```python
"""SQLite 用户仓储。"""
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class User:
    id: int
    username: str
    password_hash: str


class UserRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )

    def create_user(self, username: str, password_hash: str) -> User:
        with self._connect() as conn:
            try:
                cur = conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                raise ValueError(f"username already exists: {username}")
            user = User(id=cur.lastrowid, username=username, password_hash=password_hash)
            return user

    def get_by_username(self, username: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if row is None:
                return None
            return User(id=row["id"], username=row["username"], password_hash=row["password_hash"])
```

Create `workbench/src/workbench/auth/service.py`:

```python
"""认证业务：bcrypt 哈希 + JWT 签发/校验。"""
import datetime as dt
import uuid
from dataclasses import dataclass

import bcrypt
import jwt

from workbench.auth.repository import UserRepository, User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


@dataclass
class AuthService:
    db_path: str
    secret: bytes
    ttl_seconds: int = 3600

    def __post_init__(self):
        self.repo = UserRepository(self.db_path)

    def _issue(self, username: str) -> str:
        now = dt.datetime.now(dt.timezone.utc)
        payload = {
            "sub": username,
            "iat": now,
            "exp": now + dt.timedelta(seconds=self.ttl_seconds),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def register(self, username: str, password: str) -> str:
        if len(password) < 6:
            raise ValueError("password too short (min 6)")
        self.repo.create_user(username, hash_password(password))
        return self._issue(username)

    def authenticate(self, username: str, password: str) -> User:
        user = self.repo.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise ValueError("invalid credentials")
        return user

    def login(self, username: str, password: str) -> str:
        self.authenticate(username, password)
        return self._issue(username)
```

- [ ] **Step 5: Run to verify pass**

Run（cwd=workbench）: `python -m pytest tests/test_auth.py -v`
Expected: PASS — all 6 tests green.

- [ ] **Step 6: 在 bridge 挂载认证端点 + 鉴权依赖**

Modify `workbench/src/workbench/bridge.py`：顶部加 import 与依赖注入，并新增路由。编辑关键片段：

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt as pyjwt
from workbench.auth.service import AuthService

# cfg 已存在；新增 auth 服务（secret 从配置读取）
_AUTH_SECRET = getattr(cfg, "llm_api_key", "").encode("utf-8") or b"dev-secret-change-me"
auth_service = AuthService(db_path=str(Path(".data/app.db").resolve()), secret=_AUTH_SECRET)

bearer = HTTPBearer(auto_error=False)


def require_auth(cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if cred is None:
        raise HTTPException(status_code=401, detail="missing token")
    try:
        payload = pyjwt.decode(cred.credentials, _AUTH_SECRET, algorithms=["HS256"])
        return {"sub": payload["sub"]}
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid token")
```

新增路由（放在已有路由后）:

```python
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
```

> 注意：桥接中间件 `observe_calls` 会对这些 POST 记 usage，属可接受；若需排除可在 skip 列表加 `/api/auth/`。

- [ ] **Step 7: Write failing test — 鉴权保护端点**

Create `workbench/tests/test_bridge.py`:

```python
from fastapi.testclient import TestClient
from workbench.bridge import app

client = TestClient(app)


def test_unauthenticated_blocked():
    r = client.post("/api/search_knowledge", json={"query": "x"})
    assert r.status_code == 401


def test_register_login_me_flow(tmp_path, monkeypatch):
    # 用独立 db 避免污染真实数据目录
    import workbench.bridge as bridge
    monkeypatch.setattr(bridge, "auth_service", bridge.AuthService(str(tmp_path / "a.db"), secret=b"s"))
    r = client.post("/api/auth/register", json={"username": "u1", "password": "pw12345"})
    assert r.status_code == 200
    token = r.json()["token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "u1"
```

> 注：`test_unauthenticated_blocked` 依赖 `/api/*` 端点已挂 `Depends(require_auth)`。**鉴权范围界定（通读封板确认，自洽）：** `/api/health`、`/api/auth/*` 一律放行；**全部业务端点**（含现有 `search_knowledge / create_note / classify_text / scan_decision_closed_loop / reopen_task`，以及 M4 以后新增的统计端点 `/api/vault/*`、`/api/chroma/stats`、`/api/llm/usage`、`/api/llm/cost`）默认都纳入鉴权。`/api/usage` 亦纳入鉴权（B4 前端登录后自动带 token 闭合；B4 完成前 LIVE 模式访问受保护端点返回 401，属预期，见"执行次序总览"依赖说明）。这与"业务端点一律鉴权、健康/认证端点放行"的单一规则一致。

- [ ] **Step 8: Run test，修复业务端点鉴权**

Run（cwd=workbench）: `python -m pytest tests/test_bridge.py -v`
Expected: 若 401 未按预期，为 5 个业务端点补 `Depends(require_auth)`。最终 PASS。

- [ ] **Step 9: Run 全量测试 + coverage**

Run（cwd=workbench）: `python -m pytest --cov --cov-report=term-missing`
Expected: 全量通过，coverage ≥85%。

- [ ] **Step 10: Commit**

```bash
git add workbench/src/workbench/auth workbench/tests/test_auth.py workbench/tests/test_bridge.py workbench/pyproject.toml
git commit -m "feat(auth): M0-B1 SQLite 用户存储 + JWT 登录注册 + Bridge 鉴权"
```

### M0-B2 · 前端 React 化（Vite + React 脚手架 + 视图迁移）

**背景**：`workbench-console` 现为纯静态（`index.html` + `assets/app.js` \~26KB + `app.css`）。B2 将其迁为 Vite+React 工程，**功能等价迁移**（不丢能力），新增功能留给 M0-B3/B4。

**Files（新建 Vite 工程）:**

- Create: `workbench-console/package.json`

- Create: `workbench-console/vite.config.js`

- Create: `workbench-console/index.html`（重写为 React 挂载点）

- Create: `workbench-console/src/main.jsx`

- Create: `workbench-console/src/App.jsx`

- Create: `workbench-console/src/api/client.js`

- Create: `workbench-console/src/views/`（InboxView / TodayView / ProjectView / ReviewView / KnowledgeView / TagsView / SearchView / UsageView / SettingsView）

- Create: `workbench-console/src/components/`（InputBar / CommandPalette / Sidebar / ContextPanel / AIConfirmModal / CardMarquee / Toast）

- Create: `workbench-console/src/style/theme.css`（白·墨·金 token）

- Delete: `workbench-console/assets/app.js`（代码迁入组件后移除）

- Keep: `workbench-console/assets/app.css`（迁移为 token 基础）

- [ ] **Step 1: 初始化 Vite + React 工程**

在 `workbench-console/` 下创建 `package.json`:

```json
{
  "name": "workbench-console",
  "private": true,
  "version": "0.2.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext .jsx,.js"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.4.0",
    "eslint": "^8.57.0",
    "@eslint/js": "^9.0.0",
    "eslint-plugin-react": "^7.34.0",
    "eslint-plugin-react-hooks": "^4.6.0"
  }
}
```

创建 `vite.config.js`:

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 8212 },
  base: './',
})
```

- [ ] **Step 2: 创建挂载与入口**

Create `workbench-console/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>个人工作台</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

Create `workbench-console/src/main.jsx`:

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './style/theme.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 3: 建 API 客户端（保留 MOCK/LIVE 切换）**

Create `workbench-console/src/api/client.js`（等价迁移现有 `app.js` 的 fetch/MOCK 逻辑）:

```js
const BASE = 'http://127.0.0.1:8213'
const MODE_KEY = 'wb-mode'

export function getMode() {
  return localStorage.getItem(MODE_KEY) || 'MOCK'
}
export function setMode(m) {
  localStorage.setItem(MODE_KEY, m)
}

async function call(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// MOCK 数据占位（bridge 关闭时降级）
const MOCK = { search_knowledge: { results: [] }, list_tags: { tags: [] } }

export async function request(path, body) {
  if (getMode() === 'MOCK') return MOCK[path] ?? {}
  return call(path, body) // LIVE 时带 token（B4 加 Authorization 头）
}
```

> 说明：B4 会在此处注入 JWT —— 届时 `call` 的 headers 增 `Authorization: Bearer <token>`，从 `localStorage('wb-token')` 读取。本步先留接口。

- [ ] **Step 4: 迁移视图与组件（等价复刻）**

按现有功能 1:1 迁移，每个视图/组件一个文件。核心迁移点（实现方式从 `assets/app.js` 逐项改写为组件）：

- `InputBar` → 输入条 + 落盘（`POST /api/create_note`）+ 向量同步

- `InboxView` → 收件箱 / 分类归位规则（`ruleFor`/`folderFor` 复制）

- `TodayView` → 今天

- `ProjectView` → 项目行动

- `ReviewView` → 复盘

- `KnowledgeView` → 知识视图

- `TagsView` → 标签浏览（提取 Vault frontmatter tags）

- `SearchView` → 检索（`POST /api/search_knowledge`）

- `UsageView` → 用量观测（`GET /api/usage`）

- `SettingsView` → 设置 + MOCK/LIVE 切换

- `CommandPalette` → Ctrl+K 命令面板

- `ContextPanel` → 右侧上下文面板

- `AIConfirmModal` → AI 待确认弹层

- `CardMarquee` → 卡片跑马灯

- `Toast` → 提示

> **占位交代**：因每个文件迁移代码量大且本计划待 M0–M4 讨论完才执行，迁移期每个组件按上述职责单文件实现，执行时以 `assets/app.js` 现有逻辑为蓝本逐块移植，**确保零回归**（既有 4 轮自测坑进回归清单）。此步骤按"每组件一格 task"在真正实现阶段拆细；此处先锁定文件结构与迁移清单。

- [ ] **Step 5: 迁移设计系统为 token**

Create `workbench-console/src/style/theme.css`，将现有白·墨·金提取为 CSS 变量：

```css
:root {
  --paper: #f4f1ea;
  --ink: #1f2430;
  --gold: #b88a3e;
  --paper-cloud: #ece7dc;
  --muted: #8b8577;
  --line: #ddd6c8;
  --accent: #c0392b;
}
```

（其余样式沿用 `assets/app.css` 迁移为组件级 CSS。）

- [ ] **Step 6: Build + lint 通过**

Run（cwd=workbench-console）:

```
npm install
npm run build
npm run lint
```

Expected: build 产出 `dist/`，lint 无 error。

- [ ] **Step 7: 回归验收（零回归）**

以既有自测清单（含 Obsidian URI 直开、输入落盘、MOCK/LIVE 降级、标签聚合）启动 `npm run dev`（:8212）+ Bridge（:8213）人工逐条走查。List all must-pass in regression.md（可选，执行时产出）。

- [ ] **Step 8: Commit（移除旧 app.js，保留 app.css 作样式基座）**

```bash
git add workbench-console
git rm workbench-console/assets/app.js
git commit -m "refactor(console): M0-B2 迁移为 React+Vite，功能等价、零回归"
```

### M0-B3 · L2 外壳新功能（GridStack 拖拽 / 布局保存 / 多主题 / 命令搜索）

**背景**：在 React 化基础上升级外壳，使其具备 Dashboard 特性（对齐 Dashy 式风格）。这些是**新增**能力，不改已有功能语义。

**Files:**

- Create: `workbench-console/src/shell/GridShell.jsx`

- Create: `workbench-console/src/shell/layout.js`（layout 读写 `localStorage('wb-layout')`）

- Create: `workbench-console/src/theme/ThemeProvider.jsx`（多主题）

- Create: `workbench-console/src/theme/themes.js`

- Modify: `workbench-console/src/App.jsx`（引入 GridShell + ThemeProvider）

- Modify: `workbench-console/src/components/CommandPalette.jsx`（增强命令搜索）

- [ ] **Step 1: 安装 GridStack**

Run（cwd=workbench-console）:

```
npm install gridstack
```

- [ ] **Step 2: 布局读写模块**

Create `workbench-console/src/shell/layout.js`:

```js
const LAYOUT_KEY = 'wb-layout'

export function loadLayout() {
  try {
    return JSON.parse(localStorage.getItem(LAYOUT_KEY))
  } catch {
    return null
  }
}

export function saveLayout(l) {
  localStorage.setItem(LAYOUT_KEY, JSON.stringify(l))
}
```

- [ ] **Step 3: Create GridShell（拖拽 + 缩放 + 自动保存）**

Create `workbench-console/src/shell/GridShell.jsx`:

```jsx
import React, { useEffect, useRef } from 'react'
import { GridStack } from 'gridstack'
import 'gridstack/dist/gridstack.min.css'
import { loadLayout, saveLayout } from './layout.js'

export default function GridShell({ children }) {
  const ref = useRef(null)

  useEffect(() => {
    const grid = GridStack.init({
      cellHeight: 70,
      margin: 8,
      float: true,
    }, ref.current)
    const saved = loadLayout()
    if (saved) grid.load(saved)
    grid.on('change', () => saveLayout(grid.save(false)))
    return () => grid.destroy(false)
  }, [])

  return <div className="grid-shell" ref={ref}>{children}</div>
}
```

- [ ] **Step 4: 多主题**

Create `workbench-console/src/theme/themes.js`:

```js
export const THEMES = {
  paper: {
    '--paper': '#f4f1ea', '--ink': '#1f2430', '--gold': '#b88a3e',
    '--paper-cloud': '#ece7dc', '--muted': '#8b8577', '--line': '#ddd6c8', '--accent': '#c0392b',
  },
  midnight: {
    '--paper': '#1a1d2a', '--ink': '#e6e2d8', '--gold': '#c9a15c',
    '--paper-cloud': '#232838', '--muted': '#9aa0b0', '--line': '#343a4e', '--accent': '#e07b54',
  },
}
```

Create `workbench-console/src/theme/ThemeProvider.jsx`:

```jsx
import React, { createContext, useEffect, useState, useContext } from 'react'
import { THEMES } from './themes.js'

const ThemeCtx = createContext()
const THEME_KEY = 'wb-theme'

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(localStorage.getItem(THEME_KEY) || 'paper')

  useEffect(() => {
    const vars = THEMES[theme] || THEMES.paper
    for (const [k, v] of Object.entries(vars)) document.documentElement.style.setProperty(k, v)
    localStorage.setItem(THEME_KEY, theme)
  }, [theme])

  return <ThemeCtx.Provider value={{ theme, setTheme }}>{children}</ThemeCtx.Provider>
}

export function useTheme() {
  return useContext(ThemeCtx)
}
```

- [ ] **Step 5: 接入 App**

Modify `workbench-console/src/App.jsx`：

```jsx
import { ThemeProvider } from './theme/ThemeProvider.jsx'
import GridShell from './shell/GridShell.jsx'

export default function App() {
  return (
    <ThemeProvider>
      <GridShell>
        {/* 各视图组件以 widget 形态放入 */}
      </GridShell>
    </ThemeProvider>
  )
}
```

- [ ] **Step 6: 命令搜索增强**

Modify `workbench-console/src/components/CommandPalette.jsx`：在既有 Ctrl+K 基础上，新增命令注册表（重建索引、切主题 `<t>`, 搜索<`/`>等），并支持通过列表项执行。

- [ ] **Step 7: 手动验收**

Run（cwd=workbench-console）`npm run dev` → :8212。验收：

- [ ] 拖拽/缩放某个 widget，刷新页面后布局保持

- [ ] 切换主题（设置页或命令面板），配色即时变更且持久

- [ ] Ctrl+K 打开命令面板，可搜索并执行命令

- [ ] **Step 8: Commit**

```bash
git add workbench-console/package.json workbench-console/src/shell workbench-console/src/theme workbench-console/src/App.jsx workbench-console/src/components
git commit -m "feat(shell): M0-B3 GridStack 拖拽布局保存 + 多主题 + 命令搜索"
```

### M0-B4 · 前端认证入口（登录/注册 + 路由守卫）

**Files:**

- Create: `workbench-console/src/auth/LoginPage.jsx`

- Create: `workbench-console/src/auth/RegisterPage.jsx`

- Create: `workbench-console/src/auth/RequireAuth.jsx`

- Create: `workbench-console/src/auth/auth.js`（token 存取）

- Modify: `workbench-console/src/api/client.js`（注入 Authorization 头）

- Modify: `workbench-console/src/App.jsx`（登录门：未持 token 显示登录页）

- [ ] **Step 1: token 模块**

Create `workbench-console/src/auth/auth.js`:

```js
const TOKEN_KEY = 'wb-token'
const USER_KEY = 'wb-user'
export function getToken() { return localStorage.getItem(TOKEN_KEY) }
export function setToken(t) {
  if (t) localStorage.setItem(TOKEN_KEY, t)
  else localStorage.removeItem(TOKEN_KEY)
}
export function getUser() { return localStorage.getItem(USER_KEY) }
export function setUser(u) {
  if (u) localStorage.setItem(USER_KEY, u)
  else localStorage.removeItem(USER_KEY)
}
export function logout() { setToken(null); setUser(null) }
export function isAuthed() { return Boolean(getToken()) }
```

- [ ] **Step 2: API 客户端注入 token**

Modify `workbench-console/src/api/client.js` 的 `call`：

```js
import { getToken, logout } from '../auth/auth.js'

async function call(path, body) {
  const token = getToken()
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })
  if (res.status === 401 && token) { logout(); location.href = '/#/login' }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}
```

- [ ] **Step 3: 登录/注册页**

Create `workbench-console/src/auth/LoginPage.jsx`（含邮箱 tips：用户名 + 密码 ≥6；提交后 `setToken(setUser)`，跳 `/#/`）。RegisterPage 同理，先调 `/api/auth/register`。

- [ ] **Step 4: 路由守卫 + 接入 App**

Create `workbench-console/src/auth/RequireAuth.jsx`：`isAuthed()` 为假 → 渲染 `<LoginPage/>`；为真 → 渲染 children。

Modify `App.jsx`：外层包 `<RequireAuth>`。

- [ ] **Step 5: 手动验收**

- [ ] 未登录访问 :8212 → 跳登录页

- [ ] 注册新用户 → 自动登录进工作台

- [ ] 登出 → 回登录页；再访问受保护页被拦

- [ ] 手动改坏 token → 401 → 自动登出回登录

- [ ] **Step 6: Commit**

```bash
git add workbench-console/src/auth workbench-console/src/api/client.js workbench-console/src/App.jsx
git commit -m "feat(auth-ui): M0-B4 登录/注册页 + JWT 路由守卫"
```

### M0-B5 · Widget 容器框架（L3 搭壳）

**背景**：为未来接入真实数据源（M4 及以后：天气/日历/RSS/行情）预留统一 widget 抽象。M0 只搭接口与可挂载空壳，不接外部 API（避免网络/隐私/密钥依赖）。

**Files:**

- Create: `workbench-console/src/widgets/Widget.jsx`（统一接口基座）

- Create: `workbench-console/src/widgets/registry.js`（widget 注册表）

- Create: `workbench-console/src/widgets/PlaceholderWidget.jsx`

- Modify: `workbench-console/src/shell/GridShell.jsx`（渲染注册表 widget）

- [ ] **Step 1: 统一 widget 接口**

Create `workbench-console/src/widgets/Widget.jsx`:

```jsx
import React from 'react'

// 统一 widget 契约：id / title / size / render / refresh / config
// render 接收 { config, refresh }；refresh 由 registry 注入
export default function Widget({ id, title, size, config, refresh, children }) {
  return (
    <div className="grid-stack-item" gs-w={size.w} gs-h={size.h} id={`widget-${id}`}>
      <div className="widget">
        <header className="widget-head">
          <span>{title}</span>
          <button onClick={refresh} className="widget-refresh">↻</button>
        </header>
        <div className="widget-body">{children}</div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 注册表 + 占位 widget**

Create `workbench-console/src/widgets/registry.js`:

```js
// 注册表：未来 widget（天气/日历/RSS/行情）在此登记，size 供 GridStack 布局
export const registry = {
  placeholder: { title: '占位组件', size: { w: 3, h: 2 } },
}
```

Create `workbench-console/src/widgets/PlaceholderWidget.jsx`:

```jsx
import React from 'react'
import Widget from './Widget.jsx'

export default function PlaceholderWidget({ id, config, refresh }) {
  return (
    <Widget id={id} title="占位组件" size={{ w: 3, h: 2 }} config={config} refresh={refresh}>
      <p className="muted">此槽位可挂载：天气 · 日历 · RSS · 行情（M4 接入）</p>
    </Widget>
  )
}
```

- [ ] **Step 3: 渲染 widget 进 GridShell**

Modify `workbench-console/src/shell/GridShell.jsx`：children 中放置注册表 widget。先渲染 1 个 placeholder 验证可挂载：

```jsx
import PlaceholderWidget from '../widgets/PlaceholderWidget.jsx'
// GridShell 内，children 列表首项：
<PlaceholderWidget id="ph1" config={{}} refresh={() => {}} />
```

其它已迁移视图（收件箱/今天/知识等）同样包成 widget 形态放进 GridShell，使每个区域可拖拽/缩放——与 B3 布局保存联动。

- [ ] **Step 4: 手动验收**

- [ ] 页面出现"占位组件"widget，可随 GridStack 拖拽/缩放

- [ ] 布局仍自动保存（与 B3 一致）

- [ ] **Step 5: Commit**

```bash
git add workbench-console/src/widgets workbench-console/src/shell/GridShell.jsx
git commit -m "feat(widgets): M0-B5 widget 容器框架（统一接口 + 注册表 + 可挂载空壳）"
```

### M0 · 成功准则核对

M0 完成标志：

- [ ] 后端 CI 全绿（coverage≥85%，pytest、mypy、ruff 通过）

- [ ] 前端 React 工程可构建、现有功能零回归

- [ ] 注册/登录/JWT 闭环可用，未登录无法进入

- [ ] GridStack 拖拽布局可保存；多主题可切换

- [ ] Widget 容器已搭好接口，可挂载

- [ ] ADR/架构文档/changelog 落盘

***

## M1 · L1 主干 Agent 化（ReAct 主管 Orchestrator）

### M1 前情与决策记录（本分节由对话讨论定稿，含业界核实）

**目标：** 把当前三个平级、由前端各自触发的 Agent（Classifier/Reviewer/Coach）收敛为一个**单主管 ReAct 主循环 Orchestrator**——它是"贴进来的内容"的唯一入口，负责分类→决策→实践→复盘→知识召回的价值闭环路由，并在低置信/需拍板时升级到人。

**M1 关键决策（已与用户确认）：**

1. **主范式 = 单主管 ReAct 主循环**（像通用 agent，Thought→Action→Observation 边做边看自主修订），选 A。
2. **价值环节 = 独立 Skill 单元**（每环节一文件，可单测、可替换、可迭代），选 2。
3. **可评测矛盾解法 = ReAct 自由 + 标准化 Trace**。
4. **坏例处理 = 坏 Trace 回流为回归 case**。
5. **评测水位 = 选项 1**：M1 只做 Trace + 最小 eval runner + 坏例回流；繁重评测集/盲测/双人校准留 M5+。
6. **升级到人 = interrupt**：低置信/需拍板时挂起请求确认，resume 后从 checkpoint 恢复。
7. **范围排除**：M1 不做 L1 的"常驻观察代理(主动 watch)"（主动预警留 M2/M3）；不做 widgets 真实数据源（M4）。

> **业界核实（经 Explore 检索 LangGraph/OpenAI Agents SDK/AutoGen/CrewAI Flow/XState 源码文档）：** 上述设计点 1/3(幂等)/7 与主流框架一致；实际值与默认有出入（LangGraph 默认 recursion\_limit=1000）；"trace 是执行必须返回物"的表述不准确，M1 已采纳修正 A（见下）。

**修正 A（已采纳）：Trace 是观测层，不是执行层。**
初稿曾把 trace 定为"循环的必须返回物/混凝土"，经业界核实，LangSmith/OpenAI tracing 中 **state graph = 执行语义，trace/span = 观测记录**——二者一一对应，但 trace 不是让任务跑起来的必要条件。若把 trace 当运行保证，将来某步写 trace 出错会误判死好任务。**正确表述：每次显式状态转移应产生一个 domain event；trace 是这些事件的观测化、结构化记录（用于回放/归因/坏例回流），不是运行语义本身。**

**修正 B（已采纳）：用"显式状态图 + ReAct 节点内逻辑"，不用"有限状态机"一词。** LangGraph 支持循环图（agent→should\_continue→agent），不是传统 DFA；避免命名误导。**max\_steps 实际基准**：个人工作台普通任务 50–150 / 复杂 200–500，HITL 单独设人等待超时（LangGraph 默认 recursion\_limit=1000 对其偏大）。

***

### M1-A · ReAct 主管架构骨架（三张面孔）

```
                    ┌──────────────────────────────────────────┐
                    │            ReAct 主管 Orchestrator        │
                    │  Thought→Action→Observation 自由循环      │
                    └──────┬──────────────┬────────────┬────────┘
                           │              │            │
                   ┌───────▼────┐   ┌─────▼────┐   ┌───▼──────────┐
                   │ Skill 单元  │→  │ Skill 单元 │   │ Skill 单元   │
                   │ 分类/路由   │   │ 决策/追问  │   │ 复盘/召回     │
                   └────────────┘   └──────────┘   └──────────────┘
                           │              │            │
                           └──────┬───────┴────────────┘
                                  │  每步写 Trace(观测层)
                         ┌────────▼────────┐
                         │  Trace 存储      │← 可回放 / 可归因
                         └────────┬─────────┘
                                  │ 坏例回流
                         ┌────────▼─────────┐
                         │  eval runner      │  离线跑 golden case
                         └──────────────────┘
```

**三职责边界（独立、单向依赖、可单测）：**

| 部分               | 职责                                      | 依赖                            |
| ---------------- | --------------------------------------- | ----------------------------- |
| **ReAct 主管**     | 读输入→想→选 Action→执行→看结果→修订；低置信时 interrupt | 依赖 Skill 注册表 + 写 domain event |
| **Skill 单元**     | 每个价值环节的原子动作（分类/追问/提炼/召回），只做一件事          | 依赖 engine/vector/vault，不依赖主管  |
| **Trace + eval** | 每次状态转移取证 + 坏例回流 + 离线回归                  | 不依赖运行逻辑，只管记录与评测               |

**单向依赖约束（避免循环）：** 主管 → Skill 注册表；Skill → engine/vector/vault；Skill 不依赖主管。新增功能 = 注册表加一行，不动主管本身。

***

### M1-B · ReAct 主管状态图（主循环有界化）

主管本质是**显式状态图 + ReAct loop 作为节点内逻辑**（修正 B）。状态转移只在边界事件发生。

**状态集：**

```
IDLE → INGEST → ACTING →（低置信 interrupt）→ WAITING_HUMAN →（resume/驳回）→ ACTING
                └─────────→ DONE
       （任一步失败/超时 → ERROR）
```

| 状态                 | 进入方式         | 离开方式                                      |
| ------------------ | ------------ | ----------------------------------------- |
| **IDLE**           | 启动           | 收到输入→INGEST                               |
| **INGEST**         | 收到输入         | 归一化成功→ACTING；失败→ERROR                     |
| **ACTING**         | 归一化完成        | 低置信中断→WAITING\_HUMAN；完成→DONE；异常→ERROR     |
| **WAITING\_HUMAN** | 触发 interrupt | 用户确认→resume回ACTING；驳回→回ACTING(修订)；放弃→DONE |
| **DONE**           | 工作完成         | 等新输入                                      |
| **ERROR**          | 未捕获异常        | 记录 domain event→可回 IDLE                   |

**三类 interrupt（对齐"确认型 = 升级到人，而非默认中断"）：**

| 类型               | 触发条件              | 给用户的负载        | 用户决策    |
| ---------------- | ----------------- | ------------- | ------- |
| **confirm**      | 需执行有副作用动作（写库/发消息） | 提议 + 置信度 + 备选 | 允许/驳回/改 |
| **disambiguate** | 多类置信接近、或输入含糊      | 候选分类各带分数      | 选一个/改输入 |
| **judgement**    | 复盘结论有争议/涉及重大判断    | 主管推演 + 分歧点    | 拍板/驳回重想 |

**resume 语义（对齐 LangGraph checkpointer，业界已验证）：** 用户确认后从 WAITING\_HUMAN **恢复到 ACTING**，interrupt 前中间结果保留；**进 WAITING\_HUMAN 前的副作用必须幂等**（resume 时节点可能重放，LangGraph 文档明确 "side effects called before interrupt must be idempotent"）。

**每跳产生一个 domain event（修正 A，trace 是观测层）：**

```python
# domain event（执行语义层，每跳必产）
TraceEvent(id, state_from, state_to, event,
           thought, action, observation,   # ACTING 内才有
           tool, args, result, confidence, # 动作详情
           human_decision,                 # 若中断
           ts)
```

Trace 是这些 domain event 的**观测化持久记录**（回放/归因/坏例回流用），不是运行保证。

**执行守护（主流标配）：**

| 守卫                       | 作用                               | 建议值                    |
| ------------------------ | -------------------------------- | ---------------------- |
| **max\_steps**           | 防无限循环，超限强制 DONE/ERROR            | 普通 50–150 / 复杂 200–500 |
| **budget**               | 单任务成本上限（token+wall-clock）        | 可配                     |
| **human\_wait\_timeout** | HITL 等待你的时限                      | 单独设                    |
| **domain event 必产**      | 每跳无 event 即视为状态机不完整（不是 trace 失败） | 必须                     |

***

### M1-C · Skill 单元规范 + 注册表 + 5 个 Skill 集

**决策记录：** M1 补齐 **5 个 Skill**（分类/决策/实践/复盘/召回），产品蓝图完整闭环一上来就挂满注册表（选 2）。其中 3 个迁自现有 agent（classify/review/recall），2 个新写（decision/action）。

**职责边界（与用户确认）：** decision 只做分析、recall 只做召回（职责单一，主管可串联）。**升级到人（interrupt）映射：**

- `action` 带写 Vault 副作用 → **confirm** interrupt（写库前问）

- `decision` 低置信 → **disambiguate / judgement**

- `classify / review / recall` 高置信 → 默认自主，不中断

**Skill 统一协议（一个 file = 一个 Skill）：**

```python
# skills/base.py —— Skill 统一协议
from typing import Protocol

class Skill(Protocol):
    name: str                 # 注册表键，如 "classify"
    description: str          # 给主管看：这个 skill 干什么、何时用
    requires_confirmation: bool  # 是否需升级到人（对齐 interrupt）

    def run(self, ctx: "SkillContext", args: dict) -> "SkillResult":
        """执行本环节。ctx 注入能力；args 为主管传参。"""

# SkillContext —— 注入能力，Skill 不依赖主管
class SkillContext:
    engine: "AIEngine"
    vault: "VaultStore"
    vector: "VectorStore"
```

**5 个 Skill 职责与注入：**

| Skill        | 来源                  | 职责（run 做什么）                            | 判定  | 注入              | interrupt                  |
| ------------ | ------------------- | -------------------------------------- | --- | --------------- | -------------------------- |
| **classify** | 迁 `ClassifierAgent` | 输入分类打标 → 返回 5 类之一 + 置信度                | 确定  | engine          | 默认自主                       |
| **decision** | 新写                  | 对"决策"类输入做结构化追问 + 多维分析，产出可选方案与倾向；低置信需拍板 | 中-高 | engine          | 低置信→disambiguate/judgement |
| **action**   | 新写                  | 把结论/待办转化为可执行项：写决策备忘、登记待办、次日跟进信号        | 中   | vault(写)+engine | confirm（写库前问）              |
| **review**   | 迁 `ReviewerAgent`   | 复盘：扫闭环率、找偏差                            | 高   | vault+engine    | 默认自主                       |
| **recall**   | 迁 `CoachAgent`      | 开新任务时按主题召回历史经验递到面前                     | 确定  | vector          | 默认自主                       |

**注册表（主管唯一调度入口，单向依赖：主管→注册表）：**

```python
# skills/registry.py
REGISTRY = {
    "classify": ClassifySkill,
    "decision": DecisionSkill,
    "action":   ActionSkill,
    "review":   ReviewSkill,
    "recall":   RecallSkill,
}
def get_skill(name: str) -> Skill: ...
```

**TDD 策略：**

- **3 个迁移 Skill**：保留现有 `ClassifierAgent/ReviewerAgent/CoachAgent` 的单测断言，改为直接测 Skill 的 `run()`（结果等价即迁移成功）——这就保证了"迁移不回归"

- **2 个新 Skill（decision/action）**：TDD 先写红。`decision` 测"结构化追问产出可选方案 + 低置信触发需拍板标记"；`action` 测"写决策备忘 + 登记待办 + 触发 confirm interrupt 前副作用幂等"

- **注册表**：测"按名取 Skill、未知名抛错、5 个均已注册"

> **收口界定（选项 1）**：M1 本版定稿到"设计骨架"粒度——架构、状态机、Skill 规范、注册表、5 Skill 职责与 TDD 方向。**每个 Skill 的 run() 具体实现、3 个 Agent 迁移对照表、6 层提示词工程逐层迁入这 5 个 Skill** 均为实现细节，**留到"执行 M1 之前"再展开**（届时更新本分节，写逐任务 TDD 红绿步骤）。不提前纸上谈兵，与"M0 粒度对齐"。

### M1 · 成功准则核对

M1 完成标志：

- [ ] ReAct 主管 Orchestrator 存在，状态图（IDLE/INGEST/ACTING/WAITING\_HUMAN/DONE/ERROR）可跑

- [ ] 5 个 Skill（classify/decision/action/review/recall）全部注册进注册表，从注册表按名可取

- [ ] 3 个现有 Agent（Classifier/Reviewer/Coach）行为迁移无回归（单测断言等价）

- [ ] 2 个新 Skill（decision/action）有红转绿测试

- [ ] action 写 Vault 前触发 confirm interrupt；decision 低置信触发 disambiguate/judgement

- [ ] 每跳产生 domain event，Trace 可回放、坏例可归因

- [ ] 最小 eval runner 能跑 golden case（通过/失败）；坏 Trace 可回流为回归 case

- [ ] 执行守护（max\_steps/budget/human\_wait\_timeout）生效

***

## M2 · 知识关联 / 写卡自动双链（降本版）

### M2 前情与决策记录

**目标：** 让"agent 写入 Vault 的每张新卡"自动带上正确的 `[[双链]]`，关联到既有知识网（Obsidian 已有人工双链 + AI 隐式相似边），并复用 M1 的 recall Skill，把一次写入从"存一张散卡"升级为"存一张已挂网、可被后续 recall/decision 找到的卡"。

**M2 关键决策（已与用户确认）：**

1. **不新建独立"关联引擎"**——M2 性质是给"写卡流程"套上「召回预处理 + 阈值自动双链 + 边缘才上 LLM」的规范，复用 M1 recall；而非做一个独立的关联图谱服务。
2. **成本走"最低成本版"**（向量+阈值为主，LLM 只在边缘案例介入）——理由见下"业界核实"。
3. **"该链到谁"由主管编排 → 复用 M1 recall Skill**（不是 action 自己重做"找相关卡"，避免与 recall 职责重复）。action 的写入规范扩展为「接收待链目标(link targets)」。
4. **可选增强版（hybrid+MMR+reranker）不在 M2 做**，留待准确率确实不够时再加（升准不降本）。
5. **双链是显式边：** 尊重 Obsidian 已写入的人工 `[[双链]]`，AI 推断的是隐式边，二者合并成一张网（合成，非替代）。

> **业界核实（经 Explore 检索 Smart Connections / ObsidianGraphRAG / nathanael-fijalkow-RAG / langchain-rag-pipeline 等）：** "纯向量召回判相似、不喂 LLM"（阈值/去重/MMR）与"增量索引/懒重算"与"候选预过滤再给 LLM"均为成熟标准做法；"LLM 只输出结构化最小结果"有条件成熟（适合返回 id/confidence，但给标题+摘要+score，近全卡可能误判同名词卡）。ObsidianGraphRAG 实测：1000 笔记初始 15-30 分钟、改 5 个 30 秒——故 hash 增量索引对频繁写入很关键。

### M2-A · 写卡自动双链管线（最低成本版）

```
新卡内容
  → [hash 增量索引：算 content_hash，没变则复用旧 embedding，变了只重算这张]
  → Chroma top_k=20 召回旧卡
  → 阈值过滤(score≥0.75) + 去重
  → score≥0.85：直接生成 [[链接]]         （纯向量，不耗 LLM token）
  → 0.75≤score<0.85：才喂 LLM 判断       （只给标题+摘要+score，返回 JSON {link_to:id, confidence}）
  → score<0.75：不自动链，标记"待人工查看"
  → action 带着 link targets 写入 Obsidian
```

**成本结论：** 多数写入走纯向量路径，token 增量趋近 0；边缘案例才耗一次 \~200-600 token。M1 recall 这里被复用为"召回候选"环节，不新增独立"找相关卡"逻辑。

### M2-B · hash 增量索引（与 M1 recall 共用）

- 每张卡维护 `content_hash / version`；写卡/改卡前先算 hash

- hash 未变 → 复用旧 embedding（本实现是本地哈希词袋，embedding 自身零成本，此条为省"重扫/避免重复计算"）

- hash 变 → 只重算这一张卡的 embedding + 关联，不全文重扫

- 全量重扫仅用于：首次初始化、embedding 模型升级、chunk 规则变更、数据损坏

> 补充：本项目的 `_LocalEmbeddingFunction` 是本地哈希词袋（无网络、无模型下载），embedding 缓存对其意义不大；真正需的是"hash 判断内容是否变化"的增量索引，避免频繁写入时反复重扫全网。

### M2 · 成功准则核对

M2 完成标志：

- [ ] action 写卡流程接入了"M1 recall 召回候选 → 阈值/LLM 决策 → 带双链写入"的管线

- [ ] 高置信(≥0.85)新卡自动生成 `[[链接]]`，不消耗 LLM

- [ ] 边缘(0.75\~0.85)仅喂 LLM 标题+摘要+score，返回结构化 JSON

- [ ] 低置信(<0.75)不自动链，标记待人工

- [ ] hash 增量索引：改一张卡只重算该卡，不全文重扫

- [ ] Obsidian 已有人工双链被尊重（显式边），AI 相似边为其补充（隐式边），合成一张网

- [ ] 写卡/改卡重复操作不重复计算 embedding（hash 命中即复用）

***

## M3 · 决策辅助深化（带历史参照，反结果偏误）

### M3 前情与决策记录

**目标：** 把 M1 的 `decision` Skill 从"通用结构化追问"深化为"带历史参照的决策辅助"——用户做决策时，主管递上"你过去对同类决策怎么想、结果如何"的结构化参照，让决策站在自己的经验库上，而非每次通用模板问答。

**M3 关键决策（已与用户确认）：**

1. **历史参照检索复用 M1 recall + M2 关联管线（R1）**：decision 不自己检索，只消费 recall 传来的"历史决策候选"。避免与 recall 职责重复，对齐"只做一件事"。
2. **新写决策备忘带结构化 frontmatter（M3-A）**：含 outcome 与 result\_quality（结果质量），对齐 Decision Journal / ADR 正统做法。
3. **历史参照做结构化摘要注入、不注入全文（M3-B）**：RAG 最佳实践。
4. **存量宽松、只强新卡（M3-C）**：不强制改造存量，与 open-recall"新结构化、旧宽容"一致。
5. **反结果偏误（业界修正，已采纳）**：初始设计曾"按 outcome 优先成功案例"；业界（Decision Journal）明确这是陷阱——**决策质量 ≠ 结果质量**（结果好可能运气，结果差可能逻辑对）。修正：注入时不按成功过滤，而是让 decision 区分"为什么成/为什么败"并对比当前与历史条件差异。

> **业界核实（经 Explore 检索 decision-journal-template / adr-madr / open-recall / Metadata-Aware-Rag / git-vault-protocol 等）：** M3-A/B/C 三件套属正统主流路线。额外收获：决策记忆建议分"原文层/结构化摘要层/检索索引层"三层；检索用"metadata 过滤 + 向量召回 + 结果质量重排"（非只按成功过滤）；Chroma 支持 metadata filter（Mongo-style dict）。

### M3-A · 新决策备忘 frontmatter 结构

```markdown
---
type: 决策
date: 2026-09-01
decision: <本次定的结论>
context: <当时背景一两句>
criteria: <用到的判据，逗号分隔>
expected_outcome: <当时的预期结果>
actual_outcome: <已知实际结果：未决/成功/失败/调整>
result_quality: <好/中/差>       ← 区分于 outcome：结果质量（好可能运气）
lesson: <复盘得出的可迁移经验>
applicability: <适用/不适用条件>
---
```

> 存量卡不强制改造（M3-C）：召回到存量卡时用启发式推断 `actual_outcome`（未知→存未知），不强改原文。**decision 判断参照质量时，`result_quality`** **仅作对照维度、不作"按成功过滤"依据**（反结果偏误）。

### M3-B · decision 注入历史参照（R1，只消费不检索）

`decision` 的 run() 扩展为接收 recall 传来的「结构化历史决策候选」，内部处理：

1. 过滤候选：优先保留 `result_quality` 可辨、有结论的候选（但**不按成功与否过滤**）
2. 把历史参照提炼为「当时怎么定 / 结果如何 / 为何成败」的**经验卡对照**，注入 prompt（非全文）
3. 输出升级为「可选方案 + 历史参照对照（含成败原因）+ 倾向」

**关键：** decision 不调用检索；只消费 recall 传入参照。为防结果偏误，prompt 明确要求区分"决策逻辑优劣"与"结果好坏"，并对比当前条件与历史条件差异。

### M3-C · 主管编排决策链路（接 M1+M2+M3）

```
classify(贴的是决策类输入)
  → recall(按决策主题召回历史决策候选，走 M2 关联管线 + 三层索引 metadata 过滤)
  → decision(注入结构化历史参照，产出方案+成败对照+倾向)
  → 低置信 → interrupt(disambiguate/judgement)
  → 高置信 → action(写决策备忘：M3-A 结构 + M2 双链)
```

这条链路是 M1 主管价值的直接示范：**不是 if-else，而是主管用 ReAct 把 classify→recall→decision→action 编成一条"带历史智能的决策流"**。

### M3 · 成功准则核对

M3 完成标志：

- [ ] 新写决策备忘带 M3-A frontmatter 结构（含 outcome 与 result\_quality）

- [ ] decision 只消费 recall 参照、不自己检索（R1 单向依赖）

- [ ] decision 输出含"可选方案 + 历史参照成败对照 + 倾向"

- [ ] 参照注入为结构化经验卡摘要、非全文

- [ ] **反结果偏误**：不按 outcome 过滤成功案例；prompt 区分决策逻辑 vs 结果好坏

- [ ] 存量决策备忘宽容处理（启发式推断 outcome，不强制改写）

- [ ] 主管能编 classify→recall→decision→action 决策链路

- [ ] recall 支持 metadata 过滤 + 结果质量重排（三层索引）

***

## M4 · 内部数据统计 widget（存量型优先 + 用量 SQLite 化）

### M4 前情与决策记录

**目标：** 把工作台自身的运行数据可视化，成为 M1–M3 的观测窗口：知识量/分类分布 + 资源用量（token/花费）。前端复用 M0-B5 Widget 容器 + 双主题 + 布局保存。

**M4 关键决策（已与用户确认）：**

1. **北极星 = 内部数据统计 widget（候选 1），不做外部数据（天气/日历/RSS 留后）**。
2. **存量型优先**：知识存量（读 Vault + Chroma）直接可做；**运行型指标（依赖 trace/eval）延后**，不阻塞 M4。
3. **用量 = 存量、非扩展（用户点破 + 业界印证）**：token/花费不是"未来扩展"，是现在就要、且数据要落成可长期聚合。已从你现有 `usage.py` 确认现状为**纯内存（list/dict，MAX\_EVENTS=200 丢最旧，进程重启清零）**，缺持久化与趋势能力，故 M4-B 需补。
4. **用量存储用 SQLite（方案 X）**：`usage_records` 表替代内存 dict，可持久、可聚合、可出趋势；`daily_usage_snapshots` 做日汇总。贴合未来 trace 落库同存储思路。
5. **统计端点放 backend 聚合，前端只 fetch，MOCK 降级**（业界主流 + 已定框架）。

> **业界核实（经 Explore 检索 dastanboard / llm-usage-exporter / LLM Observatory / Langfuse / OpenLLMetry / Team-AVON / github\_dashboard 等）：** 内部统计=后端聚合端点 + 前端 fetch 是主流（dashboard 不直接读 Vault/Chroma/billing）。用量追踪轻量做"每次调用埋点记 usage 表"而非上 Langfuse/LangSmith 全家桶；聚合用"近 7 天实时 + 更久日快照缓存"；MOCK 降级用 `/health` 判断 + 前端内置 fallback + toast。"运行型指标"是观测层能拿到的更强数据，本地小数据优先走轻量自建。

### M4-A · 知识存量统计（读 Vault + Chroma）

- 卡片总数、分类分布（`ALLOWED_FOLDERS` 各目录计数）

- 决策备忘数、关联/双链数（依赖 M2 建成后可从 Vault 双链扫）

- 周/月新增卡片趋势（按 frontmatter date）

### M4-B · 资源用量统计 · SQLite 化（升级现有 usage.py）

现状：`usage.py` 内存 dict，已记录 `model / pt / ct / cost / ms / 工具名`，但无 source/skill 语义字段、不落盘、200 条丢最旧。
升级目标（最小改法，贴现状）：

```sql
-- usage_records（每次 LLM/工具调用一条，替代内存 _events）
id, ts, kind(llm|tool), source, skill, model,
input_tokens, output_tokens, cost, latency_ms, status

-- daily_usage_snapshots（每日汇总，供 7d+ 趋势，避免全表聚合）
date, source, skill, total_requests, input_tokens, output_tokens, cost
```

- 保留现有 `record_llm/record_tool` 语义，改为写 SQLite；`set_prices` 价格配置沿用

- 新增 source/skill 分组字段（记录时带上）

- 聚合端点：近 7 天实时查 `usage_records`，更久用 `daily_usage_snapshots`

> **依赖说明（通读封板确认，顺序自洽）：** `/api/usage` 数据源从内存切到 SQLite 时，UsageView 展示不变、仅数据来源切换——此端点在 B2（迁移 UsageView 指向 `/api/usage`）与 M4-B（换 SQLite 后端）先后两处被触碰，但语义保持"同一端点、同一响应形状"，B2 先接、M4-B 换源，不冲突。

### M4-C · bridge 聚合端点 + 前端展示 + MOCK 降级

- Backend 聚合端点（单一数据源，bridge 层）：

  - `/api/health`（供前端判断模式）

  - `/api/vault/stats`、`/api/vault/category-distribution`、`/api/vault/trends`

  - `/api/chroma/stats`

  - `/api/llm/usage?range=30d`、`/api/llm/cost?range=30d`（读 usage DB）

- React 只 fetch + chart（依赖 M0-B5 Widget 容器 + 双主题 + 布局保存）

- MOCK 降级：`/health` 失败或 `DASHBOARD_MODE=mock` 用前端内置 mockData + toast 提示"正在使用 mock 数据"

### M4 · 成功准则核对

M4 完成标志：

- [ ] Vault 知识存量可统计（卡片总数/分类分布/新增趋势/决策量）

- [ ] Chroma 集合统计可读（collection 文档数等）

- [ ] 用量从内存改为 SQLite `usage_records`（重启不丢、可长期聚合）

- [ ] `daily_usage_snapshots` 日汇总存在，7d+ 趋势不重算全表

- [ ] 用量记录含 source/skill 分组字段

- [ ] bridge 聚合端点齐全（/health /vault/\* /chroma/\* /llm/usage /llm/cost）

- [ ] React dashboard 只 fetch 展示，展示知识量 + 用量趋势

- [ ] MOCK 模式降级 + toast 提示可用

- [ ] 语法/测试通过（沿用 M0 的 ruff/mypy/pytest 门槛）

### M4 · 已登记扩展（不丢，待后续里程碑/横切实现）

- [ ] **运行型指标窗口**（依赖 M1 trace/domain event）：写卡频率、闭环率、召回命中率——M4 只做了存量型，运行型待 M1 trace 落库后接入统计（见 M5+ 扩展登记）

- [ ] 外部数据 widget（天气/日历/RSS/行情/服务健康）——候选 2，留 M5 以后展示增强

- [ ] 更重观测栈（Langfuse/OpenTelemetry/Prometheus+Grafana）——数据量增长或需要 eval/debug 时再评估，不默认引入

