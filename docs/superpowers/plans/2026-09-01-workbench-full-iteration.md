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

- [x] **Step 4: 运行覆盖率并确认达标**

Run（cwd=workbench）:

```
pytest --cov --cov-report=term-missing
```

Expected: Total coverage ≥85%。

> **执行修正（2026-09-02，用户拍板方案 2）：** B0 时点实测 52.8%——bridge.py 0%、usage.py 39% 是结构性缺口（其测试属 B1/M4 范围），B0 单批无法诚实达到 85%。改为**分阶段收紧**：B0=50%（已过）→ B1 补 auth/bridge 测试后提 70% → M0 收口（B4/B5 后）85%。`pyproject.toml` 的 `fail_under` 随阶段调整，理由与路线记入 ADR-0001 D5。

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

> **B1 执行记录（2026-09-02，全部 26 测试绿，coverage 78.5% ≥ 70%）：**
>
> 1. **修正 Step 6 设计缺陷**：`require_auth` 原计划用模块常量 `_AUTH_SECRET` 解码 token，但测试 monkeypatch `auth_service`（独立 secret）后签发/校验 secret 不一致，`/api/auth/me` 必 401。改为 `AuthService.verify_token()`（secret 单源，bridge 只调不持有），monkeypatch 后全链路一致。
> 2. **修正 repository 连接泄漏**：`with conn:` 只管事务不管关闭 → `closing(conn) + conn` 组合。
> 3. `repo: UserRepository = field(init=False)` 标注，过 mypy（17 文件无错）。
> 4. 鉴权端点实为 **7 个**（计划写 5 个）：search\_knowledge / list\_tags / usage(GET) / create\_note / classify\_text / scan\_decision\_closed\_loop / reopen\_task，按封板范围界定全部挂 `Depends(require_auth)`；`/api/health`、`/api/auth/*` 放行。
> 5. `observe_calls` 采纳计划注建议：skip 列表加 `/api/auth/`（auth 非业务调用，不记 usage 观测）。
> 6. 测试增强（7→13 用例）：verify\_token 回环/伪造、短密码、health 放行、错密码登录 401、重复注册 400。
> 7. `fail_under` 按分阶段约定提至 70（实测 78.5%）；JWT fallback secret 加长至 ≥32 字节（避 InsecureKeyLengthWarning）。
> 8. **Review 修复（2026-09-02，提交前复查发现）**：① `test_auth.py` 4 处 11 字节短 secret → `b"t" * 32`（与 test\_bridge 统一，InsecureKeyLengthWarning 4 处全消，19→15 个警告，余下 15 个均为 Chroma 三方库 DeprecationWarning，B0 前既有）；② `bridge.py` `_AUTH_SECRET` 补短 key 边界——LLM key 非空但 <32B 时（如 CI 的 `sk-test`）拼接 fallback 补足。修后复验：26 测试绿、coverage 78.61%、ruff 27 文件过、mypy 17 文件无错。

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

- [x] **Step 1: 初始化 Vite + React 工程**

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

- [x] **Step 2: 创建挂载与入口**

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

- [x] **Step 3: 建 API 客户端（保留 MOCK/LIVE 切换）**

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

- [x] **Step 4: 迁移视图与组件（等价复刻）**

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

- [x] **Step 5: 迁移设计系统为 token**

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

- [x] **Step 6: Build + lint 通过**

Run（cwd=workbench-console）:

```
npm install
npm run build
npm run lint
```

Expected: build 产出 `dist/`，lint 无 error。

- [x] **Step 7: 回归验收（零回归）**

以既有自测清单（含 Obsidian URI 直开、输入落盘、MOCK/LIVE 降级、标签聚合）启动 `npm run dev`（:8212）+ Bridge（:8213）人工逐条走查。List all must-pass in regression.md（可选，执行时产出）。

- [x] **Step 8: Commit（移除旧 app.js，保留 app.css 作样式基座）**

```bash
git add workbench-console
git rm workbench-console/assets/app.js
git commit -m "refactor(console): M0-B2 迁移为 React+Vite，功能等价、零回归"
```

> **B2 执行记录（2026-09-02，build ✓ 50 模块 / lint 0 error / 回归 20/20 PASS）：**
>
> 1. **结构落地**：package.json + vite.config.js（:8212，base './'）+ .eslintrc.cjs（eslint:recommended + react + react-hooks）；index.html 重写为 React 挂载点（保留原 title）；`assets/app.css` 原样保留为样式基座（main.jsx 引入），组件类名与原 DOM 结构 1:1 对齐，**视觉零回归**。
> 2. **Step 3 实现与计划模板的差异**（有意）：计划模板的 `request()` MOCK 短路与原 app.js 交互模型不符（原版是视图层判模式，MOCK 数据织入视图）。等价落地为 `api()/apiGet()` 单收口（B4 注入 Authorization 头的位置不变）+ client.js 内置 mock 数据/规则（inboxData、mockTags、mockRule、ruleFor、folderFor）。localStorage 沿用原 key `wb-mode` 与 `mock`/`live` 值（兼容老用户存量模式）。
> 3. **组件迁移**：App.jsx 编排（视图路由/mode/toast/侧栏折叠/全局快捷键 Ctrl+B·Ctrl+K）；7 组件 + 9 视图按计划清单落位；跨视图检索用 `{q, n}` 递增 token 触发（同词可重复检索）；debounce/committing 防抖用 ref 保持原时序语义。
> 4. **theme.css**：按计划建语义别名 token（--paper/--ink/--gold/--line/--accent…），取值与 app.css 原始 oklch token 一致，为 B3 ThemeProvider 换肤预留单点。
> 5. **验证**：`npm install` + `npm run build`（dist 168.57kB JS / 17.77kB CSS）+ `npm run lint` 0 error；dev(:8212) + Bridge(:8213) 起服，浏览器自动化走查 20 项（九视图/输入条分类+落盘/Ctrl+K 面板键盘流/Ctrl+B/AI 确认弹层/上下文面板/模式切换/LIVE 检索 401 中间态/控制台无 JS 错）**全部 PASS，零回归**（LIVE 端点 401 为 B1→B4 计划内中间态）。
> 6. **收尾**：.gitignore 加 `node_modules/`；CI frontend job 启用（npm ci → build → lint，package-lock.json 入库）；`git rm assets/app.js`（569 行旧逻辑全部迁入组件）。

### M0-B3 · L2 外壳新功能（GridStack 拖拽 / 布局保存 / 多主题 / 命令搜索）

**背景**：在 React 化基础上升级外壳，使其具备 Dashboard 特性（对齐 Dashy 式风格）。这些是**新增**能力，不改已有功能语义。

**Files:**

- Create: `workbench-console/src/shell/GridShell.jsx`

- Create: `workbench-console/src/shell/layout.js`（layout 读写 `localStorage('wb-layout')`）

- Create: `workbench-console/src/theme/ThemeProvider.jsx`（多主题）

- Create: `workbench-console/src/theme/themes.js`

- Modify: `workbench-console/src/App.jsx`（引入 GridShell + ThemeProvider）

- Modify: `workbench-console/src/components/CommandPalette.jsx`（增强命令搜索）

- [x] **Step 1: 安装 GridStack**

Run（cwd=workbench-console）:

```
npm install gridstack
```

- [x] **Step 2: 布局读写模块**

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

- [x] **Step 3: Create GridShell（拖拽 + 缩放 + 自动保存）**

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

- [x] **Step 4: 多主题**

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

- [x] **Step 5: 接入 App**

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

- [x] **Step 6: 命令搜索增强**

Modify `workbench-console/src/components/CommandPalette.jsx`：在既有 Ctrl+K 基础上，新增命令注册表（重建索引、切主题 `<t>`, 搜索<`/`>等），并支持通过列表项执行。

- [x] **Step 7: 手动验收**

Run（cwd=workbench-console）`npm run dev` → :8212。验收：

- [x] 拖拽/缩放某个 widget，刷新页面后布局保持

- [x] 切换主题（设置页或命令面板），配色即时变更且持久

- [x] Ctrl+K 打开命令面板，可搜索并执行命令

- [x] **Step 8: Commit**

```bash
git add workbench-console/package.json workbench-console/src/shell workbench-console/src/theme workbench-console/src/App.jsx workbench-console/src/components
git commit -m "feat(shell): M0-B3 GridStack 拖拽布局保存 + 多主题 + 命令搜索"
```

