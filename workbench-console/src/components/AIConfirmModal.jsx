import React, { useState } from 'react'

/* AI 待确认弹层：低置信度操作升级到人，逐条确认。 */
const QUEUE = [
  { text: '将「整理访谈记录」归类到 产品?' },
  { text: '从复盘提炼「环境隔离预案」卡片?' },
  { text: '补一条问题关联到「2-8验收」决策?' },
]

export default function AIConfirmModal({ open, onClose, toast }) {
  const [confirmed, setConfirmed] = useState(() => new Set())

  if (!open) return null

  const confirmOne = (i) => {
    setConfirmed((s) => new Set(s).add(i))
    toast('已确认 · AI 继续 [撤销]')
  }

  return (
    <div
      className="confirm-toast"
      role="dialog"
      aria-modal="true"
      aria-label="AI 待确认"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="confirm-inner">
        <div className="confirm-head">
          <span className="ai-chip">AI 待确认 · 3</span>
          <button className="icon-btn" aria-label="关闭" onClick={onClose}>
            ×
          </button>
        </div>
        <ul className="confirm-list">
          {QUEUE.map((q, i) => (
            <li key={i} style={confirmed.has(i) ? { opacity: '0.4' } : undefined}>
              <span>{q.text}</span>
              <button className="btn btn-mini" onClick={() => confirmOne(i)}>
                确认
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
