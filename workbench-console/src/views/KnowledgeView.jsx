import React from 'react'

/* 知识：第二大脑。卡片点击 = 检索该卡片（LIVE 真实向量检索）。 */
export default function KnowledgeView({ onSearch }) {
  const cards = [
    { title: 'Prompt 六要素', desc: '角色 · 上下文 · 任务 · 格式 · 示例 · 边界。' },
    { title: '确认型 Agent', desc: '高置信度自主收，低置信度才升级到人。' },
    { title: '环境隔离预案', desc: '刚由复盘沉淀而来，AI 已打标签并关联到「验收」项目。', isNew: true },
  ]

  return (
    <section className="view">
      <header className="view-head">
        <h1>知识</h1>
        <p className="view-sub">你的第二大脑。AI 自动打标签与关联。</p>
      </header>
      <div className="library">
        <article className="kb-card kb-main" onClick={() => onSearch('根因分析法（RCA）')}>
          <span className="kb-type">知识卡片</span>
          <h2>根因分析法（RCA）</h2>
          <p className="kb-desc">面对故障与偏差，先问「为什么」五次，不要急着归因于人。</p>
          <div className="kb-tags">
            <span className="tag tag-blue">方法论</span>
            <span className="tag tag-soft">调试</span>
            <span className="tag tag-soft">复盘</span>
          </div>
        </article>
        <div className="kb-grid">
          {cards.map((c) => (
            <article
              key={c.title}
              className={'kb-card' + (c.isNew ? ' kb-new' : '')}
              onClick={() => onSearch(c.title)}
            >
              <span className="kb-type">知识卡片{c.isNew ? ' · 新' : ''}</span>
              <h3>{c.title}</h3>
              <p className="kb-desc">{c.desc}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
