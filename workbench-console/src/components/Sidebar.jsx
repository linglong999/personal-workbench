import React from 'react'

const MAIN = [
  { v: 'inbox', ico: '☖', label: '收件箱', badge: 3 },
  { v: 'today', ico: '◉', label: '今天' },
  { v: 'projects', ico: '▤', label: '项目 / 行动' },
  { v: 'review', ico: '↻', label: '复盘' },
  { v: 'knowledge', ico: '❖', label: '知识' },
]

const SUB = [
  { v: 'tags', ico: '#', label: '标签' },
  { v: 'search', ico: '⌕', label: '检索' },
  { v: 'usage', ico: '∑', label: '用量' },
]

export default function Sidebar({ view, onNav, onCmdK, onToggleSide, onAiQueue }) {
  return (
    <aside className="sidebar" aria-label="主导航">
      <div className="brand">
        <button
          className="icon-btn"
          title="收起 / 展开侧栏 (Ctrl/⌘+B)"
          aria-label="收起或展开侧栏"
          aria-pressed="false"
          onClick={onToggleSide}
        >
          ☰
        </button>
        <span className="brand-mark" aria-hidden="true">✦</span>
        <span className="brand-name">个人工作台</span>
        <button
          className="icon-btn"
          title="命令面板 (Ctrl/⌘+K)"
          aria-label="打开命令面板"
          onClick={onCmdK}
        >
          ⌘
        </button>
      </div>

      <nav className="nav">
        {MAIN.map((it) => (
          <button
            key={it.v}
            className={'nav-item' + (view === it.v ? ' is-active' : '')}
            onClick={() => onNav(it.v)}
          >
            <span className="nav-ico">{it.ico}</span>
            {it.label}{' '}
            {it.badge != null && <span className="nav-badge">{it.badge}</span>}
          </button>
        ))}

        <div className="nav-sep" aria-hidden="true"></div>
        {SUB.map((it) => (
          <button
            key={it.v}
            className={'nav-item nav-sub' + (view === it.v ? ' is-active' : '')}
            onClick={() => onNav(it.v)}
          >
            <span className="nav-ico">{it.ico}</span>
            {it.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-foot">
        <button
          className={'nav-item nav-sub' + (view === 'settings' ? ' is-active' : '')}
          onClick={() => onNav('settings')}
        >
          <span className="nav-ico">⚙</span>设置
        </button>
      </div>

      <button
        className="ai-queue"
        title="AI 待确认"
        aria-label="AI 待确认项"
        onClick={onAiQueue}
      >
        <span className="ai-queue-dot" aria-hidden="true"></span>
        <span>AI 待确认</span>
        <span className="ai-queue-num">3</span>
      </button>
    </aside>
  )
}
