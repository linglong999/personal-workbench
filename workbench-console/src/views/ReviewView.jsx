import React from 'react'

/* 复盘：左侧事实、右侧 AI 提炼；复盘完成后沉淀为知识。 */
export default function ReviewView({ toast, setView }) {
  return (
    <section className="view">
      <header className="view-head">
        <h1>复盘</h1>
        <p className="view-sub">AI 在左侧事实、右侧提炼；复盘完成后沉淀为知识。</p>
      </header>
      <div className="review-grid">
        <div className="review-panel">
          <h3 className="col-title">本周发生过什么</h3>
          <ul className="fact-list">
            <li>• 完成 Task 2-8 端到端验收（Mock + 真实 LLM）</li>
            <li>• README 重写为理念引导版</li>
            <li>• 决定走「理念 + 示例」开源路线</li>
          </ul>
        </div>
        <div className="review-panel review-ai">
          <h3 className="col-title">
            <span className="ai-chip">AI 提炼</span>
          </h3>
          <ul className="fact-list">
            <li>• 偏差：决策闭环检查缺一条「问题」关联</li>
            <li>• 可沉淀：环境隔离预案 → 知识卡片</li>
            <li>• 下次：验收前先列环境风险清单</li>
          </ul>
          <button
            className="btn btn-ghost"
            onClick={() => {
              setView('knowledge')
              toast('已沉淀为知识卡片「环境隔离预案」 [撤销]')
            }}
          >
            沉淀为知识卡片
          </button>
        </div>
      </div>
    </section>
  )
}
