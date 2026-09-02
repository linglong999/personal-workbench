import React, { useState } from 'react'

/* 右侧上下文面板：环境式 AI 说明 + 相关笔记（点击检索）+ AI 助手提问框。 */
export default function ContextPanel({ onSearch }) {
  const [ask, setAsk] = useState('')

  const onAskKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && ask.trim()) {
      e.preventDefault()
      if (onSearch(ask.trim())) setAsk('') // MOCK 下保留输入不丢内容
    }
  }

  return (
    <aside className="context" aria-label="上下文面板">
      <div className="ctx-block">
        <h4 className="ctx-title">环境式 AI</h4>
        <p className="ctx-note">AI 在后台为你做这些，你无需逐一确认。</p>
        <ul className="ctx-ops">
          <li>
            <span className="ctx-t">已归档 2 条</span>
            <span className="tag tag-soft">自动</span>
          </li>
          <li>
            <span className="ctx-t">已打标签 3 条</span>
            <span className="tag tag-soft">自动</span>
          </li>
          <li>
            <span className="ctx-t">关联到「验收」项目</span>
            <span className="tag tag-soft">自动</span>
          </li>
        </ul>
      </div>
      <div className="ctx-block">
        <h4 className="ctx-title">相关笔记</h4>
        <p className="ctx-note">与当前查看内容最相关。</p>
        <ul className="ctx-links">
          <li onClick={() => onSearch('根因分析法（RCA）')}>↳ 根因分析法（RCA）</li>
          <li onClick={() => onSearch('确认型 Agent 设计')}>↳ 确认型 Agent 设计</li>
        </ul>
      </div>
      <div className="ctx-block">
        <h4 className="ctx-title">AI 助手</h4>
        <p className="ctx-note">可主动提问，但日常流程不依赖它。</p>
        <textarea
          className="ctx-ask"
          rows="2"
          placeholder="在任何页面按 ⌘K 也能提问…"
          aria-label="向 AI 提问"
          value={ask}
          onChange={(e) => setAsk(e.target.value)}
          onKeyDown={onAskKey}
        />
      </div>
    </aside>
  )
}
