import React, { createContext, useContext, useEffect, useState } from 'react'
import { THEMES } from './themes.js'

const ThemeCtx = createContext({ theme: 'paper', setTheme: () => {} })
const THEME_KEY = 'wb-theme'

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    try {
      return localStorage.getItem(THEME_KEY) || 'paper'
    } catch {
      return 'paper'
    }
  })

  useEffect(() => {
    const vars = (THEMES[theme] || THEMES.paper).vars
    // 先清旧主题 token 再写新值，避免主题间残留
    const allKeys = new Set(Object.values(THEMES).flatMap((t) => Object.keys(t.vars)))
    for (const k of allKeys) document.documentElement.style.removeProperty(k)
    for (const [k, v] of Object.entries(vars)) document.documentElement.style.setProperty(k, v)
    try {
      localStorage.setItem(THEME_KEY, theme)
    } catch {
      /* ignore */
    }
  }, [theme])

  const setTheme = (t) => THEMES[t] && setThemeState(t)

  return <ThemeCtx.Provider value={{ theme, setTheme }}>{children}</ThemeCtx.Provider>
}

export function useTheme() {
  return useContext(ThemeCtx)
}
