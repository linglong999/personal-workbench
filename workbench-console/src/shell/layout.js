/* 布局持久化：按容器 key 分命名空间存 localStorage。
   形状：{ [widgetId]: {x, y, w, h} }，B5 widget 容器复用。 */

const PREFIX = 'wb-layout'

export function loadLayout(key) {
  try {
    return JSON.parse(localStorage.getItem(PREFIX + ':' + key)) || null
  } catch {
    return null
  }
}

export function saveLayout(key, layout) {
  try {
    localStorage.setItem(PREFIX + ':' + key, JSON.stringify(layout))
  } catch {
    /* 隐私模式无 localStorage */
  }
}

export function resetLayout(key) {
  try {
    localStorage.removeItem(PREFIX + ':' + key)
  } catch {
    /* ignore */
  }
}