> **B3 执行记录（2026-09-02，build ✓ 68 模块 / lint 0 error / 浏览器验收 A·B·C·D 全 PASS）：**
>
> 1. **GridStack 13.2.0**（计划模板写于旧版）。**React 集成约定**（与计划模板 children 模式有意不同）：item DOM 由 React 渲染（`.grid-stack-item` + `gs-*` 属性），位置由 GridStack 接管；恢复布局不走 `grid.load()`（会动 DOM、与 React 冲突），渲染前用 saved 覆盖初始位置；卸载 `destroy(false)` 只解绑行为。GridShell 约束 item 内容静态（卡片数据常量化），为 B5 widget 容器复用铺路。
> 2. **落位场景**：知识视图 4 卡 widget 化（RCA 大卡 + 3 小卡，`wb-layout:knowledge` 按容器 key 命名空间存布局，B5 多容器可扩展）。拖拽用手柄 `⠿`（`.kb-grip`，hover 显现），卡片本体保留点击检索语义（验收 C6 过）。
> 3. **主题真实生效的关键**：计划模板 themes 只切 B2 语义别名 token，但组件样式读的是 app.css 原始 token——直接照抄会导致切主题无任何视觉变化。落地为 themes.js 定义**完整原始 token 集**（surfaces/ink/gold/ink-panel/states/shadow + 语义别名），ThemeProvider 写 documentElement（先清后写防残留）。paper=原值（默认零变化），midnight=书香暗夜（暖褐黑+亮铜金）。
> 4. **顺带 token 化 2 处硬编码**（值不变、视觉零变化）：`.kb-main` 背景 → `--bg-main-card`；`.btn` 白字 `#fff` → `var(--bg-app)`（暗色下墨底白字会不可读）。其余小面积装饰浅色（kind 标签底/tag-soft/边框等）暗色下偏亮但可辨识，**登记后续打磨**，不在 B3 扩面。
> 5. **命令面板**：命令注册表 17 条（操作 5 / 外观 3 / 导航 9），输入过滤（includes 模糊匹配）+ 分组渲染 + ↑↓/Enter/Esc 键盘流。计划提的「重建索引」命令无后端端点（MCP 5 工具中没有），**不造假功能**，以「恢复默认布局」命令替代（真实功能：resetLayout + 刷新）。主题入口两处：设置页外观卡 + 命令面板。
> 6. **验收**（浏览器自动化三轮）：A 组命令面板（17 条分组/过滤/Enter 执行导航）✓；B 组主题（暗夜即时生效+刷新持久+切回）✓；C 组 GridStack（grid.update 移动/缩放 → wb-layout 保存 → 刷新布局保持 → 点击语义保留）✓；D 组回归（九视图无白屏/无业务 JS error）✓。注：`react/no-unknown-property` 对 gs-\* 放行（eslint ignore 列表）。

### M0-B4 · 前端认证入口（登录/注册 + 路由守卫）

**Files:**

- Create: `workbench-console/src/auth/LoginPage.jsx`

- Create: `workbench-console/src/auth/RegisterPage.jsx`

- Create: `workbench-console/src/auth/RequireAuth.jsx`

- Create: `workbench-console/src/auth/auth.js`（token 存取）

- Modify: `workbench-console/src/api/client.js`（注入 Authorization 头）

- Modify: `workbench-console/src/App.jsx`（登录门：未持 token 显示登录页）

- [x] **Step 1: token 模块**

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

- [x] **Step 2: API 客户端注入 token**

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

- [x] **Step 3: 登录/注册页**

Create `workbench-console/src/auth/LoginPage.jsx`（含邮箱 tips：用户名 + 密码 ≥6；提交后 `setToken(setUser)`，跳 `/#/`）。RegisterPage 同理，先调 `/api/auth/register`。

- [x] **Step 4: 路由守卫 + 接入 App**

Create `workbench-console/src/auth/RequireAuth.jsx`：`isAuthed()` 为假 → 渲染 `<LoginPage/>`；为真 → 渲染 children。

Modify `App.jsx`：外层包 `<RequireAuth>`。

- [x] **Step 5: 手动验收**

- [x] 未登录访问 :8212 → 跳登录页

- [x] 注册新用户 → 自动登录进工作台

- [x] 登出 → 回登录页；再访问受保护页被拦

- [x] 手动改坏 token → 401 → 自动登出回登录

> **B4 执行记录（2026-09-02，build ✓ 71 模块 / lint 0 error / 浏览器验收 A·B·C·D·E 全 PASS）：**
>
> 1. **登录/注册合为 AuthPage**（计划模板分两个文件）：两态逻辑几乎相同，合并为单文件双 tab 减重复；后端 `/api/auth/login` 与 `/api/auth/register` 请求体一致（`AuthReq{username,password}`）。后端错误 detail 英文（`invalid credentials`/`password too short (min 6)`/`username already exists: …`），前端 catch 映射为中文友好提示（已补验：错误密码→「用户名或密码不正确」）。
> 2. **登录门设计决策**：计划模板要求 `location.href='/#/login'`，但项目无 URL 路由（视图是 React state），改为事件驱动——`auth.js` 派发 `wb-auth` 事件，`RequireAuth` 监听后重渲染。落地发现 `getMode()` 的 `||'mock'` 兜底使全新用户也豁免、登录页永远不出现；修正为新增 `getModeRaw()` 区分「未选择→登录页」与「明确选过 mock→豁免」。开源用户 clone 后仍可一键演示，零配置体验不受影响。
> 3. **演示模式豁免**：RequireAuth 放行条件 = `isAuthed() || getModeRaw()==='mock'`；LIVE 未持 token → 登录页。登录/注册成功后 `setMode('live')` + `setToken`；演示按钮只 `setMode('mock')`。MOCK 下点切 LIVE 被拦截提示「需先登录」。设置页账号卡：已登录→「登出」；未登录→「去登录 / 注册」（置 live + 广播事件 → 落登录页）。
> 4. **401 自动登出**：`request()` 统一收口（api/apiGet 共用）——持 token 收到 401（过期/后端换 secret）→ `logout()` 广播 → RequireAuth 重渲染落登录页；登录页自身的 401（密码错）不触发（无 token）。
> 5. **命令面板**：已登录会话追加「账号 · 登出（用户名）」命令（演示模式无此条）。设置页新增「账号」卡（当前用户/登出/去登录）。
> 6. **验收**（浏览器自动化三轮）：A 登录门（localStorage.clear 后显示登录页）✓；B 注册→自动登录（wb-mode=live/wb-user/wb-token 非空）✓；C 登出→登录页→演示模式→切 LIVE 拦截→设置页演示态 ✓；D 坏 token→401→自动登出→token 清空 ✓；E 回归（九视图无白屏/主题持久/GridStack 拖拽+点击检索/命令面板分组导航）✓。

- [x] **Step 6: Commit**

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

- [x] **Step 1: 统一 widget 接口**

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

- [x] **Step 2: 注册表 + 占位 widget**

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

- [x] **Step 3: 渲染 widget 进 GridShell**

Modify `workbench-console/src/shell/GridShell.jsx`：children 中放置注册表 widget。先渲染 1 个 placeholder 验证可挂载：

```jsx
import PlaceholderWidget from '../widgets/PlaceholderWidget.jsx'
// GridShell 内，children 列表首项：
<PlaceholderWidget id="ph1" config={{}} refresh={() => {}} />
```

其它已迁移视图（收件箱/今天/知识等）同样包成 widget 形态放进 GridShell，使每个区域可拖拽/缩放——与 B3 布局保存联动。

- [x] **Step 4: 手动验收**

- [x] 页面出现"占位组件"widget，可随 GridStack 拖拽/缩放

- [x] 布局仍自动保存（与 B3 一致）

> **B5 执行记录（2026-09-02，build ✓ / lint 0 error / 浏览器验收全 PASS）：**
>
> 1. **健康灯接真实数据源**（与计划模板「纯空壳」有意不同，源自用户拍板的 B5 范围「+ 服务健康灯」）：`/api/health` 是免鉴权本地端点（ADR 例外清单），HealthWidget 轮询 30s + ↻ 手动探活，绿=在线/红=离线——M0-B5 唯一真实数据 widget，验证容器框架 fetch→render→refresh 全链路（Bridge 访问日志证实周期性 GET /api/health）。
> 2. **挂载位 = 用量视图**（M4 统计承接位）：`WidgetGrid` 渲染注册表 4 项——服务健康（真实）+ 知识存量/用量趋势/外部数据（占位，hint 注明 M4 接入什么，不造假数据）。计划模板的「其它视图也包成 widget」**未执行**：GridShell 约定 item 内容静态（B3），而视图内容动态（state 驱动），强行包裹违反集成约定；widget 定位是 M4 数据图表（M4-B 依赖项），非重构既有视图。
> 3. **契约**：registry entry = `{id, title, size, component, props?}`（数组保序，默认布局即数组序）；component 接收 `{tick, cfg}`——tick 由面板 ↻ bump 注入（手动刷新），cfg=entry.props。M4 接入时只换 component，容器不动。Widget.jsx 只做外壳（头部/手柄/↻/内容区），不自带 `.grid-stack-item`（GridShell 职责，B3 约定）。
> 4. **GridShell 零改动**：计划模板要求改 GridShell，实际 B3 已把它做成通用容器（items props），B5 全部复用。`client.js` 导出 `BRIDGE_ORIGIN` 供免鉴权直连（健康探测不走带 token 的 request()）。
> 5. **验收**（浏览器自动化）：4 widget 渲染 + 健康灯在线（deepseek-chat）✓；`gs.update(el,{x,y,w})` 移动/缩放（GridStack 13.2 无 move/resize，API 为 update）→ `wb-layout:usage-widgets` 写入 → 刷新后位置尺寸保持（"0,10,5"）✓，两个 widget 均验 ✓；↻ 真实重探活（服务端计数 57→61 + 网络日志双重验证）✓；回归（知识视图 4 卡 + grid-shell 计数 1、收件箱/今天/设置无白屏、无业务 JS error）✓。注：鼠标模拟拖拽在自动化环境不稳定（视口异常），布局验证改用 GridStack JS API 等价覆盖；↻ 的「检测中」过渡 <50ms 肉眼难察（本地响应快，属正常）。
> 6. **顺带（B4 review 登记项解决）**：登录「记住我」——`AuthReq.remember` → `AuthService._ttl()` 覆盖 TTL（默认 1h / 记住 30 天），前端 checkbox 默认勾选；TDD 2 测试（login/register × remember 断言 exp-iat）。登记项移交：30 天 token 存 localStorage 属本地单用户形态（ADR-0001 D2/D3），公网化需换 httpOnly cookie；↻ 可加旋转动画（打磨项）。

