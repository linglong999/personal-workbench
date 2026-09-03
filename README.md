# 个人工作台 · workbench

> 一句话北极星：**把文本贴上去，它自己接住；并把你的经验与知识，变成下次可复用的有价值的东西。**

`workbench` 是一个 AI Native 的「个人成长工作台」脚手架——一个始终在后台、与你共用同一个外置大脑（Obsidian Vault）的搭档。你只需要**把碎片化的想法、决策、行动丢给它**，它负责自动**结构化 → 分类 → 关联 → 生成复盘**，把"随手记下的东西"变成"下次能再用的资产"。

它不是又一个知识管理工具，而是给「**你自己的数据 + 你的 AI**」套上一层自动化价值循环的壳。价值不在这个仓库里，价值产生在**你往里填自己的成长数据**的那一刻。

---

## 快速开始 · Quick Start

**60 秒，不配 key、不花钱，先跑通一次看效果：**

```bash
# 1. 装依赖
cd workbench
python -m pip install -e ".[dev]"

# 2. 跑内置 Mock 端到端验证（用假 LLM，免 key，验证 5 个工具 + 价值循环能跑通）
python scripts/e2e_mock.py

# 3. 看界面：启动前端 dev server（MOCK 模式；LIVE 接真实后端见下「前端页面」）
cd ../workbench-console
npm install
npm run dev               # 浏览器打开 http://localhost:8212，可「以演示模式进入」
```

看到脚本输出"价值循环跑通"即可。然后配置真实 LLM 与你的 Vault，把循环填进你自己的数据——见下方「配置」。

> 想立刻看懂"这个壳到底替你做了什么"吗？跑完 Mock 后，打开 `scripts/e2e_mock.py`，它会演示一条完整的价值闭环：输入 → 分类（chain）→ 决策闭环检查 → 再实践时主动递送历史经验（Agent）。

---

## 它解决什么

普通文件夹只能**存储**，静态笔记只能**记录**。`workbench` 的核心是**自动化知识增值**：

| 普通文件夹 / 静态笔记 | workbench |
|---|---|
| 记录后即封存 | 记录后**自动分类 + 归入正确目录** |
| 经验沉睡在旧笔记里 | 决策时**主动召回相关历史经验**（含反结果偏误分析） |
| 新笔记孤岛无连接 | 写卡时**自动建议双链**（相似历史卡片候选） |
| 闭环与否无人知晓 | **扫描决策闭环率**，识别"缺关联问题"的决策 |
| 新任务从头想起 | 开新任务时 **Coach 主动递送相关卡片** |
| 用了多少 token 无从知晓 | **用量统计仪表盘**（SQLite 持久化 + 日快照趋势） |

`classify_text`、`scan_decision_closed_loop`、`reopen_task` 分别对应价值循环里的**输入层、复盘层、再实践层**；`search_knowledge` 与 `create_note` 负责数据读写。

---

## 设计理念：价值循环 + 自主度光谱

系统围绕一条价值循环：**输入接住 → 思考决策 → 行动实践 → 回看复盘 → 长出知识 → 再实践**。

每个环节按「**自主度光谱**」选择形态——中低判断的环节（输入分类、决策追问、实践更新）用固定的 **chain**；高判断的环节（复盘偏差分析、愿景校准）才启用 **Agent 编排**。产品性格是「确认型」：**高置信度环节 agent 自主收，低置信度才升级到人**——用户是最终拍板者，但不是每步都要问。

（产品定义与六层 Prompt 工程细节见仓库根目录的 `个人工作台-PRD-初稿.md`，方法见 `提示词工程方法论.md`，六层成品见文末「阶段一产物」索引。）

---

## 前端页面 · Console（React + Vite，MOCK / LIVE 双模式）

`workbench-console/` 是这套工作台的**可视界面**（React 单页应用）——一个"AI 隐形"的产品控制台：左侧抽屉式侧栏（☰ 或 Ctrl/⌘+B 折叠）、顶部一句话接住输入、收件箱/今天/项目/复盘/知识/用量分区、可拖拽布局的 widget 仪表盘、右下 AI 轻提示，宣纸/暗夜双主题一键切换。

- 它刻意让 AI **不抢戏**：分类、检索、复盘提炼都织进流程角落（气泡、右侧相关笔记、命令面板），而不是一堆"AI 按钮"——对应「隐形式 AI」的产品定位。
- **双模式运行**：默认 **MOCK**（纯前端内置演示数据，含统计 widget 演示曲线，toast 标识）；登录后可切 **LIVE**，经本地 HTTP Bridge（:8213）真实调用后端工具——输入条实时分类（真实 LLM）、「今天」经验回流、「项目」决策闭环扫描、「检索」视图向量查询。Bridge 掉线时自动回落并提示启动命令。
- **统计仪表盘**（用量视图）：知识存量 widget（卡片总数/双链边数/Chroma 计数 KPI + 分类分布柱状图 + 新增趋势折线）与用量趋势 widget（LLM 调用次数/成本 + 输入/输出 tokens 双序列折线），uPlot 渲染、7d/30d 切换，数据来自 `GET /api/stats` 聚合端点——后端聚合、前端只 fetch。
- **登录鉴权**：JWT（bcrypt 哈希 + HS256），业务端点全部鉴权（health/auth 除外），支持"记住我"30 天免登录。

