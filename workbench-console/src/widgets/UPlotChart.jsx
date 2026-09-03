import React, { useEffect, useRef } from 'react'
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'
import { useTheme } from '../theme/ThemeProvider.jsx'

/* 当前主题的 CSS 变量取色（ThemeProvider 写在 documentElement；主题切换触发
   UPlotChart 重建 → 颜色重取，双主题即适配）。 */
export function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#888'
}

/* 柱状图路径绘制器（分布图用）：series.paths = barPaths()。
   uplot 1.6.x npm 包不含官方 demo 的 bars 绘制器，这里按 README 的
   path 协议自实现：柱宽 = 相邻 x 像素间距 * 0.6，基线 y=0，支持负值。 */
export function barPaths() {
  return (u, seriesIdx, idx0, idx1) => {
    const xData = u.data[0]
    const yData = u.data[seriesIdx]
    if (!xData || xData.length < 2) return null
    const step = Math.abs(u.valToPos(xData[1], 'x') - u.valToPos(xData[0], 'x'))
    const barW = Math.max(2, step * 0.6)
    const base = u.valToPos(0, 'y')
    const p = new Path2D()
    for (let i = idx0; i <= idx1; i++) {
      const v = yData[i]
      if (v == null) continue
      const cx = u.valToPos(xData[i], 'x')
      const y = u.valToPos(v, 'y')
      p.rect(cx - barW / 2, Math.min(y, base), barW, Math.abs(y - base))
    }
    return p
  }
}

/* uPlot 的 React 封装：props = { data, buildOpts(width, height), height }。
   - data / buildOpts / theme 变化 → 销毁重建（uPlot 不支持热改 opts；个人规模无压力）
   - ResizeObserver 跟随容器宽（gridstack 拖宽/窗口缩放自适应）
   - 卸载 destroy()（检查表 9）
   buildOpts 由调用方 useCallback 构建（引用稳定，避免无谓重建）。 */
export default function UPlotChart({ data, buildOpts, height = 120 }) {
  const wrapRef = useRef(null)
  const { theme } = useTheme()

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return undefined
    const width = Math.max(el.clientWidth, 80)
    const up = new uPlot(buildOpts(width, height), data, el)
    const ro = new ResizeObserver(() => {
      up.setSize({ width: Math.max(el.clientWidth, 80), height })
    })
    ro.observe(el)
    return () => {
      ro.disconnect()
      up.destroy()
    }
  }, [data, buildOpts, height, theme])

  return <div ref={wrapRef} className="uplot-wrap" />
}