- [x] **Step 5: Commit**

```bash
git add workbench-console/src/widgets workbench-console/src/shell/GridShell.jsx
git commit -m "feat(widgets): M0-B5 widget 容器框架（统一接口 + 注册表 + 可挂载空壳）"
```

### M0 · 成功准则核对

> **M0 收口语（2026-09-02，43 test / coverage 85.49% / mypy、ruff 干净 / 前端 lint 0 + build 无回归）：**
> 第 2 版成真线收口——补 `test_bridge_endpoints.py`（7 个业务端点 happy path + 鉴权拒访）+ `test_usage.py`（观测模块单测，作 M4 升级 SQLite 回归基准）+ `tests/helpers.py`（fake 组件替代模块级单例，不碰真实 IO）。`fail_under` 封 85；`pythonpath=["src","tests"]` 使 CI 不再依赖 `PYTHONPATH`。剩余缺口是 ADR-0001 D5 明列的低价值胶水（Obsidian 注册表 IO / 真实 LLM 调用 / `__main__`），有意不凑数。

M0 完成标志：

- [x] 后端 CI 全绿（coverage≥85%，pytest、mypy、ruff 通过）

- [x] 前端 React 工程可构建、现有功能零回归

- [x] 注册/登录/JWT 闭环可用，未登录无法进入

- [x] GridStack 拖拽布局可保存；多主题可切换

- [x] Widget 容器已搭好接口，可挂载

- [x] ADR/架构文档/changelog 落盘

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

### M1 执行分批（2026-09-02 补写，兑现上方收口界定）

M1 体量约等于 M0 全里程碑，按 M0 惯例分 5 批执行、批批验收：

| 批次        | 范围                         | 关键产出                                                                      |
| --------- | -------------------------- | ------------------------------------------------------------------------- |
| **M1-B1** | Skill 基础设施 + 3 迁移 Skill    | `ai/skills/` 包（base/registry + classify/review/recall），等价测试证迁移无回归         |
| **M1-B2** | 2 新 Skill（decision/action） | TDD 红转绿；prompt 按六层文档设计（决策层/实践层）                                           |
| **M1-B3** | ReAct 主管 + 状态机             | 六状态图 + 三类 interrupt + resume + 守护（max\_steps/budget/human\_wait\_timeout） |
| **M1-B4** | Trace + eval runner        | domain event 落 TraceStore（回放/归因）+ golden case runner + 坏例回流               |
| **M1-B5** | Bridge 接线收口                | `POST /api/orchestrate` 主管入口 + agents.py 退役；前端接入范围届时与用户确认                 |

### M1-B1 · Skill 基础设施 + 3 迁移 Skill（逐任务 TDD）

- [x] **Step 1（红）**：`tests/test_skills.py` 先写三类断言——
  1. 注册表：3 个迁移 Skill 按名可取（B2 后补齐 5）；未知名抛 KeyError；实例满足 Skill 协议（name/description/requires\_confirmation/run）
  2. 等价迁移：同一 fake 输入下 `Skill.run` 输出 == 现有 Agent 输出（classify≈ClassifierAgent / review≈ReviewerAgent / recall≈CoachAgent）——迁移无回归的机制化证明
  3. 3 个迁移 Skill `requires_confirmation=False`（默认自主，对齐 M1-C interrupt 映射）

- [x] **Step 2（绿）**：`src/workbench/ai/skills/`——`base.py`（Skill Protocol + SkillContext + SkillResult）、`classify.py` / `review.py` / `recall.py`（逻辑迁自 agents；agents.py 不动保 bridge 兼容，B5 退役）、`registry.py`（REGISTRY 单向调度入口）

- [x] **Step 3**：全量验证 ruff / mypy / pytest --cov（fail\_under=85 不许破——新代码须被等价测试全覆盖）

- [x] **Step 4**：CHANGELOG + commit

> **B1 执行记录（2026-09-02，49 test / coverage 87.06% / ruff、mypy 干净）：**
>
> 1. **等价迁移**：skill 与 agent 在同一 fake 输入下输出逐字段相等——等价测试常驻回归（若 agent 逻辑漂移会立刻被抓）。3 个迁移 Skill 均 `requires_confirmation=False`（M1-C：classify/review/recall 高置信默认自主）。
> 2. **测试修正一处**（非实现 bug）：review 等价测试初版照抄 test\_ai 的「孤决策 in 消息」断言，但 test\_ai 用的是硬编码 fake（返回「决策备忘/孤决策 缺少关联问题」）；真实 `read_all_notes` 返回笔记**内容**，消息为「{内容} 缺少关联问题」。等价断言本身一次通过。此发现顺带揭示：engine.check\_closed\_loop 的消息以内容为标识，可读性差——登记为 M3 决策深化时顺手改（消息带文件名）。
> 3. **架构对齐**：skills 落位 `ai/skills/`（ADR-0001 D1 模块图 ai 含 Skill，单向依赖 knowledge）；`SkillResult.confidence` 默认 1.0，为 B2 decision 低置信、B3 主管判 interrupt 预留。

### M1-B2 · 2 新 Skill（decision/action）（逐任务 TDD）

> **范围界定（B2 落 Skill 侧契约，interrupt 发射归 B3 主管）**：`requires_confirmation` 标志 + 未确认零副作用 + 确认后写入是 B2 可测的全部；主管读标志/置信度发射 confirm/disambiguate/judgement interrupt 是 B3 的接线。
> 「次日跟进信号」落法：待办正文含「次日跟进」节（时间/触发条件），不另立文件夹。

- [x] **Step 1（红）**：`tests/test_skills.py` 扩写 + `tests/test_ai.py` 补引擎边界测试——
  1. 注册表扩到 5（decision/action 入表）；协议标志：action `requires_confirmation=True`，其余 4 个 False
  2. decision：高置信 happy（options/lean/clarify 透传，needs\_judgement=False）；低置信 → needs\_judgement=True（拍板标记）；confidence 非法值按 0.0 处理（LLM 边界防御）
  3. action：未确认 run **零副作用且幂等**（重复调用不写库，status=needs\_confirmation 且带预览）；确认后写决策备忘（正文含「关联问题」——review 闭环契约）与待办（正文含「次日跟进」）
  4. engine 新方法 `analyze_decision`/`draft_note`（决策层/实践层 prompt）：FakeLLM 测 JSON 边界（合法/非法 JSON/非 dict 三态回退）

- [x] **Step 2（绿）**：`engine.py` 补两方法（prompt 按六层文档的决策层/实践层措辞，JSON 解析+回退）；`ai/skills/decision.py`、`ai/skills/action.py`；registry 扩 5

- [x] **Step 3**：全量验证 ruff / mypy / pytest --cov（fail\_under=85 不许破）

- [x] **Step 4**：review（用户批内指令）+ CHANGELOG + commit