```bash
# 终端 1：启动 HTTP Bridge（LIVE 模式必需，cwd=workbench）
python -m uvicorn workbench.bridge:app --port 8213

# 终端 2：启动 Console（cwd=workbench-console）
npm install
npm run dev               # 浏览器打开 http://localhost:8212
```

> Bridge 的业务端点与 MCP 工具复用同一套组件（`/api/classify_text`、`/api/orchestrate` 编排等），另提供前端专用端点：`/api/auth/*`（注册/登录/me）、`/api/stats`（知识存量 + 用量趋势聚合）、`/api/usage`（用量明细）、`/api/sync_vault`（hash 增量索引）、`/api/orchestrate/resume`（人工确认后恢复）。

---

## 技术栈

- **后端**：Python 3.10+、FastMCP、FastAPI（Bridge 层）、ChromaDB、SQLite（用量/用户）、Pydantic、JWT + bcrypt、pytest（TDD，206 test / coverage 94%+）、ruff + mypy 门槛
- **前端**：React 18 + Vite、gridstack（widget 拖拽布局）、uPlot（图表）、ESLint

## 结构

```
workbench/                        # 后端
├── src/workbench/
│   ├── config.py                # 配置管理（环境变量）
│   ├── knowledge/
│   │   ├── vault.py             # Obsidian Vault 文件读写（白名单目录）
│   │   ├── vector.py            # Chroma 向量检索
│   │   └── indexer.py           # hash 增量索引（三档同步：新增/变更/零重算）
│   ├── ai/
│   │   ├── llm.py               # LLM 客户端抽象（用量归因 skill）
│   │   ├── engine.py            # AI 引擎（分类/决策分析/起草/双链判定）
│   │   ├── orchestrator.py      # ReAct 主管（工具循环 + max_steps 防死循环）
│   │   ├── policy.py            # 状态机：classify→recall→decision→action→link→review
│   │   ├── skills/              # 技能注册表（classify/recall/decision/action/link/review）
│   │   ├── frontmatter.py       # 决策备忘结构化 frontmatter（零 YAML 依赖）
│   │   ├── trace.py             # TraceStore（执行轨迹）
│   │   └── eval.py              # golden case 评估回放
│   ├── auth/                    # JWT + bcrypt 用户认证（SQLite）
│   ├── usage.py                 # 用量 SQLite 化（明细永存 + 日快照 + source/skill 归因）
│   ├── stats.py                 # 知识存量统计聚合（分布/双链/趋势/chroma 计数）
│   ├── mcp_server.py            # FastMCP 工具注册（5 个工具）
│   ├── bridge.py                # HTTP Bridge：JWT 鉴权 + /api/stats 聚合 + orchestrate
│   └── main.py                  # 入口与集成
└── tests/                       # pytest（TDD，206 个）

workbench-console/               # 前端（React + Vite）
├── src/
│   ├── views/                   # 收件箱/今天/项目/复盘/知识/标签/检索/用量/设置
│   ├── widgets/                 # widget 仪表盘（gridstack 拖拽布局 + uPlot 统计图表）
│   ├── components/              # 侧栏/输入条/卡片流/上下文面板/命令面板/AI 确认模态
│   ├── auth/                    # 登录注册 + JWT 态管理
│   └── theme/                   # 宣纸/暗夜双主题（CSS 变量单源）
└── assets/app.css               # 设计系统（OKLCH 雅致书香风）
```

## 安装

```bash
# 后端（cwd=workbench）
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 前端（cwd=workbench-console）
npm install
```

## 配置

复制 `.env.example` 为 `.env`，填入：

- `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`：openai 兼容 API（*你的 key 只会留在本地 `.env`，已被 `.gitignore` 排除，不会进入代码仓库*）
- `VAULT_PATH`：你的 Obsidian Vault 目录
- `CHROMA_DIR`：Chroma 持久化目录（默认 `.data/chroma`）

## 运行

```bash
# 后端（cwd=workbench）
pytest -v                          # 全量测试（206 个，coverage 94%+）
python -m ruff check src tests     # 代码风格门槛
python -m mypy src                 # 静态类型门槛
python scripts/e2e_mock.py         # 免 key 端到端验证
python -m workbench.main           # 启动 MCP 服务器（stdio）
python -m uvicorn workbench.bridge:app --port 8213   # 启动 HTTP Bridge（前端 LIVE 模式）

# 前端（cwd=workbench-console）
npm run lint                       # ESLint
npm run build                      # vite 生产构建
npm run dev                        # dev server（:8212）
```

## 工具

