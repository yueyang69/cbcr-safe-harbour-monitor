import { useState } from 'react'
import { generateBriefing } from '../api/endpoints'
import type { BriefingResponse } from '../types'

interface AIBriefingCardProps {
  fiscalYear: number
}

export function AIBriefingCard({ fiscalYear }: AIBriefingCardProps) {
  const [briefing, setBriefing] = useState<BriefingResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const generate = async () => {
    setLoading(true)
    setError('')
    try {
      const result = await generateBriefing(fiscalYear)
      setBriefing(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'AI简报生成失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <article className="ai-briefing-card">
      <div className="ai-briefing-header">
        <div>
          <h3>🤖 AI 风险简报</h3>
          <p className="ai-disclaimer">AI生成摘要，仅供参考，不构成税务意见</p>
        </div>
        <button
          className="button button-secondary"
          onClick={() => void generate()}
          disabled={loading}
        >
          {loading ? '生成中...' : '生成简报'}
        </button>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      {briefing && (
        <div className="ai-briefing-content">
          <p>{briefing.briefing}</p>
          <small className="ai-timestamp">
            生成时间：{new Date(briefing.generated_at).toLocaleString('zh-CN')}
          </small>
        </div>
      )}

      {!briefing && !error && !loading && (
        <div className="ai-briefing-empty">
          点击"生成简报"按钮，AI将自动分析当前辖区数据并生成风险摘要（最多200字）。
        </div>
      )}
    </article>
  )
}
