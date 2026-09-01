# 个人工作台 · M0 工程化 + React 重写 · 设计文档

> 日期：2026-09-01
> 版本：draft
> 状态：待审阅

---

## 0. 背景与定位

本项目的北极星是「贴进去 → 长成知识资产」的完整价值闭环。已完成：
阶段一（六层 Prompt 工程）、阶段二（MCP 服务，TDD）、阶段二+（Bridge + Console 双模式）、阶段三（开源上架 GitHub）。

本次 M0 是**将项目从"可运行脚本"升级为"可构建、可鉴权、可扩展、可部署的工程"**的正确形变。目标形态对齐 PRD 的 AI Native + Agentic：**主导航为知识价值闭环（L1），外壳为可扩展 Dashboard（L2），入口为鉴权（L0），并预留 Widget 容器（L3）**。

**迭代纪律**：明确"一个一个做"，M0 内部拆成有序批次，绝不一次性冲刺；否则会掉回"范围失控、做一半烂尾"的历史老坑。

---

## 1. 核心决策（本次已确认）

| 决策项 | 结论 | 影响 |
|---|---|---|
| **JWT 存储** | 方案 **A**：token 全存 `localStorage` | 前端一个 key，无 cookie/CORS/CSRF 复杂度 |
| **公网规划** | **取消** | Drop 反向代理/HTTPS/防攻击；只做本地环境 |
| **Docker** | **取消** | 本地一键环境改由本机 `uvicorn` + `npm run dev` 承担 |
| **服务健康灯** | **不纳入 M0**（属 L4，未勾选） | 留待后续 |
| **前端重写** | React + Vite，**等价迁移现有全部视图 + 接入新外壳/认证/widget** | 不丢能力 |
| 覆盖率门槛 | 后端主路径 **85%**（bridge 走行 >80%） | CI 强制 |

**做 → 工程化 + 前端重写 + L2 外壳 + L0 认证 + L3 widget 容器**
**不做 → Docker、公网、Web 终端、服务健康灯、新增生产功能（L1 主干留给 M1）**

---

## 2. 批次划分（一个一个做，每批可独立验收）

| 批次 | 内容 | 验收点 | 涉及 |
|---|---|---|---|
| **B0 规范** | ruff + mypy + coverage 85% + CI + ADR/架构文档/changelog | CI 全绿门禁 | 根目录 / workbench |
| **B1 后端认证** | 注册/登录/JWT（方案A）+ token 校验中间件 + 测试 | 鉴权端点可测 | workbench |
| **B2 React 化** | Vite+React 工程，等价迁移现有全部视图 | 自测清单全过、零回归 | workbench-console |
| **B3 外壳新功能** | GridStack 拖拽/缩放 + 布局保存 + 多主题 + 命令搜索/快捷键 | 拖拽与存储可用 | workbench-console |
| **B4 前端认证入口** | 登录/注册页 + JWT 路由守卫 | 未登录拦截，登录后进工作台 | workbench-console |
| **B5 Widget 容器** | 可扩展 widget 容器框架（先搭壳） | 空容器可挂载 | workbench-console |

---

## 3. 架构决策（ADR 首条：分层范式）

为 M1 主管 Agent 铺路，本项目采用**分层 + 模块边界**范式：

```
personal-workbench/
├── workbench/               # 后端（Python ∩ FastAPI ∩ FastMCP）
│   ├── src/workbench/
│   │   ├── ai/              # LLM + Agents（Classifier/Reviewer/Coach → 未来主管）
│   │   ├── knowledge/       # Vault 读写 + Vector 检索
│   │   ├── auth/            # 【B1 新增】认证：用户/JWT/依赖
│   │   ├── bridge.py        # HTTP Bridge（含鉴权中间件）
│   │   ├── config.py        # 环境配置
│   │   └── usage.py         # 用量观测
│   └── tests/
├── workbench-console/       # 前端（React ∩ Vite）【B2 起改造】
│   ├── src/
│   │   ├── api/             # fetch 封装 + MOCK/LIVE 切换
│   │   ├── auth/            # 【B4】登录/注册/路由守卫
│   │   ├── views/           # 各视图组件
│   │   ├── widgets/         # 【B5】widget 容器框架
│   │   ├── shell/           # 【B3】GridStack + 主题 + 命令面板
│   │   └── style/           # 设计 token（白·墨·金）
│   └── vite.config.ts
└── docs/                    # ADR / architecture / changelog
```

