import React from 'react'

/* widget 统一外壳：头部（标题 + 手动刷新 + 拖拽手柄）+ 内容区。
   契约见 registry.js。注意：不自带 .grid-stack-item——那是 GridShell 的职责
   （B3 集成约定：item DOM 由 GridShell 渲染，本组件作为 item 内容占满格子）。 */
export default function Widget({ title, onRefresh, children }) {
  return (
    <div className="widget">
      <span className="kb-grip" title="拖拽移动">⠿</span>
      <header className="widget-head">
        <span className="widget-title">{title}</span>
        <button className="widget-refresh" onClick={onRefresh} title="刷新" aria-label={'刷新 ' + title}>
          ↻
        </button>
      </header>
      <div className="widget-body">{children}</div>
    </div>
  )
}
