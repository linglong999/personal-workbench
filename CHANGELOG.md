# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式。

## [0.4.0] - 2026-09-02

### Changed（M0-B2 · 前端 React 化，功能等价迁移）

- `workbench-console` 由纯静态（index.html + app.js 569 行 IIFE）迁移为 Vite + React 18 工程
  （`npm run dev` :8212 / `build` / `lint`），功能与视觉零回归（20 项浏览器走查全过）
- 组件化：App 编排 + 7 组件（InputBar/Sidebar/CommandPalette/ContextPanel/AIConfirmModal/
  CardMarquee/Toast）+ 9 视图（收件箱/今天/项目/复盘/知识/标签/检索/用量/设置）
- `src/api/client.js`：MOCK/LIVE 模式与假数据/归位规则单点收口（B4 在此注入 JWT）；
  localStorage 沿用原 key 与取值（老用户模式无缝保留）
- `src/style/theme.css`：白·墨·金语义 token 别名层（为 B3 多主题换肤预留单点）
- `assets/app.css` 保留为样式基座；`assets/app.js` 删除（逻辑全部迁入组件）
- CI 新增 frontend job（npm ci → build → lint）；.gitignore 加 node_modules/

## [0.3.0] - 2026-09-02

### Added（M0-B1 · 后端认证）

- `workbench/auth/` 模块：`UserRepository`（SQLite 用户表，`closing` + 事务组合防连接泄漏）与
  `AuthService`（bcrypt 哈希 + JWT 签发/校验，secret 单源、可被测试替换）
- `bridge.py` 新增 `/api/auth/register|login|me` 三端点；7 个业务端点统一挂
  `Depends(require_auth)`（missing/invalid token → 401）；`/api/health` 与 `/api/auth/*` 放行
- `observe_calls` skip 列表加 `/api/auth/`（auth 非业务调用，不计 usage 观测）
- 测试 13 → 26 个（`test_auth.py` 7 + `test_bridge.py` 6），coverage 78.6%（门槛按分阶段约定 70%）
- 依赖：PyJWT >= 2.8、bcrypt >= 4.0

### Fixed（M0-B1 review）

- `test_auth.py` 短 secret（11B）触发 4 处 InsecureKeyLengthWarning → 统一 `b"t" * 32`
- `_AUTH_SECRET` 短 key 边界：LLM key 非空但 <32B 时（如 CI 的 `sk-test`）拼接 fallback 补足，
  避免短 HMAC key 警告

## [0.2.0] - 2026-09-02

### Added（M0-B0 · 工程规范）

- ruff（lint + format，line-length 100，E/F/I/W 规则）接入 `workbench/pyproject.toml`
- mypy 静态类型检查（explicit_package_bases + mypy_path=src，`mypy src` 可用）
- pytest-cov 覆盖率门禁（分阶段收紧：B0=50% → B1=70% → M0 收口=85%）
- GitHub Actions CI（backend：lint / type check / test+coverage；frontend job 待 B2 启用）
- ADR-0001：分层架构、JWT 方案 A、取消公网/Docker、SQLite 选型、分阶段质量门槛
- `docs/architecture/index.md` 架构总览

### Fixed（B0 顺带，ruff/mypy 基线清理）

- 全仓 ruff format 格式化（20 文件）+ 29 处 lint 自动修复
- `ai/llm.py`：`complete()` 返回值兜底 None（`str | None` → `str`）
- `knowledge/vector.py`：`vec` 类型标注、`search()` 对 Chroma 可选字段的安全取值、
  `_LocalEmbeddingFunction.__call__` 与三方基类返回类型冲突的显式 `type: ignore[override]`
