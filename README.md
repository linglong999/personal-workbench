# workbench · 个人工作台

本地运行的 AI 记笔记助手，和你的 Obsidian Vault 并用同一个外置记忆。你把碎片想法、决策、行动丢进去，它做分类、关联、复盘和检索，让笔记在你需要时能被重新找到。

价值发生在你填进自己的数据和 `LLM_API_KEY` 之后——它不替你生成知识，只负责把记录整理成下次能复用的状态。

---

## 特性

- **输入分类**：粘贴一段文本，自动打标并按白名单目录归档（`classify_text`），不用手动选文件夹
- **向量检索**：基于 Chroma 的语义搜索，覆盖全部已建索引的笔记（`search_knowledge`）
- **自动建卡**：把想法写成结构化卡片（`create_note`），写卡时自动建议相似历史卡片的双链
- **决策参照**：做决策时召回相关历史决策供参考，并从分析中区分"决策过程好坏"与"结果好坏"
- **闭环检查**：扫描决策是否已记录实际结果 / 复盘（`scan_decision_closed_loop`）
- **经验回流**：开新任务时主动递送相关历史卡片（`reopen_task`）
- **用量统计**：LLM 调用次数、token、成本按天持久化（SQLite），前端仪表盘可看趋势

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

- 待办：外部数据 widget（天气 / 日历 / RSS）、运行型指标（写卡频率、闭环率）、更重观测栈
- 设计理念与原始 PRD：`个人工作台-PRD-初稿.md`；阶段一六层 Prompt 工程产物与评估数据也在仓库根目录；迭代计划与决策记录见 `docs/superpowers/plans/`

## 开源协议

MIT，见 `LICENSE`。问题与改进见 `CONTRIBUTING.md`。