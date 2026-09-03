# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式。

## [0.15.0] - 2026-09-03

### Added（M2-B2 · hash 增量索引）

- `knowledge/indexer.py`：`sync_vault(vault, vector)` 扫 Vault 白名单目录做增量同步——content\_hash 命中跳过（零 embedding 重算）/ 变更只重算该卡 / 新增入库；`SyncReport{added, updated, skipped}` 可观测
- **doc_id 与写卡路径同款 `note-{stem}`**：sync 与 action / create\_note 端点 / MCP 三入口互认，同一张卡不产重复条目（写卡后 sync 直接 skipped，集成测试证明）
- `VectorStore.content_hash()`（sha256，**只算正文**）：写卡路径索引真实标题、sync 从文件名剥日期前缀推标题——hash 若含标题，同一张卡会在两种标题间无限"更新"
- `VectorStore.add` 内部计算并落 content\_hash 进 Chroma metadata（三写卡入口零改动即满足"写入即带 hash"；旧数据无 hash 字段 → 首次 sync 自动补齐）
- `VectorStore.get_hash(doc_id)`：增量判据读取（未索引 → None）
- `POST /api/sync_vault`（鉴权）：首次初始化与手动重建入口，返回 SyncReport

### 已知限制（最小版约定）

- upsert 语义不处理删除/改名：改名产生新条目、旧条目留存（全量重建 = 清空 chroma 目录后重跑 sync）
- 同名 stem 跨目录会互相遮蔽（`note-{stem}` 约定的既有边界，写卡路径同样存在）

### 实测

- 153 test 全过（+8：indexer 6 + bridge 端点 2），coverage 94.16%（indexer.py 100%），ruff / mypy 干净（30 源文件）
- 零重算证明：monkeypatch 计数 upsert——二跑 sync 零次 upsert；改一张卡恰一次 upsert

## [0.14.0] - 2026-09-03

### Added（M2-B1 · 写卡自动双链管线）

- `ai/skills/link.py`（第 6 个 Skill，知识层）：三档阈值分流——score≥0.85 auto（零 LLM 直接链）/ 0.75~0.85 走 `engine.judge_link`（LLM 边缘判断）/ <0.75 pending_review（透出给用户裁决）；同标题去重留最高分 + 排除草稿正文已有的人工 `[[链]]`（尊重显式边）；judged 明细进 result（trace 可回放、坏例回流可精确复现）
- `engine.judge_link`：关联判断 prompt + JSON 边界三态兜底（非法 JSON / 残缺 / link_to 非 bool 一律不链——宁可不链，不可误链）
- `action` Skill 写入规范扩展：args.links 渲染为「## 关联」节（正文人工链不重复、args 内去重、无新链不加节）；索引与落盘用同一份渲染后正文
- `vector.search` 补 `score`（1 - cosine 距离），响应加字段向后兼容
- confirm interrupt payload 扩为 {preview, links, pending_review}：建议双链随确认透出

### Changed（interrupt 接线收编 policy）

- **orchestrator 纯执行器化**：action/decision 两处硬编码 interrupt 接线删除，confirm/judgement/disambiguate 全部由 policy 返回 Interrupt 指令——policy 是唯一"想"的场所（B3 接线职责不变，位置归位）
- 编排后序列（决策流）：classify → decision → action 草稿 → recall(top_k=20) → link → [confirm] → approve → action(confirmed, links) → recall 收尾；`_latest_recall` 按 finish 标志区分候选召回与收尾召回，互不串档
- golden case 2 个序列更新（decision_confirm_approve / disambiguate_pick_practice），回归=固化新编排
- `case_from_trace` 提取 link judged 明细进 script.judges，CaseEngine 重放可精确复现 LLM 档裁决（未脚本化候选默认不链）

### Fixed（review 抓到的两处缺陷）

- `vector.search` 距离缺失（API 异常形态）兜底原为 0.0 → score=1.0 会把异常结果顶进 auto 档自动建链；改兜底最大距离（score=0 最低档），补 monkeypatch 回归测试
- `engine.judge_link` 喂料与 M2-A 设计不符：原喂新卡+候选**全文**且不带 score，设计要求"仅标题+摘要+score"（成本上界 + 近全卡误判同名词卡）；改 200 字截断摘要 + score 进 prompt，补 PromptCapture 回归测试

### 实测

- 145 test 全过（+22），coverage 93.96%（link.py、policy.py 均 100%），ruff / mypy 干净（29 源文件）

## [0.13.0] - 2026-09-03

### Added（M1-B5 · Bridge 接线收口）

