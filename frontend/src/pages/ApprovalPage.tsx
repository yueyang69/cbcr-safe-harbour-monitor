import { useCallback, useEffect, useState } from 'react'
import { approveFinancialData, batchApproveFinancialData, deleteFinancialData, listCompanies, listFinancialData, returnFinancialData } from '../api/endpoints'
import { useSession } from '../session'
import type { Company, FinancialData } from '../types'

const formatMoney = (value: string | number | null) => value === null ? '—' : new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(Number(value))

export function ApprovalPage() {
  const [rows, setRows] = useState<FinancialData[]>([])
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busyId, setBusyId] = useState('')
  const [returnTarget, setReturnTarget] = useState<FinancialData | null>(null)
  const [returnReason, setReturnReason] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<FinancialData | null>(null)

  const { role: userRole } = useSession()
  const isAdmin = userRole === 'admin'

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

  const approveAll = async () => {
    setBusyId('__all__')
    setError('')
    setNotice('')
    try {
      const result = await batchApproveFinancialData()
      setNotice(result.approved_count > 0
        ? `已批量通过 ${result.approved_count} 条数据，Dashboard 已刷新。`
        : '当前没有待审批的数据。')
      await load()
    } catch (err) {
      setError(`Batch approve failed: ${err instanceof Error ? err.message : 'unknown error'}`)
    } finally {
      setBusyId('')
    }
  }

  const confirmReturn = async () => {
    if (!returnTarget) return
    const id = returnTarget.id
    setBusyId(id)
    setError('')
    try {
      await returnFinancialData(id, returnReason.trim() || undefined)
      await load()
    } catch (err) {
      setError(`Return failed: ${err instanceof Error ? err.message : 'unknown error'}`)
    } finally {
      setBusyId('')
      setReturnTarget(null)
      setReturnReason('')
    }
  }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    const id = deleteTarget.id
    setBusyId(id)
    setError('')
    try {
      await deleteFinancialData(id)
      await load()
    } catch (err) {
      setError(`Delete failed: ${err instanceof Error ? err.message : 'unknown error'}`)
    } finally {
      setBusyId('')
      setDeleteTarget(null)
    }
  }

  const statusLabel = (row: FinancialData) => row.is_approved ? 'Approved' : row.is_submitted ? 'Pending review' : 'Draft'

  return <section className="page-wrap">
    <div className="page-heading"><div><p className="eyebrow">HQ review queue</p><h1>Approvals</h1><p className="heading-copy">Submitted data awaiting review. Approve to publish to the Dashboard, or return for corrections.</p></div><div className="heading-actions"><button className="button button-primary" onClick={() => void approveAll()} disabled={pending.length === 0 || busyId !== ''}>{busyId === '__all__' ? '正在批量通过...' : '✅ 全部通过'}</button><button className="button button-secondary" onClick={() => void load()}>↻ Refresh</button></div></div>
    {error && <div className="alert alert-error" role="alert">{error}</div>}{notice && <div className="alert alert-success" role="status">{notice}</div>}
    <div className="section-heading"><div><h2>Pending approval</h2><p>{loading ? 'Loading queue…' : `${pending.length} submitted, awaiting review`}</p></div></div>
    <div className="table-frame">{loading ? <div className="empty-state">Loading approval queue…</div> : pending.length === 0 ? <div className="empty-state"><strong>No submissions awaiting review</strong><span>Subsidiary data appears here after it is submitted for approval.</span></div> : <div className="table-scroll"><table><thead><tr><th>Company</th><th>Jurisdiction</th><th>FY</th><th>Revenue</th><th>PBT</th><th>Covered taxes</th><th>Payroll</th><th>Tangible assets</th><th>Actions</th></tr></thead><tbody>{pending.map((row) => <tr key={row.id}><td>{companyName(row.company_id)}</td><td>{row.jurisdiction}</td><td>{row.fiscal_year}</td><td>{formatMoney(row.revenue)}</td><td>{formatMoney(row.pbt)}</td><td>{formatMoney(row.covered_taxes)}</td><td>{formatMoney(row.payroll)}</td><td>{formatMoney(row.tangible_assets)}</td><td><div className="row-actions"><button className="button button-primary" onClick={() => void act(row.id, approveFinancialData, 'Approve')} disabled={busyId === row.id}>Approve</button><button className="button button-secondary" onClick={() => { setReturnTarget(row); setReturnReason('') }} disabled={busyId === row.id}>Return</button>{isAdmin && <button className="button button-danger" onClick={() => setDeleteTarget(row)} disabled={busyId === row.id}>Delete</button>}</div></td></tr>)}</tbody></table></div>}</div>
    <p className="disclaimer">Approving a jurisdiction publishes it to the Dashboard — safe harbour tests re-run automatically on approval.</p>

    {isAdmin && <div className="section-heading admin-records-heading"><div><h2>All records</h2><p>{loading ? 'Loading…' : `${rows.length} records across all entities`}</p></div></div>}
    {isAdmin && <div className="table-frame">{loading ? <div className="empty-state">Loading…</div> : rows.length === 0 ? <div className="empty-state"><strong>No records yet</strong><span>Data entered via Data entry appears here.</span></div> : <div className="table-scroll"><table><thead><tr><th>Company</th><th>Jurisdiction</th><th>FY</th><th>Status</th><th>Return reason</th><th>Actions</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{companyName(row.company_id)}</td><td>{row.jurisdiction}</td><td>{row.fiscal_year}</td><td>{statusLabel(row)}</td><td>{row.return_reason || '—'}</td><td><div className="row-actions"><button className="button button-danger" onClick={() => setDeleteTarget(row)} disabled={busyId === row.id}>Delete</button></div></td></tr>)}</tbody></table></div>}</div>}

    {returnTarget && <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Return submission"><div className="modal"><h3>Return {companyName(returnTarget.company_id)} / {returnTarget.jurisdiction} ({returnTarget.fiscal_year})</h3><p className="modal-copy">The reporting subsidiary will see this reason and can resubmit after correcting the values.</p><textarea className="modal-textarea" value={returnReason} onChange={(event) => setReturnReason(event.target.value)} placeholder="Reason for returning (optional)" rows={3} maxLength={500} /><div className="modal-actions"><button className="button button-secondary" onClick={() => { setReturnTarget(null); setReturnReason('') }} disabled={busyId === returnTarget.id}>Cancel</button><button className="button button-danger" onClick={() => void confirmReturn()} disabled={busyId === returnTarget.id}>{busyId === returnTarget.id ? 'Returning…' : 'Return submission'}</button></div></div></div>}

    {deleteTarget && <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Delete submission"><div className="modal"><h3>Delete {companyName(deleteTarget.company_id)} / {deleteTarget.jurisdiction} ({deleteTarget.fiscal_year})?</h3><p className="modal-copy">Deletion is permanent and removes the jurisdiction from the Dashboard — the summary cache is rebuilt immediately.</p><div className="modal-actions"><button className="button button-secondary" onClick={() => setDeleteTarget(null)} disabled={busyId === deleteTarget.id}>Cancel</button><button className="button button-danger" onClick={() => void confirmDelete()} disabled={busyId === deleteTarget.id}>{busyId === deleteTarget.id ? 'Deleting…' : 'Delete permanently'}</button></div></div></div>}
  </section>
}