| 工具 | 说明 | 对应环节 |
|------|------|---------|
| `search_knowledge` | 知识库向量检索 | 数据层 |
| `create_note` | 白名单目录建笔记 | 数据层 |
| `classify_text` | 输入分类打标 | 输入层（chain） |
| `scan_decision_closed_loop` | 决策闭环率检查 | 复盘层（Agent） |
| `reopen_task` | 开新任务主动递送历史经验 | 再实践（Agent） |

## 已知限制

- **Chroma 默认 embedding**：上游默认识别 ONNX 模型，首次运行需下载（网络受限时不适用）。本仓库以**本地哈希 embedding 作默认**，即装即测、无需下载；如需更强语义检索，可自行替换 embedding 函数。
- **`classify_text` / `scan_decision_closed_loop` / `reopen_task`** 是真 Agent 能力，依赖**真实 LLM + 你的真实 Vault** 才有意义——这正是本项目的设计初衷：价值在你的数据 + 你的 AI 上发生。
- **对外输出（多平台适配）**：`PublisherAgent` 为后续迭代（实施计划 M11），不在当前范围。
- **Bridge 为本地单用户设计**：已内置 JWT 鉴权（业务端点全部要求 token，health/auth 除外），但仍是监听 127.0.0.1 的本地服务，请勿直接暴露到公网；如需多人使用请自行收紧 CORS 来源。
- **Obsidian 直开需真实浏览器**：Console 的检索结果 / 标签卡片点击会通过 `obsidian://` URI 唤起 Obsidian 打开原笔记。嵌入式预览浏览器（IDE 内置 webview）会静默拦截外部协议——请用 Chrome/Edge 打开 `http://localhost:8212`，首次点击时浏览器会请求确认"打开 Obsidian"。

---

## 阶段一产物 · 六层 Prompt 工程

本项目分两个递进阶段，阶段一是阶段二工程化的"设计与验证原型"，成品已在仓库根目录（只读签核件）：

| 产物 | 对应价值循环环节 | 文件 |
|---|---|---|
| 输入层提示词 | 输入接住 → 分类打标 | `输入层.md` |
| 决策层提示词 | 思考决策（追问 + 多维分析） | `决策层.md` |
| 实践层提示词 | 行动实践（行动跟踪） | `实践层.md` |
| 复盘层提示词 | 回看复盘（偏差分析 + Agent） | `复盘层.md` |
| 知识创造层提示词 | 长出知识（六区块卡片 + 双链） | `知识创造层.md` |
| 愿景层提示词 | 再实践（愿景审视 + 校准提案） | `愿景层.md` |
| 方法论 | 四步法 + 评估契约 + 已知教训 | `提示词工程方法论.md` |
| 质量防线 | 29 项跨层检查 | `层间共性检查表.md` |
| 评估治理 | 六层 golden set | `评估数据集.md` |
| 术语收敛 | 跨文档单点定义 | `跨文档术语表.md` |
| 签核报告 | 知识创造层闭环验证 | `知识创造层v0.3.1_签核报告.md` |

> 这些是阶段一签核的**只读成品**，作为开源的价值主张输入。它们证明：这条价值循环不仅代码可实现，也已被设计为一套可人工跑通的 Prompt 工作流。

## 路标 · Roadmap

| 阶段 | 内容 | 状态 |
|---|---|---|
| 阶段一 | Vault 工作流 + 六层 Prompt 工程 | ✅ 完成（本仓库） |
| 阶段二 | Python MCP 服务（5 工具，TDD） | ✅ 完成 |
| 阶段二 + | 前端 Console 接真实后端（MCP→HTTP Bridge 层 + MOCK/LIVE 开关） | ✅ 完成 |
| 工程化 M0 | 可构建/可鉴权/可扩展规范化工程：JWT 鉴权、React+Vite 前端重写、widget 仪表盘、双主题、ruff/mypy/coverage 门槛 | ✅ 完成 |
| 工程化 M1 | ReAct 主管编排 + 状态机（classify→recall→decision→action→link→review）+ TraceStore + golden case 评估 | ✅ 完成 |
| 工程化 M2 | 写卡自动双链管线 + hash 增量索引（sync\_vault 三档同步零重算） | ✅ 完成 |
| 工程化 M3 | 决策深化：历史参照注入（recall 三档 purpose）+ 反结果偏误 + 决策备忘结构化 frontmatter | ✅ 完成 |
| 工程化 M4 | 统计仪表盘：usage SQLite 化（日快照）+ `/api/stats` 聚合 + uPlot 前端 widget | ✅ 完成 |
| 阶段三 | 开源对外打磨（示例模板、演示） | 🔶 进行中 |
| M5+ 已登记 | 运行型指标（写卡频率/闭环率/召回命中率）、外部数据 widget（天气/日历/RSS）、重观测栈 | 📋 登记 |

> 工程化迭代全程逐任务 TDD + 频繁提交，当前 **206 test 全过、coverage 94%+、ruff/mypy 干净**；迭代计划与决策记录见 `docs/superpowers/plans/`。

---

## 开源协议

本项目为开源作品，采用 **MIT** 协议，详见 `LICENSE`。欢迎提出问题、贡献示例模板与改进意见（见 `CONTRIBUTING.md`）。