> **B2 执行记录（2026-09-02，64 test / coverage 89.11%（engine、skills 包均 100%）/ ruff、mypy 干净）：**
>
> 1. **TDD 红**：12 failed（registry 5 项 + decision 3 + action 3 + engine 5 方法缺失）→ 绿。
> 2. **review 抓到两个真 bug（均已修 + 补测试）**：
>
>    - **「待办」撞 Vault 白名单**：`VaultStore.ALLOWED_FOLDERS` 不含「待办」，确认写入必 ValueError——初版测试用 RecordingVault 假仓库测不出来（fake 太松）。修复：action 显式 `KIND_FOLDERS` 映射（待办→行动记录，六层框架实践层目录）+ 未知 kind 入口即拒（不论确认与否）；测试改用**真 VaultStore**（tmp\_path 落盘），白名单契约进入测试防线。
>
>    - **合法 JSON 字段残缺 → KeyError**：LLM 返回 `{"confidence": 0.9}` 这类残缺结构时 `analysis["options"]`/`draft["title"]` 直接崩。修复：engine 改 defaults 合并（`{**defaults, **data}`），已有字段透传、残缺字段兜底；补 2 个 shape-miss 测试。LLM 是系统边界，残缺 JSON 是比非法 JSON 更常见的失败模式。
> 3. **顺手关闭存量覆盖缺口**：`AIEngine.check_closed_loop` 循环体（63-67 行）此前所有测试都用 FakeEngine 绕过、真 engine 这段规则逻辑零直测——补 1 测，engine.py 至 100%。
> 4. **契约落点**：decision 输出 `needs_judgement`（<0.6）+ clarify（B3 映射 disambiguate/judgement）；action 未确认零副作用（幂等）+ 预览带起草内容（B3 confirm interrupt 直接可展示）；决策备忘正文含「关联问题」（review 闭环契约）、待办正文含「次日跟进」（跟进信号落在正文，不另立文件夹）。
> 5. **六层 prompt**：decision=决策层（结构化追问+多维分析，confidence 反映信息充分度）；action 起草=实践层（备忘三节「背景/决定/关联问题」、待办两节「下一步/次日跟进」，「不编造用户没给的事实」）。

### M1-B3 · ReAct 主管 + 状态机（逐任务 TDD）

> **设计落地（兑现 M1-A/B 骨架，2026-09-02 补写）：** `ai/policy.py`（策略=主管的"想"）+ `ai/orchestrator.py`（状态机=主管的"行"）。M1 策略为**确定性规则路由**（ReAct 框架先立、Thought 为规则；LLM 自由规划留 M5+ 评测水位后）——保证可测、可回放。
> **recall 收尾：** 每个流程以 recall 结束并把结果附在 Finish 输出（"带着经验回来"）——B5 退役 agents.py 后主管必须承接召回职责，否则召回能力随退役消失。
> **human\_wait\_timeout 语义：** 超时按"放弃"→DONE（非 ERROR；对齐状态表"放弃→DONE"，且此时无副作用，安全）。
> **resume 安全默认：** 非 approve 的裁决一律不触发写库（宁可不写，不可误写）。

- [x] **Step 1（红）**：`tests/test_orchestrator.py` ——
  1. 决策 happy path 全链：classify→decision→action 草稿→confirm interrupt→resume approve→written→recall→finish；断言 TurnResult、Vault 落盘（1 张备忘）、事件名序列与 tool 序列
  2. 三类 interrupt：judgement（低置信；approve 继续 / reject 不写库）、confirm（reject / 非法 action 均不写库——安全默认）、disambiguate（未知标签→候选五类→pick 路由；无效 pick 结束）
  3. abandon：等待中放弃→DONE 不写库；human\_wait\_timeout：超时→DONE（放弃语义）+ 未超时正常 resume
  4. 守护：max\_steps（LoopPolicy 循环策略）/ budget（自动推进假钟）/ 空输入→ERROR / 技能异常→ERROR / 策略异常→ERROR / 非法 resume 与运行中重入→RuntimeError
  5. 事件链完整性：相邻事件 state\_to==state\_from、首事件自 IDLE、末事件至 DONE/ERROR；DONE 后重开新回合（DONE→INGEST，轨迹清零）

- [x] **Step 2（绿）**：`ai/policy.py`（RunSkill/Interrupt/Finish 指令 + RunView 轨迹视图 + RulePolicy 五类路由）+ `ai/orchestrator.py`（六状态 + 每跳 DomainEvent + 主管级 interrupt 接线（action needs\_confirmation→confirm；decision needs\_judgement→judgement）+ resume + Guards 三守护）

- [x] **Step 3**：全量验证 ruff / mypy / pytest --cov（fail\_under=85 不许破）

- [x] **Step 4**：review + CHANGELOG + commit

> **B3 执行记录（2026-09-02，88 test / coverage 92.00% / ruff、mypy 干净）：** 实现 ReAct 主管状态机（六状态流转）+ RulePolicy 确定性路由 + 三类 interrupt 接线 + DomainEvent 事件链；24 个测试覆盖 happy path/中断/resume/守护/事件链完整性/各标签路由。**review 抓到 1 个真 bug 并修复**：budget\_seconds 计入了人机等待时间（用户思考 10 分钟后 approve 会被误判 "budget exceeded"）——守护语义是机器时间，resume 时重置计时起点；补 2 测试（budget 不计等待时间、ERROR 后重开回合——docstring 声明但未测）。另确认：`ruff format` 非项目门槛（CI 只跑 `ruff check`），存量格式漂移不动以免混批次。

### M1-B4 · Trace + eval runner（逐任务 TDD）

> **设计落地（兑现 M1-A 修正 A + 评测水位选项 1，2026-09-03 补写）：** `ai/trace.py`（观测层：TraceStore 落盘/回放/归因）+ `ai/eval.py`（最小 golden case runner + 坏例回流）。
> **类型解耦（防循环依赖的关键）：** trace 只认 **dict**（JSON 形态的事件），不 import DomainEvent 类——orchestrator 运行时 import trace（save 时 asdict 转换），trace 零反向依赖；观测层连事件类都不知道，修正 A"trace 不是执行语义"在类型层面落实。
> **存储格式：** 一 run 一 JSON 文件（`{run_id}.json` = meta + events）；run\_id = `时间戳-短哈希`（文件名即排序键）。不用 SQLite：trace 是 append-only 时序记录，个人规模无需聚合查询（usage 走 SQLite 是 M4 聚合统计诉求，二者不同）。
> **接线（修正 A 落实）：** Orchestrator 可选注入 `trace: TraceStore`，在进入 **WAITING\_HUMAN / DONE / ERROR 三个观测点**时快照落盘（同 run\_id 覆盖——resume 续写同文件，崩溃时保留上一稳定点）；**写 trace 失败静默不杀任务**（灵魂测试：ExplodingStore 抛 OSError，任务照常完成）。
> **归因最小版：** `attribute_failure(events)` —— error 事件定位（reason + 出错前最后 tool + at\_seq）+ 低置信步骤收集（阈值 import DecisionSkill.CONFIDENCE\_THRESHOLD，不复制魔法数）。
> **坏例回流：** `case_from_trace()` 从 trace 提取 input/script（classify 标签、decision 分析、action 草稿、review 缺失项）/resumes（interrupt 裁决序列），生成 GoldenCase——expect 从当前结果起草、人工校对为正确行为；回流产物落 `workbench/evals/golden/*.json`（一 case 一文件），`test_eval.py` 扫目录全量跑——golden case 即 CI 回归。

- [x] **Step 1（红）**：`tests/test_trace.py` + `tests/test_eval.py` + `evals/golden/` 5 初始 case ——
  1. trace：save/load roundtrip（dict 事件链 + meta）；waiting 快照 → resume 覆盖同 run\_id（终态完整链）；list\_runs 最新在前；重开回合新 run\_id 旧文件保留；verify 好链 \[] / 断链报问题；attribute\_failure 定位 error 与低置信
  2. **修正 A 灵魂测试**：ExplodingTraceStore.save 抛 OSError → 任务照常完成、笔记照常落盘、不抛异常
  3. eval：run\_case 通过/失败（failures 带原因）；judgement 双 resume 全链 case；GoldenCase JSON roundtrip；坏例回流（CaseEngine 生成 trace → case\_from\_trace → 重放通过=行为固化）
  4. golden：`evals/golden/` 5 case（决策确认写入/低置信驳回/复盘扫描/澄清选实践/空输入 ERROR）扫目录全过——进 CI 回归

- [x] **Step 2（绿）**：`ai/trace.py`（TraceStore/Trace/verify/attribute\_failure）+ `ai/eval.py`（GoldenCase/CaseEngine/CaseVector/run\_case/run\_cases/case\_from\_trace/load\_cases）+ orchestrator 接线（run\_id 生成 + 观测点快照 + 静默容错）

- [x] **Step 3**：全量验证 ruff / mypy / pytest --cov（fail\_under=85 不许破）

- [x] **Step 4**：review + CHANGELOG + commit

> **B4 执行记录（2026-09-03，117 test / coverage 93.61%（trace.py、eval.py 均 100%）/ ruff、mypy 干净）：** TraceStore（一 run 一 JSON）+ verify/attribute\_failure + 最小 eval runner + 坏例回流（decision/review/实践/等待快照/ERROR 五类提取路径全测）。**review 三个发现均处置**：1) mypy 抓出 SkillContext 类型债（engine/vector 标注具体类，CaseEngine 结构兼容但类型不符）——改为 EngineLike/VectorLike 结构协议，"Skill 只从 ctx 拿能力"在类型层落实；2) 回流核心分支（decision analysis 提取去 needs\_judgement、review\_missing、related 脚本化、等待快照 expect）初测遗漏——补 7 测后两模块 100%；3) case.id 拼路径存在目录逃逸（外部 JSON 数据边界）——run\_case 入口即拒。**无逻辑 bug**（B3 建立的模式直接复用）。类型解耦验证：trace 只认 dict 零反向依赖，无循环 import。

