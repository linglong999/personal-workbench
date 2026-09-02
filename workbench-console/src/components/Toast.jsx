import React from 'react'

/* 右下角 toast。msg 为 HTML 字符串（与原版一致，动态值已在调用侧 esc） */
export default function Toast({ msg }) {
  return (
    <div
      className={'toast' + (msg ? ' show' : '')}
      role="status"
      aria-live="polite"
      dangerouslySetInnerHTML={{ __html: msg || '' }}
    />
  )
}
