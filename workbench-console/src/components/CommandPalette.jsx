import React, { useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { bridgeDown } from '../utils.js'

/* 命令面板（Ctrl/⌘+K）：方向键选择、Enter 执行、Esc/点外关闭。
   LIVE 下「决策检查」走真实扫描（scan_decision_closed_loop），其余为演示反馈。 */
const CMDS = [
  { cmd: 'review', label: '/ 生成今日复盘', mock: '已生成今日复盘草稿 [撤销]' },
  { cmd: 'archive', label: '/ 归档输入', mock: '已归档 1 条输入 [撤销]' },
  { cmd: 'decision', label: '/ 检查决策闭环', mock: '决策检查：发现 1 条缺关联，已列入待确认' },
  { cmd: 'tag', label: '/ 自动打标签', mock: '已为你自动打标签 · 3 条 [撤销]' },
  { cmd: 'knowledge', label: '/ 沉淀为知识卡片', mock: '已沉淀「环境隔离预案」为知识卡片 [撤销]' },
]

export default function CommandPalette({ open, onClose, mode, toast }) {
  const [sel, setSel] = useState(0)
  const [text, setText] = useState('')
  const inputRef = useRef(null)

  useEffect(() => {
    if (open) {
      setText('')
      setSel(0)
      inputRef.current && inputRef.current.focus()
    }
  }, [open])

  if (!open) return null

  const run = (c) => {
    onClose()
    if (c.cmd === 'decision' && mode === 'live') {
      toast('决策检查中…（真实扫描决策备忘）')
      api('/scan_decision_closed_loop')
        .then((d) => {
          const miss = d.missing || []
          toast(
            miss.length
              ? '决策检查（真实）：发现 ' + miss.length + ' 条缺关联 —— 已列入待确认'
              : '决策检查（真实）：闭环完整 ✓',
          )
        })
        .catch(() => bridgeDown(toast))
      return
    }
    toast(c.mock)
  }

  const onKey = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSel((i) => Math.min(i + 1, CMDS.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSel((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      run(CMDS[sel])
    } else if (e.key === 'Escape') {
      onClose()
    }
  }

  return (
    <div
      className="cmd-modal"
      role="dialog"
      aria-modal="true"
      aria-label="命令面板"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="cmd-box">
        <input
          ref={inputRef}
          type="text"
          className="cmd-input"
          placeholder="输入命令，如 /复盘 /归档 /决策检查"
          aria-label="命令"
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            setSel(0)
          }}
          onKeyDown={onKey}
        />
        <ul className="cmd-list">
          {CMDS.map((c, i) => (
            <li
              key={c.cmd}
              className={i === sel ? 'sel' : ''}
              onClick={() => run(c)}
            >
              {c.label}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