- `POST /api/orchestrate`（{text} 起新回合）+ `POST /api/orchestrate/resume`（{run_id, decision} 续回合）：会话注册表按 run_id 持有 Orchestrator，**终态即删**（resume 未知/已终态 → 404）+ cap 50 最旧先出；响应透出 run_id/status/state/output/interrupt/events 全链（事件链即前端可渲染的观测数据）；回合错误（空输入等）是数据（200 + status=error），不是传输错误
- TraceStore 接线：bridge 落 `.data/traces`（gitignore），主管每回合的观测点快照直接可回放/归因

### Changed

- **agents.py 退役（M1 角色迁移收口）**：bridge 三端点（classify_text / scan_decision_closed_loop / reopen_task）改走 Skill 注册表派发，**响应契约不变**；`main.py`/`mcp_server.py` 迁 skills（ctx 从 dict 改 SkillContext 直传）；`ai/__init__.py` 去 agent 导出；B1 等价测试（Skill vs Agent 两路对照）完成防漂移使命，改为直接断言
- **写入即索引（产品契约补漏，落 Skill 层）**：action 确认写入后同步向量索引——此前仅 create_note 端点索引，agent 写的笔记检索不到（召回闭环断）；契约在 Skill 层则所有入口一致（orchestrate / MCP）；`VectorLike` 协议补 `add`

### Fixed（review 抓到的并发缺陷）

- FastAPI 同步 handler 跑线程池：双击 approve 的并发 resume，第二个会撞「resume() 非法状态」RuntimeError → 500，并发 prune 还会重复删 key——查表 + resume + prune 整体持锁（后到者 404）

### 实测

- 123 test 全过（+8 orchestrate 端点测试，-2 agent 冗余测试），coverage 93.61%，ruff / mypy 干净（28 源文件，agents.py 移除）

## [0.12.0] - 2026-09-03

### Added（M1-B4 · Trace + eval runner）

- `ai/trace.py`（观测层）：TraceStore 一 run 一 JSON 文件落盘（run_id=时间戳-短哈希，文件名即排序键）+ `verify()` 链完整性校验（首事件/seq 连续/状态跳变/末观测点）+ `attribute_failure()` 最小归因（error 定位 reason+出错前 tool+at_seq；低置信步骤收集，阈值复用 DecisionSkill.CONFIDENCE_THRESHOLD）
- `ai/eval.py`（评测水位=选项 1 最小版）：GoldenCase（脚本化引擎 CaseEngine/CaseVector，不调真 LLM）+ run_case/run_cases（每 case 独立 vault 跑真 Orchestrator，非法 resume/非法 id 报 failure 不崩）+ `case_from_trace()` 坏例回流（trace 提取 input/script/resumes，expect 从结果起草人工校对）
- `evals/golden/` 5 初始 golden case（决策确认写入/低置信驳回/复盘扫描/澄清选实践/空输入 ERROR），`test_eval.py` 扫目录全量跑——golden case 即 CI 回归
- orchestrator 接线：可选注入 TraceStore，进入 WAITING_HUMAN/DONE/ERROR 观测点时快照落盘（同 run_id 覆盖，崩溃保留上一稳定点）；run_id 生成

### Changed（review 修正：mypy 抓出的架构债）

- `SkillContext.engine/vector` 从具体类（AIEngine/VectorStore）改为结构协议（EngineLike/VectorLike）——Skill 依赖能力接口的本意落实，eval/测试的脚本化引擎可注入

### 实测

- 117 test 全过（+29），coverage 93.61%（trace.py、eval.py 均 100%），ruff / mypy 干净
- 修正 A 灵魂测试：ExplodingStore 落盘抛 OSError → 任务照常完成、笔记照常落盘（观测层失败不杀任务）

## [0.11.0] - 2026-09-02

### Added（M1-B3 · ReAct 主管 + 状态机）

- `ai/orchestrator.py`：六状态机（IDLE/INGEST/ACTING/WAITING_HUMAN/DONE/ERROR）+ 每跳必产 DomainEvent（B4 TraceStore 的原料）+ 主管级 interrupt 接线（action needs_confirmation→confirm；decision needs_judgement→judgement）+ resume 续跑 + Guards 三守护（max_steps/budget_seconds/human_wait_timeout，超时按放弃→DONE）
- `ai/policy.py`：策略=主管的"想"（纯函数式，只读 RunView 返回一条指令）——RulePolicy 确定性路由（分类→按标签走价值环节→recall 收尾"带着经验回来"）；resume 安全默认：confirm/judgement 非 approve 一律不写库（宁可不写，不可误写）
- `tests/test_orchestrator.py`：24 个测试——决策全链/三类 interrupt（含非法裁决安全默认）/放弃与等待超时/守护与异常/事件链完整性/DONE·ERROR 后重开回合/各标签路由

### Fixed（review 抓到的 1 个真 bug）