### M1-B5 · Bridge 接线收口（逐任务 TDD）

> **设计落地（2026-09-03 补写）：** 主管入口 + agents.py 退役；**前端接入不在本批**（按批次表约定，接入范围完成后与用户确认）。
> **`POST /api/orchestrate`（{text} 起新回合）+** **`POST /api/orchestrate/resume`（{run\_id, decision} 续回合）**：Orchestrator 有状态，HTTP 无状态——bridge 持会话注册表 `_sessions: dict[run_id, Orchestrator]`；**终态（DONE/ERROR）即删**（不可 resume → 404，注册表不变式保证 resume 永不撞 RuntimeError）+ cap 50 最旧先出（防放弃等待的会话泄漏）。响应 = run\_id/status/state/output/interrupt/events（asdict 全链——事件链本就是给前端渲染的观测数据）。
> **写入即索引（产品契约补漏）：** create\_note 端点写笔记后同步向量索引，但 action Skill 确认写入不索引——agent 写的笔记检索不到，召回闭环断。契约落在 **Skill 层**（所有入口一致：orchestrate/未来 MCP）：action 确认写入后 `ctx.vector.add(...)`；VectorLike 协议补 `add`，CaseVector/测试 fake 补 no-op add。
> **agents.py 退役（等价测试使命完成）：** bridge 三端点（classify/scan/reopen）迁 skills，**响应契约不变**（前端 LIVE 模式每天在调）；main.py/mcp\_server.py 迁 skills（ctx 从 dict 改 SkillContext 直传）；`ai/__init__.py` 去 agent 导出；B1 等价测试改为直接断言（agents 删除后对照对象消失，等价使命已完成）。
> **TraceStore 接线：** bridge `.data/traces`（.data 已 gitignore）；测试 monkeypatch `bridge.skill_ctx`/`bridge.trace_store`（CaseEngine 脚本化，不碰真 LLM/Vault）。

- [x] **Step 1（红）**：`tests/test_bridge_orchestrate.py`（新）+ `tests/test_bridge_endpoints.py` 改写 + `tests/helpers.py`（ScriptEngine/fake\_skill\_ctx/FakeVault.read\_all\_notes）+ `tests/test_skills.py`（去 agent 等价改直接断言；FakeVector 补 add 记录器；action 确认写入补**索引断言**）+ `tests/test_ai.py`（删 2 个 agent 测试）+ `tests/test_orchestrator.py`/`test_mcp_server.py`（fake/入参适配）——
  1. orchestrate：无 token 401；happy path（waiting\_human + confirm interrupt + run\_id → resume approve → done written + Vault 落盘 1 张 + trace 落盘）；resume reject → done 不写；resume 未知 run\_id → 404；终态后再 resume → 404；空输入 → 200 + status=error（回合错误是数据不是传输错误）
  2. 三旧端点：monkeypatch skill\_ctx 后响应契约不变（label/missing/results）
  3. action 索引契约：确认写入 → vector.add(title, content, path) 被调用（红：现未实现）

- [x] **Step 2（绿）**：`bridge.py`（skill\_ctx + 会话注册表 + 两新端点 + 三端点迁 skills）+ `action.py`（写入后索引）+ `base.py`（VectorLike.add）+ `eval.py`（CaseVector.add）+ `main.py`/`mcp_server.py`（迁 skills）+ `ai/__init__.py` + **删除** **`agents.py`**

- [x] **Step 3**：全量验证 ruff / mypy / pytest --cov（fail\_under=85 不许破）

- [x] **Step 4**：review + CHANGELOG + commit + 与用户确认前端接入范围

> **B5 执行记录（2026-09-03，123 test / coverage 93.61% / ruff、mypy 干净）：** 主管入口（orchestrate/resume + 会话注册表终态即删 + cap 50）+ agents.py 退役（bridge/main/mcp\_server 全迁 skills，三旧端点响应契约不变有测试锁定）+ 写入即索引契约落 Skill 层。**review 抓到 1 个并发缺陷并修复**：FastAPI 同步 handler 跑线程池，双击 approve 的并发 resume 第二个请求撞「resume() 非法状态」RuntimeError → 500（并发 prune 还有重复删 key 的 KeyError 风险）——查表+resume+prune 整体持锁串行化，后到者 404。**M1 全部 5 批完成**；前端接入范围待用户拍板（响应已透出 events 全链，前端渲染自由度充足）。

### M1 · 成功准则核对

M1 完成标志：

- [x] ReAct 主管 Orchestrator 存在，状态图（IDLE/INGEST/ACTING/WAITING\_HUMAN/DONE/ERROR）可跑

- [x] 5 个 Skill（classify/decision/action/review/recall）全部注册进注册表，从注册表按名可取

- [x] 3 个现有 Agent（Classifier/Reviewer/Coach）行为迁移无回归（单测断言等价）（B1 等价测试）

- [x] 2 个新 Skill（decision/action）有红转绿测试

- [x] action 写 Vault 前触发 confirm interrupt；decision 低置信触发 disambiguate/judgement（B2 已落 Skill 侧契约：标志/零副作用/拍板标记；interrupt 发射归 B3 主管）

- [x] 每跳产生 domain event，Trace 可回放、坏例可归因

- [x] 最小 eval runner 能跑 golden case（通过/失败）；坏 Trace 可回流为回归 case

- [x] 执行守护（max\_steps/budget/human\_wait\_timeout）生效

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

### M2 执行分批（2026-09-03 补写）

M2 体量约为 M1 一半，分 2 批执行（前端接入按用户拍板攒到 M4）：

| 批次        | 范围        | 关键产出                                                                                       |
| --------- | --------- | ------------------------------------------------------------------------------------------ |
| **M2-B1** | 双链管线      | link Skill（三档阈值分流）+ engine.judge\_link + action 接收 links 写入 + 主管编排 + vector.search 补 score |
| **M2-B2** | hash 增量索引 | knowledge/indexer.py（content\_hash + sync\_vault 增量同步）+ 写卡路径带 hash + /api/sync\_vault 端点   |

### M2-B1 · 写卡自动双链管线（逐任务 TDD）

> **设计落地（2026-09-03 补写）：**
> **link 是第 6 个 Skill（不是 policy 内部函数）：** 决策 3"该链到谁由主管编排"落在 policy 的路由顺序上（action 草稿 → recall 候选 → link 决策 → confirm → 写入），但 link 决策本身 Skill 化——天然拿 ctx.engine（LLM 边缘判断）、steps 里有记录（trace/eval 可回放）、不破坏 policy 纯函数性。
> **主管级 interrupt 接线挪进 policy：** M2 后草稿 action 的 needs\_confirmation 不再立即触发 confirm（要先 recall+link），orchestrator 的硬编码接线（action/decision 两处）删除，全部由 policy 返回 Interrupt 指令——orchestrator 变纯执行器，policy 是唯一"想"的场所（B3 接线职责没变，位置归位）。
> **vector.search 补 score：** Chroma cosine 距离 → score = 1 - distance；响应加字段向后兼容（前端不读即忽略）。
> **三档语义（对齐 M2-A 管线）：** score≥0.85 auto（直接链，零 LLM）；0.75\~0.85 喂 LLM（judge\_link 返回 {link\_to, confidence}，**非法 JSON/残缺默认不链**——宁可不链不可误链）；<0.75 pending\_review（不自动链，confirm 时透出给用户）。去重（同标题留最高分）+ 排除草稿正文已有的人工 \[\[链]]（尊重显式边）。
> **action 写入规范扩展：** args 增 `links`（auto 档标题列表）；写入时正文追加「## 关联」节渲染 `[[标题]]`；正文已有人工链不重复；无 links 不加节。confirm interrupt payload 扩为 {preview, links, pending\_review}。
> **编排后序列（决策流）：** classify → decision → action 草稿 → recall(top\_k=20) → link → \[confirm] → approve → action(confirmed, links) → recall(收尾)。存量 golden case / orchestrator 测试的 tools 序列全部更新（预期内行为变更）。

