import React from 'react'

/* 占位 widget：cfg.hint 说明 M4 将接入什么。统一空壳、不造假数据。 */
export default function PlaceholderWidget({ cfg }) {
  return (
    <div className="phw">
      <span className="phw-badge">M4</span>
      <p>{(cfg && cfg.hint) || '数据源待接入'}</p>
      <p className="phw-sub">槽位已就绪 · 容器可拖拽/缩放，布局自动保存</p>
    </div>
  )
}
