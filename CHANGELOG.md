# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式。

## [0.7.0] - 2026-09-02

### Added（M0-B5 · Widget 容器框架）

- `src/widgets/`：`Widget.jsx`（统一外壳：标题/↻ 刷新/⠿ 拖拽手柄/内容区）、
  `registry.js`（注册表，entry = id/title/size/component/props，数组保序即默认布局）、
  `WidgetGrid.jsx`（注册表 → GridShell，布局保存 `wb-layout:usage-widgets`；↻ bump tick 注入手动刷新）
- `HealthWidget.jsx` 服务健康灯（**真实数据源**）：轮询免鉴权 `/api/health`（30s）+ ↻ 手动探活，
  绿=在线/红=离线——验证容器框架 fetch→render→refresh 全链路
- 3 个占位 widget（知识存量/用量趋势/外部数据）：hint 注明 M4 接入内容，不造假数据
- 挂载位：用量视图（M4 统计承接位）；GridShell 零改动（B3 已做成通用容器，全部复用）
- `client.js` 导出 `BRIDGE_ORIGIN`（免鉴权直连，健康探测不走带 token 的 request()）

## [0.6.1] - 2026-09-02

### Added（M0-B4 后续 · 登录记住我）

- `AuthReq.remember` → `AuthService` TTL 覆盖（`_ttl()`）：默认 1 小时 / 记住 30 天
- 登录/注册页「记住我 · 30 天免登录」checkbox（默认勾选）；TDD 2 测试断言 exp-iat
- 解决 B4 review 登记项：本地单用户每小时重登的体验问题

## [0.6.0] - 2026-09-02

### Added（M0-B4 · 前端认证入口）

- `src/auth/`：`auth.js`（token/user 存取 + `wb-auth` 事件广播）、`AuthPage.jsx`（登录/注册
  双 tab + 演示模式入口，后端英文 detail 映射中文提示）、`RequireAuth.jsx`（登录门）
- `client.js` `request()` 统一收口（api/apiGet 共用）：注入 `Authorization: Bearer`；
  持 token 收到 401 → 自动登出并广播 → 落登录页（登录页自身的 401 不触发）
- 演示模式豁免：明确选择过 mock（`wb-mode==='mock'`）可免登录体验前端；全新用户先见
  登录页（`getModeRaw()` 区分「未选择」与「明确选择」）；MOCK 下切 LIVE 被拦截提示登录
- 设置页新增「账号」卡（当前用户/登出/去登录）；命令面板已登录时追加「登出」命令
- 登录/注册成功自动切 LIVE 并持久会话（wb-token/wb-user/wb-mode）

## [0.5.0] - 2026-09-02

### Added（M0-B3 · 拖拽布局 + 多主题 + 命令搜索）

- GridStack 13.2.0：`src/shell/GridShell.jsx`（拖拽/缩放/布局自动保存）+ `src/shell/layout.js`
  （`wb-layout:<key>` 按容器命名空间持久化）；知识视图 4 卡 widget 化，`⠿` 手柄拖拽、
  卡片本体保留点击检索语义
- React 与 GridStack 共存约定：item DOM 由 React 渲染、位置由 GridStack 接管；
  恢复布局不走 `grid.load()`（会动 DOM），渲染前用 saved 覆盖初始位置；卸载 `destroy(false)`
- 多主题：`src/theme/themes.js` 定义完整原始 token 集（非仅语义别名），`ThemeProvider`
  写 documentElement（先清后写防残留）；paper=原值（默认零变化）/ midnight=书香暗夜，
  `wb-theme` 持久化；入口两处（设置页外观卡 + 命令面板）
- 命令面板增强：命令注册表 17 条（操作/外观/导航分组）+ 输入过滤 + ↑↓/Enter/Esc 键盘流；
  计划中的「重建索引」无对应后端端点，不造假功能，以「恢复默认布局」真实功能替代
- ESLint 对 GridStack 的 `gs-*` 布局属性放行（`react/no-unknown-property` ignore 列表）

### Changed（M0-B3 · 顺带 token 化，视觉零变化）

- `.kb-main` 背景硬编码 → `--bg-main-card`；`.btn` 白字 `#fff` → `var(--bg-app)`
  （暗色主题下可读性）；小面积装饰浅色暗色下偏亮已登记后续打磨

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
