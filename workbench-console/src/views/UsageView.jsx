import React, { useEffect, useState } from 'react'
import { apiGet } from '../api/client.js'
import { bridgeDown, esc } from '../utils.js'

function fmtCost(c) {
  if (!c) return '¥0'
  return c < 0.01 ? '¥' + c.toFixed(4) : '¥' + c.toFixed(2)
}

function fmtTokens(n) {
  if (n >= 10000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

/* 用量观测：LIVE 下渲染 Bridge 记录的工具调用 + LLM token 与成本估算（GET /api/usage）。 */
export default function UsageView({ mode, toast }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    if (mode !== 'live') {
      setData(null)
      return
    }
    apiGet('/usage')
      .then(setData)
      .catch(() => bridgeDown(toast))
  }, [mode, toast])

  const note = () => {
    if (mode !== 'live') {
      return '用量观测基于 Bridge 的真实调用记录 —— 切到 LIVE 后，这里会显示每次调用、token 与成本。'
    }
    const evs = data ? data.events || [] : []
    if (!evs.length) {
      return '还没有调用记录 —— 去输入条打个字、或切到「今天 / 检索」试一次，回来这里看数据。'
    }
    const p = data.prices || {}
    return (
      '单价（可改 .env）：输入 ¥' +
      (p.in_per_m || '?') +
      '/M · 输出 ¥' +
      (p.out_per_m || '?') +
      '/M，成本为估算值；Bridge 重启后计数清零。最近 ' +
      evs.length +
      ' 条 / 最多保留 50 条。'
    )
  }

  return (
    <section className="view">
      <header className="view-head">
        <h1>用量</h1>
        <p className="view-sub">每次调用、token 消耗与成本估算 —— 评测与迭代的数据底座（LIVE）。</p>
      </header>
      <div className="usage-summary">
        {mode === 'live' && data && (
          <>
            <div className="us-card">
              <b>{(data.totals || {}).tool_calls || 0}</b>
              <span>工具调用</span>
            </div>
            <div className="us-card">
              <b>{(data.totals || {}).llm_calls || 0}</b>
              <span>LLM 调用</span>
            </div>
            <div className="us-card">
              <b>{fmtTokens((data.totals || {}).prompt_tokens || 0)}</b>
              <span>输入 tokens</span>
            </div>
            <div className="us-card">
              <b>{fmtTokens((data.totals || {}).completion_tokens || 0)}</b>
              <span>输出 tokens</span>
            </div>
            <div className="us-card us-cost">
              <b>{fmtCost((data.totals || {}).cost || 0)}</b>
              <span>成本估算</span>
            </div>
          </>
        )}
      </div>
      <ul className="usage-list">
        {mode === 'live' &&
          data &&
          (data.events || []).map((e, i) => {
            const isTool = e.kind === 'tool'
            return (
              <li className="usage-item" key={i}>
                <span className="ui-ts mono">{esc(e.ts)}</span>
                <span className={'ui-kind ' + (isTool ? 'ui-tool' : 'ui-llm')}>
                  {isTool ? '工具' : 'LLM'}
                </span>
                <span className="ui-name mono">{esc(e.name)}</span>
                <span className="ui-detail">{esc(e.detail || '')}</span>
                <span className="ui-tk mono">
                  {e.pt || e.ct
                    ? '↑' + fmtTokens(e.pt || 0) + ' ↓' + fmtTokens(e.ct || 0)
                    : isTool
                      ? e.ms != null
                        ? e.ms + 'ms'
                        : '—'
                      : '—'}
                </span>
                <span className="ui-cost mono">{fmtCost(e.cost || 0)}</span>
              </li>
            )
          })}
      </ul>
      <p className="usage-note mono">{note()}</p>
    </section>
  )
}
