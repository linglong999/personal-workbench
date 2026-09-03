import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { apiGet, getMode, mockStatsFor } from '../api/client.js'
import { bridgeDown, fireToast } from '../utils.js'
import UPlotChart, { barPaths, cssVar } from './UPlotChart.jsx'

/* M4-B3 知识存量 widget：KPI（总卡片/双链/Chroma）+ 分类分布柱状 + 新增趋势折线。
   LIVE → GET /api/stats?include=knowledge&range=7d|30d；MOCK → 内置演示数据 +
   toast 标识（决策 15）；掉线 → 自显离线态 + bridgeDown 提示。
   tick（面板 ↻）或 range 切换时重新拉取。 */

let mockNotified = false // MOCK 演示提示只 toast 一次（防两 widget 刷屏）

export default function KnowledgeStockWidget({ tick }) {
  const [range, setRange] = useState('7d')
  const [data, setData] = useState(null)
  const [offline, setOffline] = useState(false)

  useEffect(() => {
    if (getMode() !== 'live') {
      setData(mockStatsFor(range).knowledge)
      setOffline(false)
      if (!mockNotified) {
        mockNotified = true
        fireToast('知识存量 / 用量趋势 widget 正在显示 <b>内置演示数据</b>（MOCK）')
      }
      return undefined
    }
    let alive = true
    apiGet(`/stats?include=knowledge&range=${range}`)
      .then((d) => {
        if (!alive) return
        setOffline(false)
        setData(d.knowledge || null)
      })
      .catch(() => {
        if (!alive) return
        setOffline(true)
        bridgeDown((m, dur) => fireToast(m, dur))
      })
    return () => {
      alive = false
    }
  }, [tick, range])

  const distNames = useMemo(
    () => (data ? data.distribution.map((d) => d.name) : []),
    [data],
  )
  const buildDist = useCallback(
    (w, h) => ({
      width: w,
      height: h,
      legend: { show: false },
      cursor: { show: false },
      padding: [6, 4, 0, 4],
      scales: { x: { time: false }, y: { range: (u, min, max) => [0, Math.max(max, 1)] } },
      axes: [
        {
          values: (u, vals) => vals.map((v) => (distNames[v] || '').slice(0, 2)),
          stroke: cssVar('--muted'),
          grid: { show: false },
          size: 16,
          font: '10px system-ui',
        },
        { stroke: cssVar('--muted'), grid: { stroke: cssVar('--rule'), width: 1 /devicePixelRatio } },
      ],
      series: [
        {},
        {
          label: '卡片数',
          stroke: cssVar('--acc'),
          fill: cssVar('--acc-soft'),
          width: 2,
          paths: barPaths(),
          points: { show: false },
        },
      ],
    }),
    [distNames],
  )

  const trendDates = useMemo(() => (data ? data.trend.map((t) => t.date.slice(5)) : []), [data])
  const buildTrend = useCallback(
    (w, h) => ({
      width: w,
      height: h,
      legend: { show: false },
      cursor: { show: false },
      padding: [6, 4, 0, 4],
      scales: { x: { time: false }, y: { range: (u, min, max) => [min, Math.max(max, 1)] } },
      axes: [
        {
          values: (u, vals) => vals.map((v) => trendDates[v] || ''),
          stroke: cssVar('--muted'),
          grid: { show: false },
          size: 16,
          font: '10px system-ui',
        },
        { stroke: cssVar('--muted'), grid: { stroke: cssVar('--rule'), width: 1 / devicePixelRatio } },
      ],
      series: [
        {},
        {
          label: '新增',
          stroke: cssVar('--acc-deep'),
          fill: cssVar('--acc-soft'),
          width: 2,
          spanGaps: true,
          points: { show: false },
        },
      ],
    }),
    [trendDates],
  )

  const distData = data
    ? [data.distribution.map((_, i) => i), data.distribution.map((d) => d.count)]
    : [[], []]
  const trendData = data
    ? [data.trend.map((_, i) => i), data.trend.map((t) => t.value)]
    : [[], []]

  return (
    <div className="ksw">
      <div className="ksw-kpis">
        <div className="us-card">
          <b>{data ? data.total_notes : '—'}</b>
          <span>卡片总数</span>
        </div>
        <div className="us-card">
          <b>{data ? data.links : '—'}</b>
          <span>双链边数</span>
        </div>
        <div className="us-card us-cost">
          <b>{data ? data.chroma_count : '—'}</b>
          <span>Chroma</span>
        </div>
      </div>

      <div className="ksw-sec">
        <div className="ksw-sec-head">
          <span>分类分布</span>
          <div className="ksw-range" role="tablist" aria-label="时间范围">
            {['7d', '30d'].map((r) => (
              <button
                key={r}
                className={'ksw-rbtn' + (range === r ? ' on' : '')}
                onClick={() => setRange(r)}
                role="tab"
                aria-selected={range === r}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
        {data ? (
          <UPlotChart data={distData} buildOpts={buildDist} height={104} />
        ) : (
          <div className="ksw-empty">{offline ? 'Bridge 离线 —— 启动后点 ↻' : '加载中…'}</div>
        )}
      </div>

      <div className="ksw-sec">
        <div className="ksw-sec-head">
          <span>新增趋势</span>
        </div>
        {data ? (
          <UPlotChart data={trendData} buildOpts={buildTrend} height={92} />
        ) : (
          <div className="ksw-empty">{offline ? 'Bridge 离线 —— 启动后点 ↻' : '加载中…'}</div>
        )}
      </div>
    </div>
  )
}
