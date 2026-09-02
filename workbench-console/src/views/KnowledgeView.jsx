import React from 'react'
import GridShell from '../shell/GridShell.jsx'

/* 知识：第二大脑。卡片点击 = 检索该卡片（LIVE 真实向量检索）。
   M0-B3：卡片 widget 化进 GridShell —— 可拖拽（⠿ 手柄）/ 缩放，布局自动保存（wb-layout:knowledge）。
   GridShell 约定 item 内容静态，故卡片数据为常量。 */
const CARDS = [
  {
    id: 'rca',
    x: 0,
    y: 0,
    w: 8,
    h: 5,
    main: true,
    title: '根因分析法（RCA）',
    desc: '面对故障与偏差，先问「为什么」五次，不要急着归因于人。',
    tags: ['方法论', '调试', '复盘'],
  },
  {
    id: 'prompt6',
    x: 8,
    y: 0,
    w: 4,
    h: 3,
    title: 'Prompt 六要素',
    desc: '角色 · 上下文 · 任务 · 格式 · 示例 · 边界。',
  },
  {
    id: 'confirm-agent',
    x: 8,
    y: 3,
    w: 4,
    h: 3,
    title: '确认型 Agent',
    desc: '高置信度自主收，低置信度才升级到人。',
  },
  {
    id: 'env-iso',
    x: 0,
    y: 5,
    w: 8,
    h: 3,
    isNew: true,
    title: '环境隔离预案',
    desc: '刚由复盘沉淀而来，AI 已打标签并关联到「验收」项目。',
  },
]

function Card({ c, onSearch }) {
  return (
    <article
      className={'kb-card' + (c.main ? ' kb-main' : '') + (c.isNew ? ' kb-new' : '')}
      style={{ position: 'relative' }}
      onClick={() => onSearch(c.title)}
    >
      <span className="kb-grip" title="拖拽移动">⠿</span>
      <span className="kb-type">知识卡片{c.isNew ? ' · 新' : ''}</span>
      {c.main ? <h2>{c.title}</h2> : <h3>{c.title}</h3>}
      <p className="kb-desc">{c.desc}</p>
      {c.tags && (
        <div className="kb-tags">
          {c.tags.map((t) => (
            <span key={t} className={'tag ' + (t === '方法论' ? 'tag-blue' : 'tag-soft')}>
              {t}
            </span>
          ))}
        </div>
      )}
    </article>
  )
}

export default function KnowledgeView({ onSearch }) {
  return (
    <section className="view">
      <header className="view-head">
        <h1>知识</h1>
        <p className="view-sub">你的第二大脑。AI 自动打标签与关联。</p>
      </header>
      <div className="library">
        <GridShell
          storageKey="knowledge"
          items={CARDS.map((c) => ({ id: c.id, x: c.x, y: c.y, w: c.w, h: c.h, node: <Card c={c} onSearch={onSearch} /> }))}
        />
      </div>
    </section>
  )
}
