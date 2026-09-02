import React, { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { bridgeDown } from '../utils.js'
import { useTheme } from '../theme/ThemeProvider.jsx'
import { THEMES } from '../theme/themes.js'
import { resetLayout } from '../shell/layout.js'

/* 命令面板（Ctrl/⌘+K）：命令注册表 + 输入过滤搜索。
   方向键选择、Enter 执行、Esc/点外关闭。
   LIVE 下「决策检查」走真实扫描（scan_decision_closed_loop），其余为演示反馈。 */

const NAV_ITEMS = [
  { v: 'inbox', label: '收件箱' },
  { v: 'today', label: '今天' },
  { v: 'projects', label: '项目 / 行动' },
  { v: 'review', label: '复盘' },
  { v: 'knowledge', label: '知识' },
  { v: 'tags', label: '标签' },
  { v: 'search', label: '检索' },
  { v: 'usage', label: '用量' },
  { v: 'settings', label: '设置' },
]

export default function CommandPalette({ open, onClose, mode, toast, onNav }) {
  const { theme, setTheme } = useTheme()
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

  const cmds = useMemo(() => {
    const list = [
      { id: 'review', group: '操作', label: '生成今日复盘', run: () => toast('已生成今日复盘草稿 [撤销]') },
      { id: 'archive', group: '操作', label: '归档输入', run: () => toast('已归档 1 条输入 [撤销]') },
      {
        id: 'decision',
        group: '操作',
        label: '检查决策闭环',
        run: () => {
          if (mode !== 'live') {
            toast('决策检查：发现 1 条缺关联，已列入待确认')
            return
          }
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
        },
      },
      { id: 'tag', group: '操作', label: '自动打标签', run: () => toast('已为你自动打标签 · 3 条 [撤销]') },
      {
        id: 'knowledge',
        group: '操作',
        label: '沉淀为知识卡片',
        run: () => toast('已沉淀「环境隔离预案」为知识卡片 [撤销]'),
      },
    ]

    // 外观：主题切换（注册表列出全部主题，当前项跳过）+ 布局
    for (const [id, t] of Object.entries(THEMES)) {
      list.push({
        id: 'theme-' + id,
        group: '外观',
        label: '切换主题 · ' + t.label + (theme === id ? '（当前）' : ''),
        run: () => {
          setTheme(id)
          toast('已切换主题 · ' + t.label)
        },
      })
    }
    list.push({
      id: 'reset-layout',
      group: '外观',
      label: '恢复默认布局',
      run: () => {
        resetLayout('knowledge')
        toast('已恢复默认布局，刷新页面生效')
      },
    })

    // 导航：九视图
    for (const n of NAV_ITEMS) {
      list.push({ id: 'nav-' + n.v, group: '导航', label: '去 ' + n.label, run: () => onNav(n.v) })
    }
    return list
  }, [mode, toast, theme, setTheme, onNav])

  // 输入过滤（label 模糊包含）
  const filtered = useMemo(
    () => (text.trim() ? cmds.filter((c) => c.label.toLowerCase().includes(text.trim().toLowerCase())) : cmds),
    [cmds, text],
  )

  useEffect(() => {
    setSel(0)
  }, [text])

  if (!open) return null

  const run = (c) => {
    onClose()
    c && c.run()
  }

  const onKey = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSel((i) => Math.min(i + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSel((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      run(filtered[sel])
    } else if (e.key === 'Escape') {
      onClose()
    }
  }

  // 分组渲染（保持注册顺序）
  const groups = []
  filtered.forEach((c) => {
    const g = groups[groups.length - 1]
    if (g && g.name === c.group) g.items.push(c)
    else groups.push({ name: c.group, items: [c] })
  })

  let idx = -1

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
          placeholder="搜索命令，如 主题 / 布局 / 检索 / 复盘…"
          aria-label="命令"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
        />
        <ul className="cmd-list">
          {groups.map((g) => (
            <li key={g.name} className="cmd-group">
              <span className="cmd-group-name mono">{g.name}</span>
              <ul>
                {g.items.map((c) => {
                  idx += 1
                  const i = idx
                  return (
                    <li
                      key={c.id}
                      className={i === sel ? 'sel' : ''}
                      onMouseEnter={() => setSel(i)}
                      onClick={() => run(c)}
                    >
                      {c.label}
                    </li>
                  )
                })}
              </ul>
            </li>
          ))}
          {filtered.length === 0 && <li className="cmd-empty">没有匹配的命令</li>}
        </ul>
      </div>
    </div>
  )
}
