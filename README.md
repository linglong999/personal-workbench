# workbench · 个人工作台

本地运行的 AI 记笔记助手，和你的 Obsidian Vault 并用同一个外置记忆。你把碎片想法、决策、行动丢进去，它做分类、关联、复盘和检索，让笔记在你需要时能被重新找到。

价值发生在你填进自己的数据和 `LLM_API_KEY` 之后——它不替你生成知识，只负责把记录整理成下次能复用的状态。这个项目的完整来龙去脉（为什么做、面向谁、关键取舍、如何衡量）见下文「为什么做」「关键产品决策」两节。

---

## 特性

- **输入分类**：粘贴一段文本，自动打标并按白名单目录归档（`classify_text`），不用手动选文件夹
- **向量检索**：基于 Chroma 的语义搜索，覆盖全部已建索引的笔记（`search_knowledge`）
- **自动建卡**：把想法写成结构化卡片（`create_note`），写卡时自动建议相似历史卡片的双链
- **决策参照**：做决策时召回相关历史决策供参考，并从分析中区分"决策过程好坏"与"结果好坏"
- **闭环检查**：扫描决策是否已记录实际结果 / 复盘（`scan_decision_closed_loop`）
- **经验回流**：开新任务时主动递送相关历史卡片（`reopen_task`）
- **用量统计**：LLM 调用次数、token、成本按天持久化（SQLite），前端仪表盘可看趋势

## 为什么做 · 面向谁

传统笔记工具解决的是"存"，没解决"取"和"用"。结果是记完即封存，经验睡在旧笔记里；做新决策只凭当下印象，不参考自己反复踩过的坑。市面上的 AI 笔记（Notion AI 等）要么把数据交到第三方云端，要么是"帮你在文档里搜答案"，没有真正进入记录这件事本身。

这个项目面向重度个人知识管理用户：写 Obsidian、记决策、按时复盘、在意数据自主权。它不是给文档加个聊天框，而是把"分类、关联、溯源、复用"这几件本该发生的整理动作，挪到记录发生的同时做完——这样笔记在下次需要时能被重新找到，且有上下文。

## 关键产品决策 · 取舍

| 决策 | 为什么这么做 | 放弃了什么 |
|------|------------|-----------|
| 外置记忆是工具，不是聊天机器人 | 价值在"下次能被重新找到"，不在"当下给个答案" | 不做 "Ask your notes" 式对话入口 |
| 本地优先，数据与 key 都在本机 | 记录是私有的，不因上云而让渡 | 不做云端同步 / 多端协同 |
| AI 隐形：整理织进流程，不做 AI 按钮墙 | 记录动作被打断越少，越可能坚持用下去 | 不做功能繁多的 AI 面板 |
| 白名单目录 + 写入前人工确认 | AI 只给建议，落库权留在人手里 | 不做"全自动笔记"（会污染 Vault） |
| 决策辅助做反结果偏误 | 避免拿结果好坏倒推决策质量（事后诸葛） | 不做简单的"查相似笔记给参考" |
| 先做核心闭环，出站发布 / 云同步排后 | 优先验证"记→分类→关联→复盘"正循环 | 页签式发布暂缓（已登记扩展） |

## 如何衡量

工具做出来先要有"有没有被用、用了多少"的可见性，才谈得上改。用量与写卡趋势按天入库（SQLite），前端仪表盘可查。

- 已落地：5 个核心工具、206 test 全过、coverage 94%+；M0–M4 工程化（鉴权、React 前端、ReAct 编排、自动双链、决策深化、统计仪表盘）
- 待补：写卡频率、决策闭环率、历史召回命中率——作为"这道循环有没有真的转起来"的观测

## 快速开始

不配 key、不花钱先跑通一次：

```bash
cd workbench
python -m pip install -e ".[dev]"
python scripts/e2e_mock.py        # 用假 LLM 跑通 5 个工具，免 key

cd ../workbench-console
npm install
npm run dev                       # 打开 http://localhost:8212，可"以演示模式进入"（内置数据）
```

看到脚本输出跑通提示即可。之后配置真实 LLM 和你的 Vault，见「配置」。

## 前端页面

`workbench-console/` 是 React 单页应用：顶部输入条、收件箱 / 今天 / 项目 / 复盘 / 知识 / 用量几个分区、可拖拽的 widget 仪表盘、宣纸 / 暗夜两套主题。

