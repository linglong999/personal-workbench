import React, { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { bridgeDown } from '../utils.js'

/* 项目 / 行动：行动关联知识，AI 在决策遗漏时提醒。
   LIVE：真实扫描决策备忘（scan_decision_closed_loop），回填闭环提示卡。 */
export default function ProjectView({ mode, toast }) {
  // insight: null=默认文案 / 'ok' / {missing}
  const [insight, setInsight] = useState(null)

  useEffect(() => {
    if (mode !== 'live') {
      setInsight(null)
      return
    }
    api('/scan_decision_closed_loop')
      .then((d) => {
        const miss = d.missing || []
        setInsight(miss.length ? { missing: miss } : 'ok')
      })
      .catch(() => bridgeDown(toast))
  }, [mode, toast])

  return (
    <section className="view">
      <header className="view-head">
        <h1>项目 / 行动</h1>
        <p className="view-sub">每个行动关联到知识，AI 会在决策遗漏时提醒你。</p>
      </header>
      <ul className="proj-list">
        <li className="proj-item">
          <span className="proj-ico" aria-hidden="true">❖</span>
          <div>
            <b>个人工作台开源项目</b>
            <span className="task-meta">3 个行动 · 2 条决策</span>
          </div>
          <span className="tag tag-blue">进行中</span>
        </li>
        <li className="proj-item">
          <span className="proj-ico" aria-hidden="true">❖</span>
          <div>
            <b>AI 素养学习计划</b>
            <span className="task-meta">5 个行动 · 8 篇知识</span>
          </div>
          <span className="tag tag-blue">进行中</span>
        </li>
        <li className="proj-item">
          <span className="proj-ico" aria-hidden="true">❖</span>
          <div>
            <b>面试作品集打磨</b>
            <span className="task-meta">1 个行动</span>
          </div>
          <span className="tag tag-amber">待开始</span>
        </li>
      </ul>
      <div className="ai-insight" role="note">
        <span className="ai-insight-mark" aria-hidden="true">✦</span>
        <div>
          <b>决策闭环提示</b>
          <p>
            {insight === null &&
              '「项目2-8验收」这条决策尚未关联到任何「问题」—— 建议补一条来形成闭环。'}
            {insight === 'ok' && '真实扫描：决策闭环完整，所有决策均已关联问题 ✓'}
            {insight && insight.missing && (
              <>
                <b>真实扫描</b>：{insight.missing.join('；')} —— 建议补关联形成闭环。
              </>
            )}
          </p>
        </div>
      </div>
    </section>
  )
}
