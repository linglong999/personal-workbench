import React from 'react'

/* 设置：占位（工作区 / 模型 / 白名单目录）。B4 接入认证入口。 */
export default function SettingsView() {
  return (
    <section className="view">
      <div className="empty">
        <span className="empty-ico" aria-hidden="true">⚙</span>
        <h2>设置</h2>
        <p>工作区 / 模型 / 白名单目录。</p>
      </div>
    </section>
  )
}
