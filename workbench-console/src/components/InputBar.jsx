import React, { useEffect, useRef, useState } from 'react'
import { api, folderFor, mockRule, ruleFor } from '../api/client.js'
import { bridgeDown, esc } from '../utils.js'

/* 全局输入条：AI 隐形式识别（MOCK 关键词 / LIVE 真实 LLM 防抖分类）+ Enter 落盘。
   LIVE 写入 vault：未分类过（或分类为通用「任务/想法」）时先 classify_text 再 create_note。 */
export default function InputBar({ mode, onToggleMode, toast }) {
  const [value, setValue] = useState('')
  // hint: null=隐藏 / {loading:true} / {type, rule, live}
  const [hint, setHint] = useState(null)
  const lastLabel = useRef('') // 最近一次分类结果，Enter 写入时用
  const debounceTimer = useRef(null)
  const committing = useRef(false) // 写入中防抖：双击/回车连按不重复落盘

  useEffect(() => () => debounceTimer.current && clearTimeout(debounceTimer.current), [])

  const showHint = (type, rule, live) => {
    lastLabel.current = type
    setHint({ type, rule, live })
  }

  const onInput = (v) => {
    setValue(v)
    const t = v.trim()
    lastLabel.current = '' // 换了输入内容，旧分类作废，提交时重新分类
    if (!t) {
      setHint(null)
      return
    }
    if (mode !== 'live') {
      const m = mockRule(t)
      showHint(m.type, m.rule, false)
      return
    }
    // LIVE：防抖 600ms 后走 Bridge 真实分类（classify_text）
    setHint({ loading: true })
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => {
      api('/classify_text', { text: t })
        .then((d) => {
          const label = (d.label || '').trim()
          if (label) {
            showHint(label, ruleFor(label), true)
          } else {
            const m = mockRule(t)
            showHint(m.type, m.rule, false)
          }
        })
        .catch(() => {
          const m = mockRule(t)
          showHint(m.type, m.rule, false)
          bridgeDown(toast)
        })
    }, 600)
  }

  const write = (v, label) => {
    const folder = folderFor(label)
    const d0 = new Date()
    const today =
      d0.getFullYear() +
      '-' +
      String(d0.getMonth() + 1).padStart(2, '0') +
      '-' +
      String(d0.getDate()).padStart(2, '0')
    const title = v.replace(/[\\/:*?"<>|#[\]]/g, '-').slice(0, 24)
    const content = `---\ntype: ${label}\nsource: console-input\ndate: ${today}\n---\n\n${v}`
    committing.current = true
    api('/create_note', { folder, title, content })
      .then((d) => {
        const fn = (d.path || '').split(/[\\/]/).pop()
        toast(
          '已存入 vault ·「' +
            folder +
            '」/ ' +
            esc(fn) +
            (d.obsidian_uri ? ' · <a href="' + d.obsidian_uri + '">在 Obsidian 打开 ↗</a>' : ''),
        )
        setValue('')
        setHint(null)
        committing.current = false
      })
      .catch(() => {
        toast('写入失败：Bridge 未启动，内容未保存（仍在输入框）')
        bridgeDown(toast)
        committing.current = false
      })
  }

  const commit = () => {
    if (committing.current || !value.trim()) return
    const v = value.trim()
    if (mode !== 'live') {
      toast('已接住，AI 自动归位为「想法」到收件箱 [撤销]')
      setValue('')
      setHint(null)
      return
    }
    // LIVE：真实写入 vault —— 未分类过则先分类再落盘
    setHint(null)
    const label = lastLabel.current
    if (label && label !== '任务' && label !== '想法') {
      write(v, label)
    } else {
      committing.current = true
      api('/classify_text', { text: v })
        .then((d) => {
          committing.current = false
          write(v, (d.label || '').trim() || '输入')
        })
        .catch(() => {
          committing.current = false
          write(v, '输入')
          bridgeDown(toast)
        })
    }
  }

  return (
    <div className="capture" role="search">
      <span className="capture-mark" aria-hidden="true">＋</span>
      <input
        type="text"
        className="capture-input"
        placeholder="接住想法 / 任务 / 问题 —— 随手记，剩下的交给工作台"
        aria-label="快速输入"
        value={value}
        onChange={(e) => onInput(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && commit()}
      />
      <button
        className={'mode-chip' + (mode === 'live' ? ' is-live' : '')}
        title="切换 MOCK / LIVE（LIVE 连接本地 Bridge :8213，需先启动 uvicorn workbench.bridge:app）"
        onClick={onToggleMode}
      >
        {mode === 'live' ? 'LIVE' : 'MOCK'}
      </button>
      <span className="capture-hint mono">Ctrl/⌘+K</span>
      {hint && (
        <div className="ai-hint">
          {hint.loading ? (
            <b>✦ AI 识别中…</b>
          ) : (
            <>
              <b>
                ✦ AI 识别为「{hint.type}」
                {hint.live && (
                  <span className="mono" style={{ fontSize: '.75em', opacity: '.75' }}>
                    · 真实 LLM
                  </span>
                )}
              </b>{' '}
              · 建议{hint.rule}{' '}
              <button
                className="btn btn-mini"
                style={{ marginLeft: '8px' }}
                onClick={commit}
              >
                确认归位
              </button>{' '}
              <span style={{ opacity: '.7' }}>· 可改</span>
            </>
          )}
        </div>
      )}
    </div>
  )
}
