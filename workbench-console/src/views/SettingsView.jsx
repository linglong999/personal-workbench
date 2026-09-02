import React from 'react'
import { useTheme } from '../theme/ThemeProvider.jsx'
import { THEMES } from '../theme/themes.js'
import { resetLayout } from '../shell/layout.js'
import { setMode } from '../api/client.js'
import { getUser, isAuthed, logout } from '../auth/auth.js'

/* 设置：账号（B4 认证入口）+ 外观（主题 / 布局）+ 占位（工作区 / 模型 / 白名单目录）。 */
export default function SettingsView({ toast }) {
  const { theme, setTheme } = useTheme()

  const applyTheme = (id) => {
    setTheme(id)
    toast('已切换主题 · ' + THEMES[id].label)
  }

  const resetAll = () => {
    resetLayout('knowledge')
    toast('已恢复默认布局，刷新页面生效')
    setTimeout(() => window.location.reload(), 600)
  }

  // 登出：清 token 后刷新——live 无 token 落登录页；mock 留在演示模式（豁免语义不变）
  const doLogout = () => {
    logout()
    toast('已登出')
    setTimeout(() => window.location.reload(), 500)
  }

  // 演示模式下去登录：借 logout() 的认证事件广播，置 live 后 RequireAuth 落到登录页
  const goLogin = () => {
    setMode('live')
    logout()
  }

  return (
    <section className="view">
      <div className="empty">
        <span className="empty-ico" aria-hidden="true">⚙</span>
        <h2>设置</h2>
        <p>账号 / 外观 / 工作区 / 模型 / 白名单目录。</p>
      </div>

      <div className="library" style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <article className="kb-card" style={{ position: 'relative', maxWidth: 560 }}>
          <span className="kb-type">账号</span>
          <h3>{isAuthed() ? '已登录' : '演示模式 · 未登录'}</h3>
          <p className="kb-desc" style={{ marginBottom: 10 }}>
            {isAuthed()
              ? '当前用户：' + (getUser() || '（未知）') + ' · LIVE 可访问真实 Vault 与 LLM。'
              : '演示数据只在前端流转；连接真实后端（127.0.0.1:8213）需要登录。'}
          </p>
          {isAuthed() ? (
            <button className="btn btn-ghost" onClick={doLogout}>
              登出
            </button>
          ) : (
            <button
              className="btn"
              style={{ background: 'var(--acc-soft)', color: 'var(--acc-deep)' }}
              onClick={goLogin}
            >
              去登录 / 注册
            </button>
          )}
        </article>

        <article className="kb-card kb-main" style={{ position: 'relative', maxWidth: 560 }}>
          <span className="kb-type">外观</span>
          <h3>主题</h3>
          <p className="kb-desc" style={{ marginBottom: 10 }}>
            全局配色即时生效并持久保存（wb-theme）。
          </p>
          <div style={{ display: 'flex', gap: 8 }}>
            {Object.entries(THEMES).map(([id, t]) => (
              <button
                key={id}
                className="btn"
                style={
                  theme === id
                    ? { background: 'var(--ink-panel)', color: 'var(--ink-panel-fg)' }
                    : { background: 'var(--acc-soft)', color: 'var(--acc-deep)' }
                }
                onClick={() => applyTheme(id)}
              >
                {t.label}
                {theme === id ? ' · 当前' : ''}
              </button>
            ))}
          </div>

          <h3 style={{ marginTop: 16 }}>布局</h3>
          <p className="kb-desc" style={{ marginBottom: 10 }}>
            知识卡片支持拖拽（⠿）与缩放，位置自动保存。重置将恢复初始排布。
          </p>
          <button className="btn btn-ghost" onClick={resetAll}>
            恢复默认布局
          </button>
        </article>
      </div>
    </section>
  )
}
