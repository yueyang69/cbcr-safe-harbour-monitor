import { useCallback, useEffect, useState } from 'react'
import { approveFinancialData, listCompanies, listFinancialData, returnFinancialData } from '../api/endpoints'
import type { Company, FinancialData } from '../types'

const formatMoney = (value: string | number | null) => value === null ? '—' : new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(Number(value))

export function ApprovalPage() {
  const [rows, setRows] = useState<FinancialData[]>([])
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [dataRows, companyRows] = await Promise.all([listFinancialData(), listCompanies()])
      setRows(dataRows)
      setCompanies(companyRows)
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load the approval queue.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const companyName = (id: string) => companies.find((company) => company.id === id)?.name ?? id.slice(0, 8)
  const pending = rows.filter((row) => row.is_submitted && !row.is_approved)

  const act = async (id: string, fn: (dataId: string) => Promise<unknown>, verb: string) => {
    setBusyId(id)
    setError('')
    try {
      await fn(id)
      await load()
    } catch (err) {
      setError(`${verb} failed: ${err instanceof Error ? err.message : 'unknown error'}`)
    } finally {
      setBusyId('')
    }
  }

  return <section className="page-wrap">
    <div className="page-heading"><div><p className="eyebrow">HQ review queue</p><h1>Approvals</h1><p className="heading-copy">Submitted data awaiting review. Approve to publish to the Dashboard, or return for corrections.</p></div><div className="heading-actions"><button className="button button-secondary" onClick={() => void load()}>↻ Refresh</button></div></div>
    {error && <div className="alert alert-error" role="alert">{error}</div>}
    <div className="section-heading"><div><h2>Pending approval</h2><p>{loading ? 'Loading queue…' : `${pending.length} submitted, awaiting review`}</p></div></div>
    <div className="table-frame">{loading ? <div className="empty-state">Loading approval queue…</div> : pending.length === 0 ? <div className="empty-state"><strong>No submissions awaiting review</strong><span>Subsidiary data appears here after it is submitted for approval.</span></div> : <div className="table-scroll"><table><thead><tr><th>Company</th><th>Jurisdiction</th><th>FY</th><th>Revenue</th><th>PBT</th><th>Covered taxes</th><th>Payroll</th><th>Tangible assets</th><th>Actions</th></tr></thead><tbody>{pending.map((row) => <tr key={row.id}><td>{companyName(row.company_id)}</td><td>{row.jurisdiction}</td><td>{row.fiscal_year}</td><td>{formatMoney(row.revenue)}</td><td>{formatMoney(row.pbt)}</td><td>{formatMoney(row.covered_taxes)}</td><td>{formatMoney(row.payroll)}</td><td>{formatMoney(row.tangible_assets)}</td><td><div className="row-actions"><button className="button button-primary" onClick={() => void act(row.id, approveFinancialData, 'Approve')} disabled={busyId === row.id}>Approve</button><button className="button button-secondary" onClick={() => void act(row.id, returnFinancialData, 'Return')} disabled={busyId === row.id}>Return</button></div></td></tr>)}</tbody></table></div>}</div>
    <p className="disclaimer">Approving a jurisdiction publishes it to the Dashboard — safe harbour tests re-run automatically on approval.</p>
  </section>
}