- [x] **Step 1（红）**：`tests/test_skills.py`（link 三档/去重/人工链排除/judge\_link 边界；action links 渲染/无 links 不加节/人工链去重；注册表 6）+ `tests/test_ai.py`（engine.judge\_link JSON 三态：合法/非法→不链/残缺→默认）+ `tests/test_vector.py`（search 返回 score）+ `tests/test_orchestrator.py`（新序列 + confirm payload 含 links + 驳回不写不变）+ `evals/golden/` 5 case 序列更新 ——
  1. link：三档分流（0.9→auto 零 LLM；0.8→走 judge\_link，approve→链 / reject→不链；0.6→pending\_review）；同标题去重留最高分；草稿已有 \[\[X]] 则 X 排除
  2. action：links=\[A,B] → 正文含「## 关联」+ \[\[A]] + \[\[B]]；正文已有 \[\[A]] → A 不重复；links 空/缺 → 无关联节
  3. 编排：决策 happy path 全链序列（含 recall+link）；confirm payload 带 links/pending\_review；驳回仍零写入；judgement 双 interrupt 串行流
  4. eval：golden 序列更新后全过；回流 case（case\_from\_trace）重放通过

- [x] **Step 2（绿）**：`ai/skills/link.py` + `engine.py`（judge\_link）+ `action.py`（links 渲染）+ `policy.py`（路由 + Interrupt 收编）+ `orchestrator.py`（删硬编码接线）+ `vector.py`（score）+ registry/CaseEngine/回流适配

- [x] **Step 3**：全量验证 ruff / mypy / pytest --cov（fail\_under=85 不许破）

- [x] **Step 4**：review + CHANGELOG + commit

> **M2-B1 执行记录（2026-09-03）：** 145 test 全过（+22），coverage 93.96%（link.py / policy.py 100%），ruff / mypy 干净。review 发现并修复 2 处缺陷：① vector.search 距离缺失兜底原为 0.0（→score=1.0 会误进 auto 档自动建链），改兜底最大距离并补回归测试；② engine.judge\_link 喂料与 M2-A 设计不符（原喂全文且不带 score），改 200 字截断摘要 + score 进 prompt 并补 PromptCapture 回归测试。存量断言修正两处：test\_skills「## 关联」改行级正则（区分「## 关联问题」契约节）；test\_vector score 绝对值断言改相对排序（本地哈希 embedding 量纲低于语义模型，不绑量纲）。

### M2-B2 · hash 增量索引（逐任务 TDD）

> **设计落地（2026-09-03 补写）：** `knowledge/indexer.py`——content\_hash（sha256）存 Chroma metadata；`sync_vault(vault, vector)` 扫 Vault 白名单目录，hash 命中跳过 / 变更重算 / 新增入库（upsert 语义，**不处理删除**——最小版，删除卡留全量重建）；写卡路径（action / create\_note 端点 / MCP）add 时带 content\_hash。bridge `POST /api/sync_vault`（鉴权）供首次初始化与手动重建。SyncReport{added, updated, skipped} 可观测。

- [x] **Step 1（红）**：`tests/test_indexer.py`——首次 sync 全量入库；二跑全 skipped（hash 命中零重算）；改一张卡只 updated 该卡；新增卡 added；写卡路径 metadata 带 content\_hash

- [x] **Step 2（绿）**：`knowledge/indexer.py` + vector.add 带 hash + 三入口接线 + bridge 端点

- [x] **Step 3**：全量验证

- [x] **Step 4**：review + CHANGELOG + commit

> **M2-B2 执行记录（2026-09-03）：** 153 test 全过（+8），coverage 94.16%（indexer.py 100%），ruff / mypy 干净（30 源文件）。实现简化一处：hash 由 `VectorStore.add` 内部计算落 metadata（三写卡入口零改动即满足"写入即带 hash"，单点计算免三处重复）；两个关键设计约定——doc\_id 与写卡路径同款 `note-{stem}`（互认不产重复条目，action 写卡后 sync 直接 skipped 有集成测试）、hash 只算正文（写卡索引真实标题、sync 从文件名剥日期前缀推标题，含标题会无限"更新"）。零重算证明走 monkeypatch 计数 upsert：二跑零次、改一张恰一次。已知限制按最小版登记：不处理删除/改名、同名 stem 跨目录遮蔽（见 CHANGELOG 0.15.0）。

### M2 · 成功准则核对

M2 完成标志：

- [x] action 写卡流程接入了"M1 recall 召回候选 → 阈值/LLM 决策 → 带双链写入"的管线

- [x] 高置信(≥0.85)新卡自动生成 `[[链接]]`，不消耗 LLM

- [x] 边缘(0.75\~0.85)仅喂 LLM 标题+摘要+score，返回结构化 JSON

- [x] 低置信(<0.75)不自动链，标记待人工

- [x] hash 增量索引：改一张卡只重算该卡，不全文重扫

- [x] Obsidian 已有人工双链被尊重（显式边），AI 相似边为其补充（隐式边），合成一张网

- [x] 写卡/改卡重复操作不重复计算 embedding（hash 命中即复用）

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

> **业界核实（经 Explore 检索 decision-journal-template / adr-madr / open-recall / Metadata-Aware-Rag / git-vault-protocol 等）：** M3-A/B/C 三件套属正统主流路线。额外收获：决策记忆建议分"原文层/结构化摘要层/检索索引层"三层；检索重排用 relevance/证据完整度/时效，**结果质量只作展示角标、绝不作排序键**（反结果偏误）；Chroma 支持 metadata filter，但过滤缺失字段会报错/漏召回——故本项目对**存量无 type 字段**的库不做硬过滤（见决策 7）。

### M3 · Step 0 写码边界清单（2026-09-03 定点研究落地，写码前逐条对照）

> 方案 C+A：对 M3 做过一轮定点 Explore（decision-journal-template / adr-madr / 元数据感知 RAG / 反结果偏误），产出直接灌成下面这份**检查表**。目标是"一次做对"，把 review 返工（如 M2 的距离兜底/喂料边界两处）压到最低。

**用户拍板 + 研究新决策（写码必须遵守）：**
- **决策 6（schema 口径，用户已定）**：**保持两栏** `actual_outcome + result_quality`，**不拆** `decision_quality` 栏；"决策过程质量 vs 结果好坏"的区分与反结果偏误靠 **prompt 措辞**实现，不靠加字段。
- **决策 7（检索口径）**：`recall` **不做 metadata 硬过滤**——旧卡无 `type` 字段会漏召回（Chroma 过滤缺失字段会报错/无结果），违反"存量宽容"。一律向量全量召回后，把历史结果当作**展示维度**透出，**绝不当排序键**（规避结果偏误 + 兼容存量）。
- **决策 8（enum 规范化）**：`actual_outcome` 只用 `success / failure / inconclusive / unknown`（缺省 `unknown`，宁缺毋猜）；`result_quality` 用 `good / medium / poor / unknown`；中文解释一律放 `*_note` 字段；日期严格 ISO 8601；含中文/冒号/特殊字符的值加引号。

**检查表（每完成一项打勾）：**
1. [ ] frontmatter 只允许文件**顶部一组** `---`；正文里的 `---`（分段/代码块）不得截断正文——解析失败时**丢 meta 不丢正文**，正文照常可读可检索
2. [ ] enum 写死英文值、中文防引号；日期 ISO；不把自然语言写进枚举字段
3. [ ] 新决策备忘**落盘与索引用同一份含 frontmatter 的正文**（对齐 M2 教训：index 与 disk 渲染分裂会造成无限"更新"）
4. [ ] 结果不确定一律 `unknown`，硬盘不硬猜；"有结论 ≠ 有决策"；不因"失败/风险"等词硬映射 result 字段
5. [ ] `recall` 不禁 metadata 硬过滤；历史结果只作展示、不作排序键
6. [ ] prompt 显式区分"决策**过程**质量"与"结果好坏"，指令式措辞（禁止"因结果好而高估决策逻辑"、"因结果差否定过程"）
7. [ ] 存量旧卡不强制改写字段（宽容读取、缺失→unknown），仅新卡走强 schema

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

- [x] 新写决策备忘带 M3-A frontmatter 结构（含 outcome 与 result\_quality）（B2）

- [x] decision 只消费 recall 参照、不自己检索（R1 单向依赖）（B1）

- [x] decision 输出含"可选方案 + 历史参照成败对照 + 倾向"（B1）

- [x] 参照注入为结构化经验卡摘要、非全文（B1）

- [x] **反结果偏误**：不按 outcome 过滤成功案例；prompt 区分决策逻辑 vs 结果好坏（B1）

- [x] 存量决策备忘宽容处理（启发式推断 outcome，不强制改写）（B1 不硬过滤不强判 + B2 parse 宽容读回缺省 unknown，原文不改写）

- [x] 主管能编 classify→recall→decision→action 决策链路（B1）

- [x] recall 全量向量召回历史参照，结构化摘要进 decision；历史结果仅作展示维度、不作排序键（决策 7，反结果偏误）（B1）

### M3 执行分批（2026-09-03 补写）

M3 体量≈M2，分 2 批执行，每批走 check 表 + 逐任务 TDD：

