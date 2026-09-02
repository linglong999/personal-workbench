import React from 'react'
import { inboxData } from '../api/client.js'

/* 收件箱：待处理的碎片，AI 已按类型与置信度归拢（MOCK 演示数据）。 */
export default function InboxView() {
  return (
    <section className="view">
      <header className="view-head">
        <h1>收件箱</h1>
        <p className="view-sub">待处理的碎片。AI 已按类型与置信度为你归拢。</p>
      </header>
      <ul className="inbox-list">
        {inboxData.map((it, i) => (
          <li className="inbox-item" key={i}>
            <span className={'inbox-kind ' + it.cls}>{it.kind}</span>
            <span className="inbox-txt">{it.txt}</span>
            <span className="inbox-conf">
              <b>✦</b> {it.conf}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
