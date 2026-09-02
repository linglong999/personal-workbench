import React, { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { bridgeDown, openNote } from '../utils.js'

/* 检索：LIVE 模式真实向量检索知识库（search_knowledge）。
   pending（来自其他视图的 searchFor）触发自动检索；点击结果直开 Obsidian。 */
export default function SearchView({ mode, toast, pending }) {
  const [q, setQ] = useState('')
  // results: null=未搜索 / []=空命中 / Array
  const [results, setResults] = useState(null)
  const [note, setNote] = useState('') // '检索中…' / 失败提示

  const doSearch = async (text) => {
    if (!text.trim()) return
    setNote('检索中…')
    try {
      const d = await api('/search_knowledge', { query: text.trim(), top_k: 5 })
      setResults(d.results || [])
      setNote('')
    } catch {
      setResults(null)
      setNote('检索失败：Bridge 未启动。')
      bridgeDown(toast)
    }
  }

  useEffect(() => {
    if (!pending) return
    setQ(pending.q)
    doSearch(pending.q)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending])

  return (
    <section className="view">
      {mode !== 'live' ? (
        <div className="empty">
          <span className="empty-ico" aria-hidden="true">⌕</span>
          <h2>检索</h2>
          <p>用自然语言问你的知识库。（LIVE 模式下可用真实向量检索）</p>
        </div>
      ) : (
        <div className="live-search">
          <header className="view-head">
            <h1>检索</h1>
            <p className="view-sub">用自然语言问你的知识库 · 真实向量检索（LIVE）。</p>
          </header>
          <div className="sr-bar">
            <input
              type="text"
              className="sr-input"
              placeholder="例如：RAG 幻觉怎么处理？"
              aria-label="检索知识库"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && doSearch(q)}
            />
            <button className="btn" onClick={() => doSearch(q)}>
              检索
            </button>
          </div>
          <div className="sr-results">
            {note && <p className="sr-note">{note}</p>}
            {!note && results && results.length === 0 && (
              <p className="sr-note">没有命中 —— 换个问法试试。</p>
            )}
            {!note &&
              results &&
              results.map((r, i) => (
                <article
                  key={i}
                  className="sr-item"
                  onClick={() => r.obsidian_uri && openNote(r, r.path, { mode, toast })}
                >
                  <span className="sr-rank">{i + 1}</span>
                  <div>
                    <h3>{r.title || '未命名'}</h3>
                    <p>{(r.content || '').slice(0, 160)}</p>
                  </div>
                  {r.obsidian_uri && (
                    <span className="sr-open" title="在 Obsidian 中打开">↗</span>
                  )}
                </article>
              ))}
          </div>
        </div>
      )}
    </section>
  )
}
