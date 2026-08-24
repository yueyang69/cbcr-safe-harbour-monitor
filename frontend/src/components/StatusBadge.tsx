import type { ResultStatus } from '../types'

const statusLabels: Record<ResultStatus, string> = {
  PASS: 'Pass', FAIL: 'Fail', WARNING: 'Risk warning', INCOMPLETE: 'Incomplete',
}

export function StatusBadge({ status, compact = false }: { status: ResultStatus; compact?: boolean }) {
  const tone = {
    PASS: 'status-pass', FAIL: 'status-fail', WARNING: 'status-warning', INCOMPLETE: 'status-incomplete',
  }[status]
  return <span className={`status-badge ${tone} ${compact ? 'status-compact' : ''}`}><span className="status-dot" aria-hidden="true" />{statusLabels[status]}</span>
}
