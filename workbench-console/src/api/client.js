/* API 客户端：MOCK / LIVE 双模式。
   LIVE 走本地 Bridge（127.0.0.1:8213，FastAPI 暴露的 5 个 MCP 工具同构端点）。
   B4 在 api()/apiGet() 的 headers 注入 Authorization: Bearer <token>（唯一收口点）。 */

const BASE = 'http://127.0.0.1:8213/api'
const MODE_KEY = 'wb-mode'

export function getMode() {
  try {
    return localStorage.getItem(MODE_KEY) || 'mock'
  } catch {
    return 'mock' // 隐私模式无 localStorage
  }
}

export function setMode(m) {
  try {
    localStorage.setItem(MODE_KEY, m)
  } catch {
    /* ignore */
  }
}

export async function api(path, body) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  })
  if (!res.ok) throw new Error('HTTP ' + res.status)
  return res.json()
}

export async function apiGet(path) {
  const res = await fetch(BASE + path)
  if (!res.ok) throw new Error('HTTP ' + res.status)
  return res.json()
}

/* ───────── 归位规则（classify_text 标签 → 建议/目录）───────── */

// classify_text 的真实标签（输入/决策/实践/复盘/创造）→ 归位建议
export function ruleFor(label) {
  const map = {
    输入: '归入收件箱',
    决策: '进入决策备忘',
    实践: '放入项目 · 行动',
    复盘: '生成今日复盘',
    创造: '沉淀为知识卡片',
  }
  return map[label] || '归入收件箱'
}

// 分类标签 → vault 白名单目录（写入用）
export function folderFor(label) {
  return (
    {
      输入: '问题整理',
      决策: '决策备忘',
      实践: '行动记录',
      复盘: '复盘沉淀',
      创造: '知识卡片',
    }[label] || '问题整理'
  )
}

// MOCK：关键词分类（LIVE 无 Bridge 时也回退到这里）
export function mockRule(v) {
  if (/(复盘|总结|回顾)/.test(v)) return { type: '复盘', rule: '生成今日复盘' }
  if (/(任务|做完|搞定|安排)/.test(v)) return { type: '任务', rule: '放入项目 · 行动' }
  if (/(决策|决定|要不要|该不该)/.test(v)) return { type: '决策', rule: '进入决策备忘' }
  return { type: '想法', rule: '归入收件箱' }
}

/* ───────── MOCK 演示数据 ───────── */

export const inboxData = [
  {
    kind: '想法',
    cls: 'kind-idea',
    txt: '把「确认型 Agent」写成一篇对外讲的简洁说明',
    conf: '高置信度 · 已就位',
  },
  { kind: '任务', cls: 'kind-task', txt: '给开源项目补一个 LICENSE', conf: '高置信度 · 已就位' },
  { kind: '问题', cls: 'kind-q', txt: '这条该归到「复盘」还是「知识」？', conf: '低置信度 · AI 请你定夺' },
]

const C = (t) => ({ title: t })

export const mockTags = {
  RAG: [
    'GraphRAG',
    'RAG六步流水线',
    'RAG检索与生成',
    '混合检索与重排序',
    '向量化',
    'Embedding',
  ].map(C),
  Prompt工程: [
    'Prompt六要素',
    '角色设定三层结构',
    'SystemPrompt与UserPrompt',
    'Few-shot',
    'CRISPE框架',
    '肯定指令与否定指令',
  ].map(C),
  AgentWorkflow: [
    'Agent框架全景',
    'Agent四种模式',
    'LangGraph图抽象',
    '链式调用Chain',
    '子智能体Subagent',
    '编排vsAgent',
  ].map(C),
  思维模型: [
    '第一性原理',
    '金字塔原理',
    'MECE原则',
    '逆向思维',
    '六顶思考帽',
    '二八法则',
    'STAR法则',
  ].map(C),
}
