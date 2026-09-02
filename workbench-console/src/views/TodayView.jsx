import React, { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { bridgeDown } from '../utils.js'

const FIRST_TASK = '完成个人工作台 2-8 验收'

/* 今天：今日任务 + 一条来自过往经验的 AI 提示。
   LIVE：用第一条任务真实召回历史经验（reopen_task），回填洞察卡。 */
export default function TodayView({ mode, toast }) {
  // insight: null=默认文案 / 'empty' / JSX（真实召回）
  const [insight, setInsight] = useState(null)

  useEffect(() => {
    if (mode !== 'live') {
      setInsight(null)
      return
    }
    api('/reopen_task', { task: FIRST_TASK, top_k: 3 })
      .then((d) => {
        const rs = d.results || []
        if (!rs.length) {
          setInsight('empty')
          return
        }
        setInsight(
          <>
            与「{FIRST_TASK}」最相关的过往经验（真实检索）：
            <b>{rs.map((r) => r.title || r.id || '').join(' · ')}</b>
          </>,
        )
      })
      .catch(() => bridgeDown(toast))
  }, [mode, toast])

  return (
    <section className="view">
      <header className="view-head">
        <h1>今天</h1>
        <p className="view-sub">今日任务 + 一条来自过往经验的 AI 提示。</p>
      </header>

      <div className="task-board">
        <div className="task-col">
          <h3 className="col-title">待做</h3>
          <div className="task" data-priority="high">
            <span className="task-dot" aria-hidden="true"></span>
            <div>
              <b>{FIRST_TASK}</b>
              <span className="task-meta">项目 · 高优先级</span>
            </div>
          </div>
          <div className="task" data-priority="med">
            <span className="task-dot" aria-hidden="true"></span>
            <div>
              <b>整理用户访谈记录</b>
              <span className="task-meta">产品 · 关联知识 2 条</span>
            </div>
          </div>
          <div className="task" data-priority="med">
            <span className="task-dot" aria-hidden="true"></span>
            <div>
              <b>起草本周复盘</b>
              <span className="task-meta">复盘 · 待 AI 提炼</span>
            </div>
          </div>
        </div>
        <div className="task-col">
          <h3 className="col-title">已完成</h3>
          <div className="task is-done">
            <span className="task-dot" aria-hidden="true"></span>
            <div>
              <s>更新知识卡片 根因分析法</s>
              <span className="task-meta">知识 · 三小时前</span>
            </div>
          </div>
        </div>
      </div>

      <div className="ai-insight" role="note">
        <span className="ai-insight-mark" aria-hidden="true">✦</span>
        <div>
          <b>来自过往经验</b>
          <p>
            {insight === null &&
              '你上次做验收时，把「环境隔离」列为首要风险并提前解决了 —— 这次可以复用这条复盘。'}
            {insight === 'empty' &&
              '知识库里还没有与该任务相关的历史经验 —— 做完这单，它会替你记下来。'}
            {insight !== null && insight !== 'empty' && insight}
          </p>
        </div>
      </div>
    </section>
  )
}
