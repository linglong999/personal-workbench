import React, { useCallback, useEffect, useRef, useState } from 'react'
import { getMode, setMode } from './api/client.js'
import { ThemeProvider } from './theme/ThemeProvider.jsx'
import RequireAuth from './auth/RequireAuth.jsx'
import { isAuthed } from './auth/auth.js'
import Sidebar from './components/Sidebar.jsx'
import InputBar from './components/InputBar.jsx'
import CardMarquee from './components/CardMarquee.jsx'
import ContextPanel from './components/ContextPanel.jsx'
import CommandPalette from './components/CommandPalette.jsx'
import AIConfirmModal from './components/AIConfirmModal.jsx'
import Toast from './components/Toast.jsx'
import InboxView from './views/InboxView.jsx'
import TodayView from './views/TodayView.jsx'
import ProjectView from './views/ProjectView.jsx'
import ReviewView from './views/ReviewView.jsx'
import KnowledgeView from './views/KnowledgeView.jsx'
import TagsView from './views/TagsView.jsx'
import SearchView from './views/SearchView.jsx'
import UsageView from './views/UsageView.jsx'
import SettingsView from './views/SettingsView.jsx'

/* 外壳编排：视图路由 + MOCK/LIVE 模式 + toast + 侧栏折叠 + 全局快捷键 + 主题。 */
export default function App() {
  return (
    <ThemeProvider>
      <RequireAuth>
        <Shell />
      </RequireAuth>
    </ThemeProvider>
  )
}

function Shell() {
  const [mode, setModeState] = useState(getMode())
  const [view, setView] = useState('inbox')
  const [sideHidden, setSideHidden] = useState(false)
  const [cmdOpen, setCmdOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  // 跨视图检索：{q, n}，n 递增保证同词重复触发
  const [pendingSearch, setPendingSearch] = useState(null)
  const [toastMsg, setToastMsg] = useState('')
  const toastTimer = useRef(null)
  const searchN = useRef(0)

  const toast = useCallback((msg, dur) => {
    setToastMsg(msg)
    if (toastTimer.current) clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToastMsg(''), dur || 2600)
  }, [])

  useEffect(() => () => toastTimer.current && clearTimeout(toastTimer.current), [])

  const toggleMode = useCallback(() => {
        const m = mode === 'live' ? 'mock' : 'live'
        // 未登录（演示模式）不可进 LIVE：Bridge 的业务端点全部要 token
        if (m === 'live' && !isAuthed()) {
            toast('LIVE 需要先登录 —— 请在「设置 · 账号」登录后再切换')
            return
        }
        setMode(m)
        setModeState(m)
        toast(
            m === 'live'
                ? '已切换到 LIVE · 真实调用本地 Bridge (:8213)'
                : '已切换到 MOCK · 使用内置演示数据',
        )
    }, [mode, toast])

  // searchFor：切到检索视图并自动执行（LIVE）；MOCK 提示切换
  const searchFor = useCallback(
    (text) => {
      if (mode !== 'live') {
        toast('真实检索需要 <b>LIVE</b> 模式 —— 点输入条右侧的 MOCK 切换')
        return false
      }
      searchN.current += 1
      setPendingSearch({ q: text, n: searchN.current })
      setView('search')
      return true
    },
    [mode, toast],
  )

  // 全局快捷键：Ctrl/⌘+B 侧栏折叠、Ctrl/⌘+K 命令面板
  useEffect(() => {
    const onKey = (e) => {
      if (e.ctrlKey || e.metaKey) {
        const k = e.key.toLowerCase()
        if (k === 'b') {
          e.preventDefault()
          setSideHidden((s) => !s)
        } else if (k === 'k') {
          e.preventDefault()
          setCmdOpen(true)
        }
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  return (
    <div className={'app' + (sideHidden ? ' side-hidden' : '')}>
      {/* 常驻折叠窄条：sidebar 收起后，用它展开 */}
      {sideHidden && (
        <div className="side-rail">
          <button
            className="rail-btn"
            title="展开侧栏 (Ctrl/⌘+B)"
            aria-label="展开侧栏"
            onClick={() => setSideHidden(false)}
          >
            ☰
          </button>
        </div>
      )}

      <Sidebar
        view={view}
        onNav={setView}
        onCmdK={() => setCmdOpen(true)}
        onToggleSide={() => setSideHidden((s) => !s)}
        onAiQueue={() => setConfirmOpen(true)}
      />

      <main className="workspace" role="main">
        <InputBar mode={mode} onToggleMode={toggleMode} toast={toast} />

        {/* 稍后再看是演示假数据：LIVE（自己真实使用）时整条隐藏，避免干扰 */}
        {mode !== 'live' && <CardMarquee toast={toast} />}

        <div className="views">
          {view === 'inbox' && <InboxView />}
          {view === 'today' && <TodayView mode={mode} toast={toast} />}
          {view === 'projects' && <ProjectView mode={mode} toast={toast} />}
          {view === 'review' && <ReviewView toast={toast} setView={setView} />}
          {view === 'knowledge' && <KnowledgeView onSearch={searchFor} />}
          {view === 'tags' && <TagsView mode={mode} toast={toast} onSearch={searchFor} />}
          {view === 'search' && <SearchView mode={mode} toast={toast} pending={pendingSearch} />}
          {view === 'usage' && <UsageView mode={mode} toast={toast} />}
          {view === 'settings' && <SettingsView toast={toast} />}
        </div>

        <Toast msg={toastMsg} />
      </main>

      <ContextPanel onSearch={searchFor} />

      <CommandPalette
        open={cmdOpen}
        onClose={() => setCmdOpen(false)}
        mode={mode}
        toast={toast}
        onNav={setView}
      />
      <AIConfirmModal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        toast={toast}
      />
    </div>
  )
}