**模块边界原则**：每模块一个清晰职责，通过定义良好的接口通信，可独立测试。

---

## 4. B1 · 后端认证（方案 A）

### 数据
- **存储：SQLite**（单文件，Python 内置 `sqlite3`，无额外服务器）→ `workbench/.data/app.db`（该数据目录已 `.gitignore`）
- `users` 表：id / username(唯一) / password_hash(bcrypt) / created_at
- token：JWT，secret 来自 `.env`（不入库）

### 端点（Bridge 新增）
- `POST /api/auth/register`（username, password）→ 建用户
- `POST /api/auth/login`（username, password）→ 返回 access_token
- `GET /api/auth/me`（需 Bearer）→ 校验。

### 中间件
- 对受保护端点（`/api/*` 除 auth 外）校验 `Authorization: Bearer <token>`
- 失败→ 401。

### 安全
- 仅方案 A（localStorage 存取，无 cookie），不做 refresh token 轮换
- 密码 bcrypt 哈希，不落明文
- JWT secret 只从 `.env` 读，`.gitignore` 已排除

---

## 5. B2 · 前端 React 化（等价迁移）

现有 Console 能力（必须保留到 React）：
收件箱 / 今天 / 项目行动 / 复盘 / 知识 / 标签 / 检索 / 用量 / 设置 + 右侧上下文面板 + 命令面板（Ctrl+K）+ AI 待确认弹层 + MOCK/LIVE 切换。

**迁移清单**（现有 app.js ~26KB + index.html，逐项复刻）：
- [ ] MOCK/LIVE 双模式与 Bridge 降级（bridgeDown 提示）
- [ ] 分类归位规则（ruleFor / folderFor）
- [ ] 各视图渲染、AI 待确认、toast
- [ ] 输入条落盘（create_note + 向量同步）
- [ ] Obsidian URI 直开（读注册表上移后端已做，前端只渲染链接）
- [ ] 白·墨·金设计系统迁移为设计 token

**新增但不改语义**：组件化拆分、Vite 构建、ts(可选) 类型。
**零回归**：以既有 4 轮自测修掉的坑做回归验收清单。

---

## 6. B3 · 外壳新功能

- **GridStack.js**：拖拽/缩放网格布局；布局存 `localStorage`(key `wb-layout`)，会话间持久
- **多主题**：token 化主题（白·墨·金 + 至少一套），存 `wb-theme`
- **命令搜索/快捷键**：Ctrl+K 命令面板保留，增强为可发现命令 + 全局快捷键

---

## 7. B4 · 前端认证入口

- 登录页 / 注册页（未登录重定向）
- 路由守卫：未持有 token → 强制登录；持 token → 进工作台
- JWT 存 `localStorage`（方案 A）
- 401 处理：token 失效 → 登出回登录页

---

## 8. B5 · Widget 容器框架（先搭壳）

- 通用 widget 统一接口（id / title / render / refresh / config）
- 空容器可挂载、可扩展；数据源接入留到 M4 及以后
- 不接真实外部 API（天气/行情等），避免网络/隐私/密钥依赖

---

## 9. 测试策略

- 后端：现有 13 项 + 新增覆盖 auth 端点、覆盖率门槛 85%
- 前端：回归验收清单（复刻自测坑）+ 组件 smoke + CI build/lint
- CI：push/PR 触发，后端 pytest+coverage+mypy+ruff，前端 build+lint 全门禁

---

## 10. 错误处理与边界

- MOCK/LIVE 降级原样保留（Bridge 关 → 自动假数据）
- 认证失败/401 → 明确提示 + 回登录
- JWT 失效 → 静默登出，不白屏
- 所有密钥仅 `.env`；无公网、无对外暴露

---

## 11. 成功准则

M0 完成后：
1. 后端 CI 全绿（coverage≥85%，pytest、mypy、ruff 通过）
2. 前端 React 工程可构建、现有功能零回归
3. 注册/登录/JWT 闭环可用，未登录无法进入
4. GridStack 拖拽布局可保存；多主题可切换
5. Widget 容器已搭好接口，可挂载
6. ADR/架构文档/changelog 落盘

---

## 12. 明确不做（防范围蔓延）

- Docker、docker-compose、公网部署、HTTPS
- Web 终端、服务健康灯
- 新增生产数据源 widget（M4 再接入）
- L1 主干 agent 化（主管 Agent 属 M1）