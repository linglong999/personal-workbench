import React, { useState } from 'react'
import GridShell from '../shell/GridShell.jsx'
import Widget from './Widget.jsx'
import { REGISTRY } from './registry.js'

/* widget 容器：注册表 → GridShell（拖拽/缩放/布局保存 wb-layout:usage-widgets）。
   ↻ bump 对应 widget 的 tick → 组件自行刷新（HealthWidget 重新探活）。
   GridShell 约定 item 结构静态：注册表是模块常量，只换内容不换节点（见 B3 集成约定）。 */
export default function WidgetGrid() {
  const [ticks, setTicks] = useState({})

  const items = REGISTRY.map((w) => ({
    id: w.id,
    x: w.size.x,
    y: w.size.y,
    w: w.size.w,
    h: w.size.h,
    node: (
      <Widget
        title={w.title}
        onRefresh={() => setTicks((t) => ({ ...t, [w.id]: (t[w.id] || 0) + 1 }))}
      >
        <w.component tick={ticks[w.id] || 0} cfg={w.props || {}} />
      </Widget>
    ),
  }))

  return <GridShell storageKey="usage-widgets" items={items} />
}
