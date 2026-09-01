# 个人工作台 · 全面迭代实施计划（M0 → M4）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将个人工作台从「可运行脚本」升级为「可构建、可鉴权、可扩展、可部署的规范化工程」，并完成 M0–M4 的既定功能迭代。

**架构：** 分层 + 模块边界范式。Python 后端（FastAPI Bridge + MCP）与 React/Vite 前端分离，各自通过定义良好的接口通信，CI 全门禁保证「提交即可信」。

**Tech Stack：** Python 3.10 · FastAPI · FastMCP · ChromaDB · SQLite(JWT, 方案A) · React · Vite · GridStack.js

**计划纪律：** 本文档为**唯一统一计划文件**。M0–M4 各里程碑计划全部收敛在此文件，按里程碑分节。**只在全部里程碑（M0–M4）计划都讨论定稿后统一执行，执行时逐任务 TDD + 频繁提交。**

> 关联 spec：`docs/superpowers/specs/2026-09-01-workbench-m0-engineering-design.md`

---

## 执行次序总览

按里程碑推进，每个里程碑内部按批次顺序做，**每批独立 commit、独立验收，不做完下一批**：

```
B0 后端规范 → B1 后端认证 → B2 React 化 → B3 外壳 → B4 前端认证 → B5 Widget 壳
───────────────────────── M0 ─────────────────────────
→ M1 → M2 → M3 → M4（各里程碑计划在下方对应分节，讨论定稿后填充）
```

> 依赖说明：B1（后端认证）先于 B4（前端认证入口）——先有后端端点，前端才能接。B3/B5 依赖 B2（React 工程）。B1 的鉴权加在业务端点上，会**先于**前端 B4，因此在 B2 React 迁移期间，`request()` 尚未带 token；B2 的 MOCK 模式不受影响，LIVE 模式在 B4 完成前访问受保护端点会 401——**这是预期**，B4 补齐 token 后闭合。

---

## M0 · 工程化 + React 重写

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

> 注：`test_unauthenticated_blocked` 依赖 `/api/*` 端点已全部挂 `Depends(require_auth)`。若某些端点（如 `/api/auth/*`、`/api/usage`、`/api/list_tags`）需放行，调整 `require_auth` 的适用范围：只对 `search_knowledge / create_note / classify_text / scan_decision_closed_loop / reopen_task` 加依赖，`/api/health`、`/api/auth/*` 放行。计划默认对 5 个业务端点加鉴权，`/api/usage` 视前端需求可选鉴权。

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

**背景**：`workbench-console` 现为纯静态（`index.html` + `assets/app.js` ~26KB + `app.css`）。B2 将其迁为 Vite+React 工程，**功能等价迁移**（不丢能力），新增功能留给 M0-B3/B4。

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

---

> **M1–M4 计划（待逐个讨论定稿后追加到本文件）**
> 占位：M1 L1 主干 agent 化（主管 Agent）；M2 知识关联/洞察；M3 决策辅助深化；M4 真实数据源 widget。以下各节在讨论定稿后填充完整 TDD 步骤。