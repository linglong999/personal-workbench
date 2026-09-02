import React, { useEffect, useState } from 'react'
import { BRIDGE_ORIGIN } from '../api/client.js'

/* 服务健康灯：轮询 Bridge /api/health（免鉴权端点，MOCK/LIVE 均可探测）。
   M0-B5 唯一接真实数据源的 widget——验证容器框架 fetch→render→refresh 全链路。
   tick 变化（面板 ↻ 或重新挂载）触发即时探活。 */
const POLL_MS = 30000

export default function HealthWidget({ tick }) {
  const [state, setState] = useState({ status: 'checking', model: '' })

  useEffect(() => {
    const check = () => {
      setState((s) => ({ ...s, status: 'checking' }))
      fetch(BRIDGE_ORIGIN + '/api/health')
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))))
        .then((d) => setState({ status: 'ok', model: d.model || '' }))
        .catch(() => setState({ status: 'down', model: '' }))
    }
    check()
    const t = setInterval(check, POLL_MS)
    return () => clearInterval(t)
  }, [tick])

  const label = { checking: '检测中', ok: '在线', down: '离线' }[state.status]

  return (
    <div className="hw">
      <div className="hw-row">
        <span className={'hl-dot hl-' + state.status} aria-hidden="true" />
        <b>本地 Bridge</b>
        <span className={'hw-st hw-st-' + state.status}>{label}</span>
      </div>
      <div className="hw-meta mono">
        {state.status === 'ok' ? '模型 ' + state.model + ' · 127.0.0.1:8213' : '127.0.0.1:8213'}
      </div>
      <div className="hw-meta">5 个 MCP 工具 · JWT 鉴权 · 每 30s 自动探活</div>
    </div>
  )
}