| 批次 | 范围 | 关键产出 |
| --- | --- | --- |
| **M3-B1** | 决策带历史参照（R1 单向依赖） | 编排后序列加 recall → `decision` args 接收 `history`；`engine.analyze_decision(text, history)` 注入结构化历史经验对照（非全文）+ 反结果偏误 prompt；`decision` 输出含"方案+历史对照+倾向" |
| **M3-B2** | 决策备忘 frontmatter（两栏） | `draft_note` 决策备忘生成两栏 enum frontmatter（决策 8）；action 落盘与索引同源含 frontmatter（check 3）；读回解析丢 meta 不丢正文；存量宽容缺省 |

### M3-B1 · 决策带历史参照（逐任务 TDD）

- [x] **Step 0（check）**：核对上文 Step 0 边界清单——B1 只做"注参照"，不做 frontmatter/写库（归属 M3-B2）；recall 不做硬过滤（决策 7）
- [x] **Step 1（红）**：`tests/test_skills.py`（decision 收 history、无 history 兼容）+ `tests/test_ai.py`（注入为 200 字截断摘要+score 保序、无 history 不产生空参照块、反结果偏误 prompt 措辞、history_view 字段兜底）+ 新增 `tests/test_policy.py`（决策流 recall(history)→decision(history) 路由 + recall 三档用途 purpose 键互不串档 + 实践流无历史召回 + 收尾档）+ `tests/test_orchestrator.py`（新序列 + decision 收到参照）+ golden 2 个决策 case 序列更新——14 失败全部指向"history 未接入"，红得正确
- [x] **Step 2（绿）**：`ai/skills/decision.py`（args.history 透传，R1）+ `engine.py`（analyze_decision 收 history：结构化摘要注入非全文 + 反结果偏误 system 措辞 + 输出契约扩 history_view）+ `policy.py`（_decision_flow 前置 recall(history)；recall 三档用途统一为 args.purpose 键：history/candidates/finish，缺省 candidates 兼容旧步）+ `base.py` 协议 + `eval.py` CaseEngine 签名
- [x] **Step 3**：全量验证 ruff / mypy / pytest --cov——167 test 全过（+14），coverage 94.19%，ruff / mypy 干净
- [x] **Step 4**：review（对照 check 表逐条，重点：history 注入边界/三档串档/反偏误措辞/回流 script.related 双召回覆盖语义）+ CHANGELOG + 提交

> **B1 执行记录（2026-09-03，167 test / coverage 94.19% / ruff、mypy 干净）：** 决策流前置 recall(history) 注入结构化历史参照（标题+200 字截断+score 非全文）+ 反结果偏误 system 措辞 + 输出契约扩 history_view；recall 三档用途统一 args.purpose 键。**review 逐条通过、零返工**：① 注入边界——601 字全文不进 prompt 有断言，无 history 时 prompt 为原文不产生空参照块；② 三档串档——purpose 键隔离 + 旧步缺省 candidates（运行态无跨进程持久化，无兼容风险）；③ 反偏误措辞——过程/结果分开、运气、未知不强行判断三要素均有 PromptCapture 断言固化；④ 回流 script.related last-wins 为 M2 起既有语义非本批回归（回放时 decision 分析由 script 固化、link 未命中 title 安全默认不链），登记 M5+ 评测水位提升时改进。额外确认 loop 安全：decision 一次性触发、judgement reject → finish 不回环、max_steps 兜底仍在。

### M3-B2 · 决策备忘 frontmatter（两栏）（逐任务 TDD）

- [x] **Step 0（check）**：核对 Step 0 清单 1/2/3/4/7（frontmatter 解析边界 + enum + 落盘索引同源 + 宁缺毋猜 + 存量宽容）
- [x] **Step 1（红）**：新增 `tests/test_frontmatter.py`（encode/parse roundtrip、特殊值引号、正文 `---` 不截断、无闭合丢 meta 保正文、存量无 frontmatter、烂行宽容跳过、缺字段缺省 unknown、enum_or_unknown 严格）+ `tests/test_ai.py`（draft_note 决策备忘两栏 frontmatter、待办不加、LLM 污染 enum 被强制 unknown、meta 残缺骨架仍全、bad JSON 保骨架原文不丢）+ `tests/test_indexer.py`（DraftEngine 升级含 frontmatter + 落盘/索引同源直接断言 + 改 frontmatter 一栏触发重算）——3 文件 collection error 全指向 frontmatter 模块缺失，红得正确
- [x] **Step 2（绿）**：新增 `ai/frontmatter.py`（encode/parse/enum_or_unknown，零 YAML 依赖：键值行 + json.dumps 引号）+ `engine.py`（draft_note 决策备忘分支合成 frontmatter：type/date/两栏 enum 代码生成 + LLM 只提炼自然语言栏；待办不加）。**action.py / indexer.py 零改动**——同源 M2-B1 已建（单一 content 变量），hash 只算 content 天然含 frontmatter，测试证明
- [x] **Step 3**：全量验证 ruff / mypy / pytest --cov——186 test 全过（+19），coverage 94.25%，ruff / mypy 干净（31 源文件）；修一处 mypy 类型窄化（三元表达式 `.get()` 的 isinstance 窄化不持久，拆两步）
- [x] **Step 4**：review + CHANGELOG + 提交

> **B2 执行记录（2026-09-03，186 test / coverage 94.25% / ruff、mypy 干净）：** 决策备忘新卡带两栏 enum frontmatter（M3-A 结构，lesson 留复盘后填）；两栏与 type/date 由代码生成（新决策结果未发生 → unknown 是事实非猜测，LLM 不参与，污染测试证明）；LLM 只从输入提炼自然语言栏。**review 确认**：① 解析边界——顶部一组 `---`、正文 `---` 原样保留、无闭合丢 meta 保正文、烂行跳过；② 同源——落盘==索引直接断言 + sync hash 命中 + 改 frontmatter 一栏恰重算一次；③ 存量宽容——parse 只读不改写，create_note/MCP/手写卡路径不加 frontmatter（强 schema 只强 AI 起草的新卡）；④ vault.\_frontmatter\_tags 与新格式无冲突（list\_tags 查知识卡片目录，决策备忘 frontmatter 无 tags 键返回空）。CaseEngine（eval 回放）draft 不拼 frontmatter——脚本回放非真起草，golden 断言不涉及，留待 M5+ 需要时扩展。

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

### M4 · Step 0 写码边界清单（方案 C 定点研究落地，2026-09-03）

**研究来源（定点 Explore 两路）：** ①SQLite 用量持久化——LiteLLM `DailyUserSpend` 日聚合表先例（v1.65.0 为百万日志后减查询负载而引入）、Langfuse observation 模型（归因字段直接落明细每行，不事后推断）、SQLite WAL 语义、Python contextvars 在 ThreadPoolExecutor **不自动传播**（FastAPI 同步 handler 跑线程池 → 隐式归因会丢）；②极简 dashboard——uPlot ~50KB min 零传递依赖（canvas、时间序列专用）vs recharts ~500KB 级多依赖 vs 手写 SVG/CSS（分类 ≤10、趋势点 ≤30 在手写上限内）；聚合端点惯例、趋势补零语义、降级三层 state。

**用户拍板（M4 决策 6/7）：**

- **决策 6（图表方案）**：引入 **uPlot**（~50KB min、零传递依赖、canvas 时间序列专用）——分类分布柱状 + 趋势折线均走 uPlot；不引 recharts/chart.js（体积与依赖树和极简哲学冲突）；KPI 数字卡（卡片总数/累计成本等）不画图。

- **决策 7（端点形态）**：**单一聚合端点** `GET /api/stats?include=knowledge,usage&range=7d|30d` 替代原 6 细分端点草稿（个人 dashboard 请求数最小化）；`/api/usage` 明细端点保留且响应形状不变；stats 端点走 `require_auth`（业务端点统一鉴权）。

**研究新决策（写码必须遵守）：**

- **决策 8（快照时机）**：写时 upsert——每次 record 与当日快照 upsert **同一事务**（原子，快照天然新鲜）；**趋势查询一律走快照表**（30 天趋势 = 30 行直查，永不重算全表——取代原"近 7 天实时查明细 + 更久查快照"双口径：写时 upsert 下快照即当日终值，双口径是无谓复杂度）；快照缺失日**读时从明细聚合补齐**（兜底迁移/异常场景）；不引 cron/APScheduler/后台线程。

- **决策 9（时间与金额）**：`ts` 本地 ISO8601 文本（`YYYY-MM-DDTHH:MM:SS`）、快照 `date` 本地日期串；**日界全部 Python 侧计算**（`datetime.now()` 本地时间），SQL 内禁用 `date('now')`/`datetime('now')`（SQLite 默认 UTC，日界会漂移）；`cost` REAL 元直存；`status` 两档 success/error（沿用 record_tool 的 ok 语义）。

- **决策 10（归因）**：**显式参数贯穿，不用 contextvars**（FastAPI 同步 handler 跑线程池，contextvars 不自动传播，隐式归因会串档/丢失）——engine 各方法显式把 skill 名传给 `complete(..., skill=...)` → `record_llm(skill=...)`；`source` 由 bridge middleware 按端点名记（orchestrate/classify_text/…）。

