import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { apiGet, getMode, mockStatsFor } from '../api/client.js'
import { bridgeDown, fireToast } from '../utils.js'
import UPlotChart, { cssVar } from './UPlotChart.jsx'

/* M4-B3 用量趋势 widget：KPI（LLM 调用/成本估算）+ 输入/输出 tokens 双序列折线。
   数据 = GET /api/stats?include=usage&range=7d|30d（B1 daily_trend 聚合，
   快照直查）。MOCK / 掉线降级同 KnowledgeStockWidget（mockNotified 在那侧共享）。 */

function fmtCost(c) {
  if (!c) return '¥0'
  return c < 0.01 ? '¥' + c.toFixed(4) : '¥' + c.toFixed(2)
}

function fmtTokens(n) {
  if (n >= 10000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

export default function UsageTrendWidget({ tick }) {
  const [range, setRange] = useState('7d')
  const [data, setData] = useState(null)
  const [offline, setOffline] = useState(false)

  useEffect(() => {
    if (getMode() !== 'live') {
      setData(mockStatsFor(range).usage)
      setOffline(false)
      return undefined
    }
    let alive = true
    apiGet(`/stats?include=usage&range=${range}`)
      .then((d) => {
        if (!alive) return
        setOffline(false)
        setData(d.usage || null)
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

  const trendDates = useMemo(() => (data ? data.trend.map((t) => t.date.slice(5)) : []), [data])
  const buildOpts = useCallback(
    (w, h) => ({
      width: w,
      height: h,
      legend: { show: false },
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
        {
          stroke: cssVar('--muted'),
          grid: { stroke: cssVar('--rule'), width: 1 / devicePixelRatio },
          values: (u, vals) => vals.map(fmtTokens),
        },
      ],
      series: [
        {},
        {
          label: '输入',
          stroke: cssVar('--acc'),
          fill: cssVar('--acc-soft'),
          width: 2,
          spanGaps: true,
          points: { show: false },
        },
        {
          label: '输出',
          stroke: cssVar('--acc-deep'),
          width: 2,
          spanGaps: true,
          points: { show: false },
        },
      ],
    }),
    [trendDates],
  )

  const totals = data
    ? data.trend.reduce(
        (a, t) => ({ req: a.req + (t.requests || 0), cost: a.cost + (t.cost || 0) }),
        { req: 0, cost: 0 },
      )
    : null
  const chartData = data
    ? [
        data.trend.map((_, i) => i),
        data.trend.map((t) => t.input_tokens || 0),
        data.trend.map((t) => t.output_tokens || 0),
      ]
    : [[], [], []]

  return (
    <div className="ksw">
      <div className="ksw-kpis">
        <div className="us-card">
          <b>{totals ? totals.req : '—'}</b>
          <span>LLM 调用（{range}）</span>
        </div>
        <div className="us-card us-cost">
          <b>{totals ? fmtCost(totals.cost) : '—'}</b>
          <span>成本估算（{range}）</span>
        </div>
      </div>

      <div className="ksw-sec">
        <div className="ksw-sec-head">
          <span>token 消耗</span>
          <div className="ksw-legend" aria-hidden="true">
            <i style={{ background: 'var(--acc)' }} />
            输入
            <i style={{ background: 'var(--acc-deep)' }} />
            输出
          </div>
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
          <UPlotChart data={chartData} buildOpts={buildOpts} height={148} />
        ) : (
          <div className="ksw-empty">{offline ? 'Bridge 离线 —— 启动后点 ↻' : '加载中…'}</div>
        )}
      </div>
    </div>
  )
}
