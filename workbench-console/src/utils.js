/* 共享小工具：HTML 转义、Obsidian 唤起、Bridge 掉线提示。 */

export function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
  )
}

/* Bridge 掉线统一提示（8s 冷却防刷屏） */
let bridgeWarned = false
export function bridgeDown(toast) {
  if (bridgeWarned) return
  bridgeWarned = true
  toast(
    "⚠ 连不上 Bridge —— 请在 workbench/ 目录启动：<span class='mono'>uvicorn workbench.bridge:app --port 8213</span>",
  )
  setTimeout(() => {
    bridgeWarned = false
  }, 8000)
}

/* 点任何知识实体：有 obsidian_uri → 唤起 Obsidian 打开原笔记；MOCK → 提示切 LIVE。
   嵌入式预览浏览器会静默拦截外部协议，toast 始终附带路径与出路。返回是否已处理。 */
export function openNote(item, absPath, { mode, toast }) {
  if (item && item.obsidian_uri) {
    const a = document.createElement('a')
    a.href = item.obsidian_uri
    document.body.appendChild(a)
    a.click()
    a.remove()
    toast(
      '已请求 Obsidian 打开 · 若无反应，你在嵌入式预览里 ——' +
        '用 Chrome/Edge 打开 <b>http://127.0.0.1:8212</b> 可直连' +
        (absPath ? " · 文件 <span class='mono'>" + esc(absPath) + '</span>' : ''),
      5200,
    )
    return true
  }
  if (mode !== 'live') {
    toast('真实打开需要 <b>LIVE</b> 模式 —— 点输入条右侧的 MOCK 切换')
  }
  return false
}
