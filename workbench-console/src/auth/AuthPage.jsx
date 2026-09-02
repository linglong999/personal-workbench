import React, { useEffect, useRef, useState } from 'react'
import { api, setMode } from '../api/client.js'
import { setToken, setUser } from './auth.js'

/* 登录门：登录 / 注册双 tab + 演示模式入口。
   - 登录注册调真实 Bridge（/api/auth/*），成功后 setToken + 切 LIVE
   - 演示模式：无 Bridge 也能体验前端（开源用户 clone 即用），免 token 进 MOCK
   - 密码规则与后端一致（≥6）；错误显示后端 detail（用户名重复/凭证错） */

export default function AuthPage({ onAuthed }) {
  const [tab, setTab] = useState('login')
  const [name, setName] = useState('')
  const [pass, setPass] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const nameRef = useRef(null)

  useEffect(() => {
    nameRef.current && nameRef.current.focus()
  }, [tab])

  const switchTab = (t) => {
    setTab(t)
    setErr('')
    setPass('')
  }

  const submit = (e) => {
    e.preventDefault()
    if (!name.trim() || !pass) {
      setErr('请输入用户名和密码')
      return
    }
    if (tab === 'register' && pass.length < 6) {
      setErr('密码至少 6 位（后端同样校验）')
      return
    }
    setBusy(true)
    setErr('')
    api('/auth/' + (tab === 'login' ? 'login' : 'register'), {
      username: name.trim(),
      password: pass,
    })
      .then((d) => {
        setToken(d.token)
        setUser(name.trim())
        setMode('live')
        onAuthed()
      })
      .catch((e2) => {
        const msg = e2.message
        if (msg === 'Failed to fetch')
          setErr('连不上 Bridge（127.0.0.1:8213）——请先启动后端，或改用演示模式')
        else if (msg === 'invalid credentials') setErr('用户名或密码不正确')
        else if (msg === 'password too short (min 6)') setErr('密码至少 6 位')
        else if (msg.startsWith('username already exists')) setErr('用户名已存在，试试登录')
        else setErr(msg)
      })
      .finally(() => setBusy(false))
  }

  const demo = () => {
    setMode('mock')
    onAuthed()
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="brand-mark">◈</span> 隐形式 AI 工作台
        </div>

        <div className="auth-tabs" role="tablist">
          <button
            role="tab"
            aria-selected={tab === 'login'}
            className={tab === 'login' ? 'on' : ''}
            onClick={() => switchTab('login')}
          >
            登录
          </button>
          <button
            role="tab"
            aria-selected={tab === 'register'}
            className={tab === 'register' ? 'on' : ''}
            onClick={() => switchTab('register')}
          >
            注册
          </button>
        </div>

        <form onSubmit={submit}>
          <label className="auth-field">
            <span>用户名</span>
            <input
              ref={nameRef}
              type="text"
              autoComplete="username"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="auth-field">
            <span>密码{tab === 'register' ? '（≥6 位）' : ''}</span>
            <input
              type="password"
              autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
              value={pass}
              onChange={(e) => setPass(e.target.value)}
            />
          </label>

          {err && (
            <p className="auth-err" role="alert">
              {err}
            </p>
          )}

          <button className="auth-submit" type="submit" disabled={busy}>
            {busy ? '连接中…' : tab === 'login' ? '进入工作台' : '创建账号并进入'}
          </button>
        </form>

        <div className="auth-sep">
          <span>或</span>
        </div>

        <button className="auth-demo" onClick={demo}>
          以演示模式进入 · 不连接后端
        </button>
        <p className="auth-hint">演示模式使用内置数据；连接真实 Vault 与 LLM 需登录（LIVE）。</p>
      </div>
    </div>
  )
}
