import React, { useEffect, useRef } from 'react'
import { GridStack } from 'gridstack'
import 'gridstack/dist/gridstack.min.css'
import { loadLayout, saveLayout } from './layout.js'

/* GridShell：GridStack 容器（拖拽 / 缩放 / 布局自动保存）。
   集成约定（React 与 GridStack 共存的关键）：
   - item 的 DOM 由 React 渲染（.grid-stack-item + gs-* 属性），位置由 GridStack 接管；
     item 内容必须静态（不因 state 重渲染换 DOM），本组件只用于静态卡片区。
   - 恢复布局不走 grid.load()（会动 DOM、与 React 冲突），而是渲染前用 saved 覆盖初始位置。
   - 卸载 destroy(false)：只解绑行为不移除 DOM，让 React 正常卸载。 */

export default function GridShell({ storageKey, items }) {
  const ref = useRef(null)

  useEffect(() => {
    const grid = GridStack.init(
      {
        cellHeight: 80,
        margin: 10,
        column: 12,
        float: true,
        draggable: { handle: '.kb-grip' },
        resizable: { handles: 'se' },
      },
      ref.current,
    )
    const persist = () => {
      const layout = {}
      grid.engine.nodes.forEach((n) => {
        if (n.id != null) layout[String(n.id)] = { x: n.x, y: n.y, w: n.w, h: n.h }
      })
      saveLayout(storageKey, layout)
    }
    grid.on('change', persist)
    return () => grid.destroy(false)
    // items 静态：仅在容器生命周期挂一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storageKey])

  const saved = loadLayout(storageKey) || {}

  return (
    <div className="grid-shell" ref={ref}>
      {items.map((it) => {
        const pos = saved[it.id] || it
        return (
          <div
            key={it.id}
            className="grid-stack-item"
            gs-id={it.id}
            gs-x={pos.x}
            gs-y={pos.y}
            gs-w={pos.w}
            gs-h={pos.h}
          >
            <div className="grid-stack-item-content">{it.node}</div>
          </div>
        )
      })}
    </div>
  )
}
