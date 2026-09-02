import React from 'react'

/* 稍后再看 · 流动卡片条带（MOCK 演示数据，LIVE 模式整条隐藏）。
   站点图标用本地字母头像，不依赖 Google favicon 服务（国内不可达、离线亦可）。 */
const watchList = [
  { url: 'https://www.bilibili.com', title: 'B 站知识区 · AI 全栈导论', site: 'bilibili.com' },
  { url: 'https://www.youtube.com', title: 'Y Combinator · How to Build an AI', site: 'youtube.com' },
  { url: 'https://sspai.com', title: '少数派 · 个人知识库搭建复盘', site: 'sspai.com' },
  { url: 'https://zhihu.com', title: '知乎 · 如何建立第二大脑', site: 'zhihu.com' },
  { url: 'https://github.com', title: 'GitHub · agent 开源项目盘点', site: 'github.com' },
  { url: 'https://mp.weixin.qq.com', title: '公众号 · Prompt 工程实践指南', site: 'mp.weixin.qq.com' },
  { url: 'https://www.zhihu.com/column', title: '知乎专栏 · AI Native 产品思考', site: 'zhihu.com' },
  { url: 'https://arxiv.org', title: 'Arxiv · RAG 综述', site: 'arxiv.org' },
]

function letterOf(url) {
  try {
    return (new URL(url).hostname || '•')[0].toUpperCase()
  } catch {
    return '•'
  }
}

function Card({ it }) {
  return (
    <div className="wcard">
      <span className="wcard-fav">
        <span className="fallback">{letterOf(it.url)}</span>
      </span>
      <span className="wcard-info">
        <span className="wcard-title">{it.title}</span>
        <span className="wcard-site">{it.site}</span>
      </span>
    </div>
  )
}

export default function CardMarquee({ toast }) {
  // 无缝循环：一份内容渲染两组（A+A），动画平移 -50%，首尾相接
  const halves = [...watchList, ...watchList]
  return (
    <section className="watch-band" aria-label="稍后再看">
      <header className="watch-head">
        <h2>稍后再看</h2>
        <span className="watch-sub">来自视频 / 文章网站的收藏</span>
        <button
          className="icon-btn watch-add"
          title="添加一条"
          aria-label="添加稍后再看"
          onClick={() => toast('粘贴链接，AI 会把它归入「稍后再看」 [撤销]')}
        >
          ＋
        </button>
      </header>
      <div className="marquee-wrap">
        <div className="marquee-track">{halves.map((it, i) => <Card key={i} it={it} />)}</div>
      </div>
    </section>
  )
}