- **双模式**：默认 MOCK（纯前端内置数据）；登录后切 LIVE，经本地 HTTP Bridge（:8213）调用真实后端。Bridge 掉线自动回落并提示启动命令
- **统计仪表盘**（用量视图）：知识存量（卡片数 / 双链边数 / Chroma 计数 + 分布柱状图 + 新增趋势）与用量趋势（调用次数 / 成本 + token 折线），数据来自 `GET /api/stats` 聚合端点

```bash
# 终端 1：HTTP Bridge（LIVE 必需，cwd=workbench）
python -m uvicorn workbench.bridge:app --port 8213

# 终端 2：Console（cwd=workbench-console）
npm install
npm run dev
```

## 安装

```bash
cd workbench
python -m venv .venv
.venv\Scripts\activate           # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"

cd ../workbench-console
npm install
```

## 配置

复制 `workbench/.env.example` 为 `.env`，填入：

- `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`：openai 兼容 API。key 只留在本地 `.env`，已被 `.gitignore` 排除
- `VAULT_PATH`：你的 Obsidian Vault 目录
- `CHROMA_DIR`：Chroma 持久化目录（默认 `.data/chroma`）

## 运行

```bash
# 后端（cwd=workbench）
pytest -v                          # 全量测试 206 个，coverage 94%+
python -m ruff check src tests     # lint
python -m mypy src                 # 类型检查
python scripts/e2e_mock.py         # 免 key 端到端验证
python -m workbench.main           # MCP 服务器（stdio）
python -m uvicorn workbench.bridge:app --port 8213   # HTTP Bridge

# 前端（cwd=workbench-console）
npm run lint
npm run build
npm run dev
```

## 工具

| 工具 | 说明 | 环节 |
|------|------|------|
| `search_knowledge` | 知识库向量检索 | 数据读写 |
| `create_note` | 白名单目录建笔记 | 数据读写 |
| `classify_text` | 输入分类打标 | 输入 |
| `scan_decision_closed_loop` | 决策闭环检查 | 复盘 |
| `reopen_task` | 开任务递送历史经验 | 再实践 |

## 结构

```
workbench/                     # 后端（Python 3.10+，FastMCP + FastAPI）
├── src/workbench/
│   ├── config.py             # 配置（环境变量）
│   ├── knowledge/            # vault.py 读写 / vector.py 检索 / indexer.py 增量索引
│   ├── ai/                   # engine / orchestrator / policy 状态机 / skills / eval
│   ├── auth/                 # JWT + bcrypt（SQLite）
│   ├── usage.py              # 用量 SQLite 化（日快照）
│   ├── stats.py              # 知识存量统计聚合
│   ├── mcp_server.py         # 5 个 MCP 工具
│   ├── bridge.py             # HTTP Bridge + /api/stats
│   └── main.py
└── tests/                    # pytest（TDD）

workbench-console/            # 前端（React + Vite）
├── src/views/                # 收件箱/今天/项目/复盘/知识/用量/设置
├── src/widgets/              # 仪表盘 widget（uPlot 图表）
├── src/auth/  src/theme/     # 登录 / 双主题
└── assets/app.css
```

## 已知限制

- **Chroma embedding**：默认用本地哈希 embedding（即装即测、无需下载模型）；需要更强语义可自替换 embedding 函数
- **Agent 能力依赖真实 LLM + 你的真实 Vault**：`classify_text` / `scan_decision_closed_loop` / `reopen_task` 用假 LLM 只能跑通流程，没有实际意义——这正是本项目的前提
- **Bridge 为本地单用户设计**：业务端点已走 JWT 鉴权（health/auth 除外），但仅监听 127.0.0.1，勿直接暴露公网
- **Obsidian 直开需真实浏览器**：检索结果点击会走 `obsidian://` 协议唤起 Obsidian；IDE 内置 webview 会拦截外部协议，请用 Chrome / Edge 打开页面

---

## 现状与路线

工程化迭代（M0–M4）已完成：JWT 鉴权、React+Vite 前端重写、ReAct 编排状态机、自动双链、决策深化、统计仪表盘。当前 206 test 全过、coverage 94%+、ruff / mypy 干净。

- 后续扩展（已登记）：外部数据 widget（天气 / 日历 / RSS）、更重的观测栈（排在运行型指标落地之后）
- 设计理念与原始 PRD：`个人工作台-PRD-初稿.md`；阶段一六层 Prompt 工程产物与评估数据也在仓库根目录；迭代计划与决策记录见 `docs/superpowers/plans/`

## 开源协议

MIT，见 `LICENSE`。问题与改进见 `CONTRIBUTING.md`。