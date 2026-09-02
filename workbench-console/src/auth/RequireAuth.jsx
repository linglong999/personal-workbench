import React, { useEffect, useState } from 'react'
import { getModeRaw } from '../api/client.js'
import { AUTH_EVENT, isAuthed } from './auth.js'
import AuthPage from './AuthPage.jsx'

/* 登录门：LIVE（调真实 Bridge）必须持 token；MOCK 为演示豁免。
   豁免仅在用户「明确选择过」演示模式时成立（wb-mode==='mock'）——
   全新用户（无 wb-mode）先见登录页，可一键进入演示；开源用户 clone 即用不受影响。
   401 广播（token 过期/失效）后重渲染：live 无 token → 登录页。 */

export default function RequireAuth({ children }) {
  const [, bumpState] = useState(0)

  useEffect(() => {
    const bump = () => bumpState((t) => t + 1)
    window.addEventListener(AUTH_EVENT, bump)
    return () => window.removeEventListener(AUTH_EVENT, bump)
  }, [])

  const ok = isAuthed() || getModeRaw() === 'mock'
  if (!ok) return <AuthPage onAuthed={() => bumpState((t) => t + 1)} />
  return children
}