- **决策 11（连接）**：per-call `sqlite3.connect` + `closing()`（对齐 auth/repository.py 库内先例，天然线程安全）+ `PRAGMA journal_mode=WAL`（UI 边查边写降锁竞争）；不建连接池、不引 SQLAlchemy。

- **决策 12（明细永存）**：`MAX_EVENTS=200` 退役；明细不删（个人规模一年千行级）；`/api/usage` 事件列表改查 SQLite `ORDER BY id DESC LIMIT 50`，**响应形状不变（前端零改动）**；totals 改为快照全表聚合（口径从"本进程"升级为"全部历史"，形状不变）；不做内存→SQLite 历史搬迁（内存数据本就易失，无搬迁价值）。

- **决策 13（响应形状）**：分布 `[{name, count}]` 按 count 降序；趋势 `[{date, value}]` **缺失日补零**（折线渲染稳定 + 断档可见，优于跳过）；`range` 只认 `7d|30d`（非法值 422，FastAPI Query 校验）。

- **决策 14（知识趋势数据源）**：文件名日期前缀（vault 写卡惯例 `{YYYY-MM-DD}-{title}.md`，indexer 同款解析口径），不读 mtime、不遍历解析 frontmatter；无日期前缀的存量文件不计趋势（宽容，不改写存量）。

- **决策 15（前端降级与刷新）**：三层 state（null/data/mock）+ 既有 toast 机制（bridgeDown 同款位置与文案风格）；刷新走容器既有 ↻ tick 手动刷新，**不加自动轮询**；uPlot 实例组件卸载时 `destroy()`（防泄漏），配色从 CSS 变量取（适配双主题）。

**分批定义（TDD 节奏同 M3，红→绿→验证→review）：**

- **M4-B1 · usage SQLite 化（纯后端数据层）**：`usage_records`/`daily_usage_snapshots` 建表 + record_llm/record_tool 写 SQLite（同事务 upsert 快照）+ source/skill 归因贯穿（engine 显式传 skill、middleware 记 source）+ `/api/usage` 换源（形状不变）+ 趋势聚合查询（快照优先 + 明细兜底补齐）。验收：tmp db 重开不丢、totals 全史口径、重启后事件时间线仍在。

- **M4-B2 · 知识存量统计 + `/api/stats` 聚合端点**：vault 卡片总数/分类分布/决策备忘数/双链数/新增趋势（文件名前缀口径）+ chroma collection 计数 + include/range 参数路由 + 补零与降序。验收：401 无 token、include 过滤、7d/30d 边界、无前缀文件不计趋势。

- **M4-B3 · 前端 widget 接入**：`npm i uplot`；registry 两个 Placeholder 换真组件（knowledge-stock / usage-trend）+ KPI 数字卡 + MOCK 降级 + toast。验收：LIVE 真数据、MOCK 降级提示、双主题不破、卸载 destroy。

**Step 0 检查表（各批写码前对照）：**

1. B1 只动数据层与 `/api/usage` 数据源，**响应形状零变化**（决策 12）
2. 不搬内存历史；`reset()` 保留（测试清场用，改清 SQLite 表）
3. `record_llm/record_tool` 签名**兼容扩展**（新参带默认值），LLMClient/engine 现有调用点与测试不破坏；CaseEngine 不落库（eval 回放非真实调用，usage 层不感知）
4. record + 快照 upsert 同一 SQLite 事务（conn 上下文一次 commit，决策 8）
5. 日期/日界全部 Python 侧计算；SQL 不出现 `date('now')`/`datetime('now')`（决策 9）
6. `/api/stats`：`require_auth`；`include` 缺省 `knowledge,usage`；`range` 非法 422；响应回显 `range`
7. 趋势补零：起止日内每一天（含今日）都有数据点（决策 13）
8. B3 不动 WidgetGrid/registry 容器契约（entry `{id,title,size,component,props}` + component 收 `{tick,cfg}`），只换 component 与 props
9. uPlot：卸载 `destroy()`；配色走 CSS 变量（双主题）；空数据/单点不炸（NaN 兜底）
10. MOCK 模式 widget 用内置 mockData + toast 标识，与既有视图降级（bridgeDown）一致

### M4-B1 · usage SQLite 化（纯后端数据层）（逐任务 TDD）

- [x] **Step 0（check）**：对照检查表 1–5（形状零变化/不搬内存历史/签名兼容扩展/同事务快照/日界 Python 侧）——现有 test_usage.py 锁定契约后重写；`MAX_EVENTS` 上限测试随决策 12 退役
- [x] **Step 1（红）**：重写 `tests/test_usage.py`（形状逐字段锁定 ×2 + 重开不丢 + 明细永存 250 条 + skill/source 归因落表 + 快照同事务累加 + tool 行不双算 tokens + 趋势直查快照/明细兜底/补零 ×4）+ `tests/test_ai.py`（engine 4 方法 skill 透传）+ 新增 `tests/conftest.py`（autouse：usage db 指向 tmp，隔离 .data 真文件）——39 error 全指向 `usage.set_db` 缺失，红得正确
- [x] **Step 2（绿）**：`usage.py` 重写（`usage_records` + `daily_usage_snapshots` 建表；record_llm/record_tool 写明细 + 同事务快照 upsert；`report()` totals 改快照全表聚合、events 改 `ORDER BY id DESC LIMIT 50`、ts ISO 存储转展示格式；`daily_trend(days)` 快照直查 + 明细兜底 + 补零；per-call connect + WAL）+ `llm.py`（complete 加 `skill=""` → record_llm）+ `engine.py`（classify/decision/action/link 4 处显式传 skill）+ 3 个测试替身签名加 skill
- [x] **Step 3**：全量验证——**196 test 全过（+10），coverage 94.25%（usage.py 97%），ruff / mypy 干净**；修一处兜底测试断言（删快照后 totals 快照口径自然为 0，对照改明细同式）
- [x] **Step 4**：review + CHANGELOG + 提交

> **B1 执行记录（2026-09-03，196 test / coverage 94.25% / ruff、mypy 干净）：** 归因分层——skill 记 llm 行（engine 显式传，contextvars 弃用：线程池不传播）、source 记 tool 行（middleware 端点名，现有参数直落 source 列，签名零变化）；**tool 行快照 upsert 只 +1 请求数、tokens/cost 加 0**——llm 行是 tokens/cost 唯一事实源，防全表聚合双算（有测试锁定）；`/api/usage` 响应形状逐字段锁定（llm 行含 system 无 ms/llm/ok、tool 行反之），前端零改动；totals 口径升级为全史（快照全表聚合）；`daily_trend` 供 B2 `/api/stats` 直调。bridge.py **零改动**（middleware 与 report 调用点原样），middleware 记录的 source 天然落库。

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

- Backend 聚合端点（单一数据源，bridge 层；决策 7 收敛为单一端点，取代原 6 端点草稿）：

  - `/api/health`（供前端判断模式）

  - `GET /api/stats?include=knowledge,usage&range=7d|30d`（分布/趋势/双链/chroma 计数/用量一次返回）

  - `/api/usage` 明细端点保留（用量页时间线，B1 已换 SQLite 源、形状不变）

- React 只 fetch + chart（依赖 M0-B5 Widget 容器 + 双主题 + 布局保存）

- MOCK 降级：`/health` 失败或 `DASHBOARD_MODE=mock` 用前端内置 mockData + toast 提示"正在使用 mock 数据"

### M4 · 成功准则核对

M4 完成标志：

- [ ] Vault 知识存量可统计（卡片总数/分类分布/新增趋势/决策量）

- [ ] Chroma 集合统计可读（collection 文档数等）

- [ ] 用量从内存改为 SQLite `usage_records`（重启不丢、可长期聚合）

- [ ] `daily_usage_snapshots` 日汇总存在，7d+ 趋势不重算全表

- [ ] 用量记录含 source/skill 分组字段

- [ ] bridge 聚合端点就绪（/health + `/api/stats` 单一聚合 + `/api/usage` 明细，决策 7）

- [ ] React dashboard 只 fetch 展示，展示知识量 + 用量趋势

- [ ] MOCK 模式降级 + toast 提示可用

- [ ] 语法/测试通过（沿用 M0 的 ruff/mypy/pytest 门槛）

### M4 · 已登记扩展（不丢，待后续里程碑/横切实现）

- [ ] **运行型指标窗口**（依赖 M1 trace/domain event）：写卡频率、闭环率、召回命中率——M4 只做了存量型，运行型待 M1 trace 落库后接入统计（见 M5+ 扩展登记）

- [ ] 外部数据 widget（天气/日历/RSS/行情/服务健康）——候选 2，留 M5 以后展示增强

- [ ] 更重观测栈（Langfuse/OpenTelemetry/Prometheus+Grafana）——数据量增长或需要 eval/debug 时再评估，不默认引入

