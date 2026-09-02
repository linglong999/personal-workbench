import React from 'react'
import { useTheme } from '../theme/ThemeProvider.jsx'
import { THEMES } from '../theme/themes.js'
import { resetLayout } from '../shell/layout.js'

/* 设置：外观（主题 / 布局）+ 占位（工作区 / 模型 / 白名单目录）。B4 接入认证入口。 */
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

  return (
    <section className="view">
      <div className="empty">
        <span className="empty-ico" aria-hidden="true">⚙</span>
        <h2>设置</h2>
        <p>工作区 / 模型 / 白名单目录。</p>
      </div>

      <div className="library" style={{ marginTop: 8 }}>
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
