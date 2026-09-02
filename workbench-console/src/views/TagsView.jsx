import React, { useEffect, useState } from 'react'
import { api, mockTags } from '../api/client.js'
import { bridgeDown, openNote } from '../utils.js'

/* 标签浏览：MOCK 演示 / LIVE 真实聚合（list_tags）。
   统一数据形状：{tag: [{title, obsidian_uri}]}，uri 存在则点击直开 Obsidian。 */
export default function TagsView({ mode, toast, onSearch }) {
  const [tags, setTags] = useState(mockTags)
  // active: null=列表隐藏 / {tag, cards}
  const [active, setActive] = useState(null)

  useEffect(() => {
    if (mode !== 'live') {
      setTags(mockTags)
      return
    }
    api('/list_tags')
      .then((d) => setTags(d.tags || {}))
      .catch(() => {
        setTags(mockTags)
        bridgeDown(toast)
      })
  }, [mode, toast])

  return (
    <section className="view">
      <div className="view-head">
        <h1>标签</h1>
        <p className="view-sub">按主题浏览你的知识网络（LIVE 展示真实标签）。</p>
      </div>
      <div className="tag-cloud">
        {Object.keys(tags)
          .sort()
          .map((tag) => {
            const cards = tags[tag]
            return (
              <button
                key={tag}
                className="tag tag-blue"
                title={cards.map((x) => x.title).join('、')}
                onClick={() => setActive({ tag, cards })}
              >
                #{tag} <span className="tag-count">{cards.length}</span>
              </button>
            )
          })}
      </div>
      {active && (
        <ul className="tag-card-list">
          {active.cards.map((item, i) => (
            <li
              key={i}
              className="tag-card-item"
              onClick={() => {
                if (!openNote(item, item.path, { mode, toast })) onSearch(item.title)
              }}
            >
              <b>{item.title}</b>
              <span className="mono">↗ Obsidian</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
