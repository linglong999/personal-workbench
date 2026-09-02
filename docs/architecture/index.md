# 架构总览

> 对应 ADR-0001；M0–M4 迭代计划见 `docs/superpowers/plans/2026-09-01-workbench-full-iteration.md`

## 分层图（M0 完成后目标态）

```
┌─────────────────────────────────────────────────────┐
│  frontend · workbench-console                        │
│  (B2 起：Vite + React；B3 拖拽外壳/主题/命令面板；     │
│   B4 登录+token；B5 Widget 容器)                     │
└────────────────── HTTP (Bearer JWT) ─────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  bridge · FastAPI (端口 8213)                        │
│  /api/auth/* (B1, 放行)  /api/health (放行)           │
│  业务端点 = Depends(require_auth)                    │
│  协议转换层：不承载业务逻辑                           │
└──┬──────────────────────┬───────────────────────────┘
   │                      │
┌──▼───────────┐   ┌──────▼──────────────┐   ┌────────┐
│ ai           │   │ knowledge            │   │ auth   │
│ engine/agents│──▶│ vault(Obsidian读写)  │   │ SQLite │
│ (M1: skills/ │单向│ vector(Chroma+本地   │   │ bcrypt │
│  orchestrator│依赖│   哈希embedding)     │   │ PyJWT  │
│  ReAct主管)   │   └──────────────────────┘   └────────┘
└──────────────┘
```

## 模块边界（单向依赖）

- `ai` → `knowledge`（允许）；反向禁止。
- `bridge` 只做 HTTP↔MCP/业务编排的协议转换。
- `auth` 独立包，被 bridge 以依赖注入方式挂载。
- M1 起：Skill 单元只依赖 `knowledge`/`ai.engine`，不依赖 Orchestrator；注册表反向引用 Skill。

## 数据与存储

| 数据 | 存储 | 位置 |
|---|---|---|
| 知识卡片/决策备忘 | Obsidian Vault（Markdown + frontmatter） | `VAULT_PATH`（.env） |
| 向量索引 | Chroma PersistentClient | 本地持久目录 |
| 用户凭证（B1） | SQLite（bcrypt 哈希） | workbench 本地 |
| 用量记录（M4-B） | SQLite `usage_records`/`daily_usage_snapshots` | workbench 本地 |

## 质量门禁（ADR-0001 D5）

- ruff check + format、mypy src、pytest --cov（阈值分阶段收紧至 85%）
- CI：`.github/workflows/ci.yml`（backend job 先行；frontend job 待 B2 启用）

## 部署形态

本地自用（无公网、无 Docker）。开源用户：克隆 → 装依赖 → 配 .env → 启动（见 README）。
