import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getSummary } from '../api/endpoints'
import { StatusBadge } from '../components/StatusBadge'
import type { JurisdictionSummary, TestResult } from '../types'

const money = (value: string | number | null) => value == null ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(Number(value))
const testNames = { de_minimis: 'De minimis test', simplified_etr: 'Simplified ETR test', routine_profits: 'Routine profits test' }

function TestPanel({ name, result }: { name: string; result: TestResult }) {
  return <article className="test-panel"><div className="test-panel-head"><h3>{name}</h3><StatusBadge status={result.result} compact /></div><p>{result.explanation}</p>{result.threshold != null && <dl className="inline-metrics"><div><dt>Threshold</dt><dd>{(Number(result.threshold) * 100).toFixed(0)}%</dd></div>{result.value != null && name.includes('ETR') && <div><dt>Reported ETR</dt><dd>{(Number(result.value) * 100).toFixed(2)}%</dd></div>}</dl>}</article>
}

export function SummaryDetailPage() {
  const { id = '' } = useParams()
  const [summary, setSummary] = useState<JurisdictionSummary | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { getSummary(id).then(setSummary).catch((err: Error) => setError(err.message)) }, [id])
  if (error) return <section className="page-wrap"><div className="alert alert-error" role="alert">{error}</div><Link to="/dashboard">← Back to dashboard</Link></section>
  if (!summary) return <section className="page-wrap"><div className="empty-state">Loading jurisdiction explanation…</div></section>
  const evaluation = summary.evaluation
  return <section className="page-wrap detail-page"><Link className="back-link" to="/dashboard">← Back to dashboard</Link><div className="detail-hero"><div><p className="eyebrow">FY {summary.fiscal_year} / Jurisdiction detail</p><h1>{summary.jurisdiction}</h1><p>Aggregated from {summary.included_count} approved {summary.included_count === 1 ? 'entity' : 'entities'}.</p></div><StatusBadge status={summary.status} /></div>
    {evaluation?.warning && <div className="risk-banner" role="alert"><div aria-hidden="true">!</div><p><strong>Human review required</strong><span>{evaluation.warning}</span></p></div>}
    <dl className="summary-stats"><div><dt>Revenue</dt><dd>{money(summary.revenue)}</dd></div><div><dt>Profit before tax</dt><dd>{money(summary.pbt)}</dd></div><div><dt>Covered taxes</dt><dd>{money(summary.covered_taxes)}</dd></div><div><dt>Eligible payroll</dt><dd>{money(summary.payroll)}</dd></div><div><dt>Tangible assets</dt><dd>{money(summary.tangible_assets)}</dd></div></dl>
    <div className="section-heading"><div><h2>Why this result?</h2><p>Explanations below are returned by the deterministic backend rules engine.</p></div></div>
    <div className="test-grid">{evaluation && (Object.keys(testNames) as Array<keyof typeof testNames>).map((key) => <TestPanel key={key} name={testNames[key]} result={evaluation.tests[key]} />)}</div>
    <div className="decision-note"><strong>Decision boundary</strong><p>{summary.status === 'PASS' ? 'At least one Safe Harbour test passed. This jurisdiction is shown as PASS for this screening workflow.' : summary.status === 'WARNING' || summary.status === 'FAIL' ? 'All three tests failed. Processing stops at risk warning; perform a separate, human-led GloBE analysis.' : 'The available data is insufficient for a complete screening result. Complete and re-approve the source data.'}</p></div>
  </section>
}