- budget_seconds 计入了人机等待时间——用户思考超过 budget 后 approve 会被误判 "budget exceeded"（守护语义是机器时间）；修复：resume 时重置计时起点，并补回归测试（budget 不计等待时间）

### 实测

- 88 test 全过（+24），coverage 92.00%（orchestrator.py、policy.py 均 100%），ruff / mypy 干净

## [0.10.0] - 2026-09-02

### Added（M1-B2 · decision/action 两个新 Skill，注册表满 5）

- `ai/skills/decision.py`（决策层）：结构化追问 + 多维分析，产出可选方案与倾向；confidence<0.6 输出 `needs_judgement` 拍板标记（B3 主管映射 disambiguate/judgement）；LLM 非法置信度按 0.0 处理
- `ai/skills/action.py`（实践层）：结论/待办起草落库，`requires_confirmation=True`；未确认零副作用且幂等（预览带起草内容供 confirm interrupt 展示）；`KIND_FOLDERS` 显式映射（待办→行动记录，Vault 白名单目录）+ 未知 kind 入口即拒
- `engine.py` 新增 `analyze_decision` / `draft_note`（决策层/实践层 prompt，六层文档措辞）；JSON 边界三态兜底（非法 JSON/非 dict/字段残缺 → defaults 合并，不抛异常）
- 闭环契约内嵌：决策备忘正文必含「关联问题」（review 扫描依赖）、待办正文必含「次日跟进」（跟进信号落在正文）

### Fixed（review 抓到的两个真 bug）

- 「待办」kind 撞 `VaultStore.ALLOWED_FOLDERS` 白名单（确认写入必 ValueError）——初版假仓库测试测不出，改真 VaultStore 测试后修复
- LLM 返回合法 JSON 但字段残缺时 `analysis["options"]`/`draft["title"]` KeyError——engine 改 defaults 合并

### 实测

- 64 test 全过（+15），coverage 89.11%（engine.py、skills 包均 100%），ruff / mypy 干净
- 顺带关闭存量缺口：`AIEngine.check_closed_loop` 此前零直测（全被 FakeEngine 绕过）

## [0.9.0] - 2026-09-02

### Added（M1-B1 · Skill 基础设施 + 3 迁移 Skill）

- `src/workbench/ai/skills/` 新包（ADR-0001 D1：ai 含引擎/Agent/Skill，单向依赖 knowledge）：
  - `base.py`：`Skill` Protocol（name/description/requires_confirmation/run）+ `SkillContext`（engine/vault/vector 注入，Skill 不依赖主管）+ `SkillResult`（output + confidence 供主管判 interrupt）
  - `classify.py` / `review.py` / `recall.py`：逻辑迁自 Classifier/Reviewer/Coach 三个 Agent（agents.py 本批不动保 bridge 兼容，M1-B5 退役）
  - `registry.py`：`REGISTRY` + `get_skill()`——主管唯一调度入口，未知名抛 KeyError
- `tests/test_skills.py`：**等价迁移测试**——同一 fake 输入下 `Skill.run` 输出 == 现有 Agent 输出（迁移无回归的机制化证明）+ 注册表/协议断言

### 实测

- 49 test 全过（+6），coverage 87.06%（skills 包 100%），ruff / mypy 干净

## [0.8.0] - 2026-09-02

### Changed（M0 收口语 · 覆盖率 70%→85%）

- `pyproject.toml` `fail_under` 提至 85（ADR-0001 D5 分阶段收紧的最终线），CI 门禁封板
- 顺带修 pytest `pythonpath = ["src","tests"]` 配置（此前 CI 依赖环境变量 `PYTHONPATH` 才可导入）

### Added（M0 收口语 · 补测试批次，非凑数）

- `tests/helpers.py`：端点测试共享——独立鉴权（独立 db/secret）+ fake 组件（FakeVector/Vault/Classifier/Reviewer/Coach），绝不触碰真实 Vault/Chroma/Obsidian 注册表
- `tests/test_bridge_endpoints.py`：7 个业务端点（search_knowledge / list_tags / usage / create_note / classify_text / scan_decision_closed_loop / reopen_task）happy path + 鉴权拒访回归——给前端 LIVE 的 API 契约补上自动化防线
- `tests/test_usage.py`：usage 观测模块单测（计数 / 成本公式 / 增量 diff / 上限截断 / reset），并锁定现有行为作 M4 升级 SQLite 的回归基准

### 实测

- 43 test 全过，coverage 85.49%（此前 79%）；ruf / mypy 干净；前端 lint 0 + build 无回归
- 剩余缺口为低价值胶水：Obsidian 注册表 IO / LLM 真调用分支 / `__main__`（见 ADR-0001 D5）

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
