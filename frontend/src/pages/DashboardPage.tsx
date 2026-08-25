import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getDashboard, rebuildSummaries } from '../api/endpoints'
import { StatusBadge } from '../components/StatusBadge'
import { AIBriefingCard } from '../components/AIBriefingCard'
import type { DashboardData, DashboardJurisdiction, ResultStatus } from '../types'

const formatMoney = (value: string | number | null) => value === null ? '—' : new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(Number(value))
const testShort: Record<string, string> = { de_minimis: 'De minimis', simplified_etr: 'ETR', routine_profits: 'Routine profits' }

function Metric({ label, value, note, tone }: { label: string; value: number; note: string; tone: string }) {
  return <article className={`metric-card ${tone}`}><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-note">{note}</div></article>
}
function TableStatus({ status }: { status: ResultStatus }) { return <StatusBadge status={status} compact /> }
function JurisdictionRow({ row }: { row: DashboardJurisdiction }) {
  const tests = row.evaluation?.tests
  return <tr><td><Link className="jurisdiction-link" to={`/summaries/${row.id}`}>{row.jurisdiction}<span aria-hidden="true">↗</span></Link><small>{row.evaluation?.warning ? 'Review required' : 'All submitted data'}</small></td><td>{formatMoney(row.revenue)}</td><td>{formatMoney(row.pbt)}</td><td>{tests?.simplified_etr?.value == null ? '—' : `${(Number(tests.simplified_etr.value) * 100).toFixed(1)}%`}</td><td>{formatMoney(tests?.routine_profits?.value ?? null)}</td>{(['de_minimis', 'simplified_etr', 'routine_profits'] as const).map((key) => <td key={key}><TableStatus status={tests?.[key]?.result || 'INCOMPLETE'} /></td>)}<td><TableStatus status={row.status} /></td></tr>
}

export function DashboardPage() {
  const [year, setYear] = useState(2025)
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const rows = useMemo(() => data?.jurisdictions || [], [data])
  const load = async () => { setLoading(true); setError(''); try { setData(await getDashboard(year)) } catch (err) { setError(err instanceof Error ? err.message : 'Unable to load dashboard.') } finally { setLoading(false) } }
  useEffect(() => { void load() }, [year])
  const refresh = async () => { setRefreshing(true); setError(''); try { await rebuildSummaries(year); await load() } catch (err) { setError(err instanceof Error ? err.message : 'Unable to rebuild summaries.') } finally { setRefreshing(false) } }

  return <section className="page-wrap"><div className="page-heading"><div><p className="eyebrow">Group overview / FY {year}</p><h1>Safe Harbour monitor</h1><p className="heading-copy">Review jurisdiction-level eligibility signals before moving to detailed GloBE analysis.</p></div><div className="heading-actions"><label className="year-control">Fiscal year<select value={year} onChange={(event) => setYear(Number(event.target.value))}><option value="2024">2024</option><option value="2025">2025</option><option value="2026">2026</option></select></label><button className="button button-primary" onClick={() => void refresh()} disabled={refreshing}>{refreshing ? 'Refreshing…' : '↻ Refresh summaries'}</button></div></div>
    {error && <div className="alert alert-error" role="alert"><strong>Dashboard unavailable.</strong> {error}<button onClick={() => void load()}>Try again</button></div>}
    <AIBriefingCard fiscalYear={year} />
    <div className="metric-grid"><Metric label="Jurisdictions" value={data?.kpis.jurisdiction_count ?? 0} note="In current reporting year" tone="metric-neutral" /><Metric label="Pass" value={data?.kpis.pass_count ?? 0} note="At least one test passed" tone="metric-good" /><Metric label="Risk warnings" value={data?.kpis.warning_count ?? 0} note="All three tests failed" tone="metric-risk" /><Metric label="Incomplete" value={data?.kpis.incomplete_count ?? 0} note="Requires data follow-up" tone="metric-muted" /></div>
    <div className="section-heading"><div><h2>Jurisdiction results</h2><p>{loading ? 'Loading server evaluation…' : `${rows.length} jurisdictions · select a row to inspect the rationale`}</p></div><div className="legend" aria-label="Result legend"><StatusBadge status="PASS" compact /><StatusBadge status="WARNING" compact /><StatusBadge status="INCOMPLETE" compact /></div></div>
    <div className="table-frame">{loading ? <div className="empty-state">Loading jurisdiction results…</div> : rows.length === 0 ? <div className="empty-state"><strong>No approved data for FY {year}</strong><span>Submit and approve financial data, then refresh summaries.</span><Link className="button button-secondary" to="/data-entry">Open data entry</Link></div> : <div className="table-scroll"><table><caption className="sr-only">Safe Harbour tests by jurisdiction for fiscal year {year}</caption><thead><tr><th>Jurisdiction</th><th>Revenue</th><th>PBT</th><th>ETR</th><th>SBIE</th>{Object.values(testShort).map((label) => <th key={label}>{label}</th>)}<th>Final result</th></tr></thead><tbody>{rows.map((row) => <JurisdictionRow key={row.id} row={row} />)}</tbody></table></div>}</div>
    <p className="disclaimer">This workspace generates risk warnings only. It does not calculate GloBE Top-up Tax.</p>
  </section>
}
