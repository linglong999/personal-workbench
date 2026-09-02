# ADR-0001 · 分层架构与技术选型基线

- 状态：已接受
- 日期：2026-09-01
- 背景：M0 工程化 + React 重写启动（M0–M4 全量迭代计划封板，见 `docs/superpowers/plans/2026-09-01-workbench-full-iteration.md`）

## 背景与决策语境

个人工作台（workbench）已完成阶段一（提示词工程）与阶段二（Python MCP 服务，5 工具，TDD 13 测试全绿），现进入"工程化底座 + agent 化"迭代。M0 需要确定：代码分层范式、认证方案、部署形态、本地数据存储选型，为 M1（ReAct 主管 + Skill）到 M4（数据统计 widget）铺轨。

## 决策

### D1 · 分层架构范式

```
backend/   workbench（Python src-layout：ai / knowledge / bridge / auth…）
frontend/  workbench-console（B2 起迁为 Vite + React）
infra/     .github CI；无 Docker（见 D3）
docs/      ADR / architecture / plans / specs
```

- 模块边界：`ai`（引擎/Agent/Skill）单向依赖 `knowledge`（vault/vector）；`bridge`（FastAPI HTTP 层）只做协议转换，不承载业务逻辑；`auth` 独立成包。
- 单向依赖原则：Skill 不依赖主管（Orchestrator），注册表反向引用 Skill（M1 落地）。

### D2 · 认证：JWT 方案 A（token 存 localStorage）

- 形态：注册/登录 → 签发 JWT（PyJWT）→ 存 localStorage → 请求带 `Authorization: Bearer`。
- 鉴权范围：`/api/health`、`/api/auth/*` 放行；其余业务端点（含未来 M4 统计端点）一律 `Depends(require_auth)`。
- 密码存储：bcrypt 哈希；用户库：SQLite。
- 取舍理由：本项目为本地单人自用（不公网暴露），XSS 面低；方案 A 开发成本最低。方案 B（refresh token httpOnly cookie）更安全但引入 CORS/credentials 复杂度，在"本地自用"威胁模型下收益不兑现。认证逻辑封一层接口，将来若公网化可切换。

### D3 · 部署形态：本地自用，取消公网与 Docker 规划

- 开源定位：用户下载源码、自己本地跑（安装 → 配 .env → 启动），复现本地流程。
- 不为公网做交付物（无反代/HTTPS/公网防护）；Docker 演示形态如有需要另立任务，不在本迭代计划内。
- 理由：用户拍板（开源后使用者也是本地自用，公网场景不存在）。

### D4 · 本地数据存储：SQLite

- 认证用户表（B1）与用量记录 `usage_records` / `daily_usage_snapshots`（M4-B）统一走 SQLite（Python 标准库 sqlite3，无新增依赖）。
- 理由：可聚合、可持久、免服务进程；与"token/花费要出 7d/30d 趋势"的查询需求匹配；JSONL 聚合查询弱，不选。

### D5 · 质量门槛：分阶段收紧

- 最终目标 coverage ≥85%，分阶段执行：B0 过渡阈值 50%（bridge/usage 尚无测试，结构性事实）→ B1 补 auth/bridge 测试后提到 70% → **M0 收口达成 85%（2026-09-02，实测 85.49%）**。
- 收口语（第 2 版成真线，非凑数）：补 `test_bridge_endpoints.py` 覆盖 7 个业务端点 happy path + 鉴权拒访——给前端 LIVE 的 API 契约补回归防线；补 `test_usage.py` 锁定 usage 观测行为（作 M4 升级 SQLite 的回归基准）；`tests/helpers.py` 用 fake 组件替代模块级单例，不碰真实外部 IO。
- `pyproject.toml` `fail_under` 已封 85；`pythonpath=["src","tests"]` 配置使 CI 不再依赖 `PYTHONPATH` 环境变量。
- 有意不追到 100% 的剩余缺口（低价值/环境相关）：Obsidian 注册表 IO（`_registry_path`/`_registered_vault_for`）、真实 LLM 调用分支（`llm.py`/`engine.py`）、`__main__` 启动块、平台特化路径。追这些应__计数凑数不增价值__，留真实业务演进（M4 重写 usage 存储等）。
- 工具链：ruff（lint+format）+ mypy（explicit_package_bases + mypy_path=src 组合下 `mypy src` 可用）+ pytest-cov + GitHub Actions CI（backend job 先行，frontend job 待 B2 启用）。

## 后果

- 正面：模块边界清晰、M1 Skill/主管可直接挂载；认证与用量同用 SQLite，技术栈收敛；CI 从 B0 即绿。
- 负面/已知代价：localStorage 存 token 的 XSS 面未消除（接受，本地威胁模型）；无 Docker 意味着"环境一键复现"留给文档（README 安装步骤承担）。
- 后续触发器：若项目公网化 → 重议 D2/D3；若数据量或多人需求 → 重议 D4。
