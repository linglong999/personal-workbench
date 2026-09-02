/* 认证态单点：token/user 存取 + 登出广播。
   项目无 URL 路由（视图是 React state），401 登出不能跳 '/#/login'，
   改为派发 'wb-auth' 事件，RequireAuth 监听后重渲染出登录页。 */

const TOKEN_KEY = 'wb-token'
const USER_KEY = 'wb-user'
export const AUTH_EVENT = 'wb-auth'

function ls() {
  try {
    return localStorage
  } catch {
    return null
  }
}

export function getToken() {
  return ls()?.getItem(TOKEN_KEY) || ''
}

export function setToken(t) {
  const s = ls()
  if (!s) return
  if (t) s.setItem(TOKEN_KEY, t)
  else s.removeItem(TOKEN_KEY)
}

export function getUser() {
  return ls()?.getItem(USER_KEY) || ''
}

export function setUser(u) {
  const s = ls()
  if (!s) return
  if (u) s.setItem(USER_KEY, u)
  else s.removeItem(USER_KEY)
}

export function logout() {
  setToken(null)
  setUser(null)
  window.dispatchEvent(new Event(AUTH_EVENT))
}

export function isAuthed() {
  return Boolean(getToken())
}
