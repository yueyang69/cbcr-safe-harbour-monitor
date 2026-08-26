import { FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { batchSubmitFinancialData, confirmMapping, createFinancialData, detectAnomalies, listCompanies, listFinancialData, quickSubmitFinancialData, submitFinancialData, suggestMapping, updateFinancialData } from '../api/endpoints'
import type { AnomalyFlag, Company, FinancialData, FinancialDataInput, MappingSuggestion, UserRole } from '../types'

const fields = ['jurisdiction', 'fiscal_year', 'currency', 'revenue', 'pbt', 'covered_taxes', 'payroll', 'tangible_assets'] as const
const labels: Record<typeof fields[number], string> = { jurisdiction: 'Jurisdiction', fiscal_year: 'Fiscal year', currency: 'Currency', revenue: 'Revenue', pbt: 'Profit before tax', covered_taxes: 'Covered taxes', payroll: 'Eligible payroll', tangible_assets: 'Eligible tangible assets' }
const sampleSourceFields = ['所在国家/地区', '报告期', '本位币', '全年营业收入', '税前利润', '已涵盖所得税', '合格员工薪酬', '合格有形资产']

export function DataEntryPage() {
  const navigate = useNavigate()
  const [companies, setCompanies] = useState<Company[]>([])
  const [mappings, setMappings] = useState<MappingSuggestion[]>([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [form, setForm] = useState<FinancialDataInput>({ company_id: '', fiscal_year: 2025, jurisdiction: '', currency: 'EUR', revenue: null, pbt: null, covered_taxes: null, payroll: null, tangible_assets: null })
  const [anomalies, setAnomalies] = useState<AnomalyFlag[]>([])
  const [detectingAnomalies, setDetectingAnomalies] = useState(false)
  const [savedDraftId, setSavedDraftId] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)
  const [draftCount, setDraftCount] = useState(0)
  const [submittingAll, setSubmittingAll] = useState(false)

  const userRole = (localStorage.getItem('cbcr-role') || 'hq') as UserRole
  const isSubsidiary = userRole === 'subsidiary'
  const isApprover = userRole === 'hq' || userRole === 'admin'
  const entityId = localStorage.getItem('cbcr-entity')
  const showMappingStep = userRole !== 'reviewer'

  useEffect(() => {
    setError('')
    setSavedDraftId(null)
    setSubmitted(false)
    if (isSubsidiary && !entityId) {
      // Strict GET /companies returns 400 without X-Entity-Id — skip the fetch.
      setCompanies([])
      setForm((current) => ({ ...current, company_id: '' }))
      setError('Select an entity in the top-right before entering data.')
      return
    }
    listCompanies().then((items) => {
      setCompanies(items)
      const target = isSubsidiary && entityId ? items.find((item) => item.id === entityId) : items[0]
      if (target) setForm((current) => ({ ...current, company_id: target.id }))
    }).catch((err: Error) => setError(err.message))
    if (isSubsidiary && entityId) {
      // Resume the strict flow: restore this entity's first unsubmitted draft
      // (editable). `submitted` tracks ONLY the loaded draft — a sibling row
      // already pending approval must not lock the page (that deadlocked the
      // whole batch after the first row was submitted).
      listFinancialData().then((rows) => {
        const drafts = rows.filter((row) => !row.is_submitted && !row.is_approved)
        const draft = drafts[0]
        if (draft) {
          setDraftCount(drafts.filter((row) => row.company_id === draft.company_id && row.fiscal_year === draft.fiscal_year).length)
          fillFormFromDraft(draft)
        } else {
          setDraftCount(0)
        }
      }).catch(() => undefined)
    }
  }, [isSubsidiary, entityId])

  const update = (key: keyof FinancialDataInput, value: string) => setForm((current) => ({ ...current, [key]: ['revenue', 'pbt', 'covered_taxes', 'payroll', 'tangible_assets'].includes(key) ? (value === '' ? null : Number(value)) : key === 'fiscal_year' ? Number(value) : value }))
  const startMapping = async () => { setError(''); setMessage(''); try { setMappings(await suggestMapping(sampleSourceFields)); } catch (err) { setError(err instanceof Error ? err.message : 'Could not suggest mappings.') } }
  const saveMapping = async () => { try { await confirmMapping(mappings); setMessage('Mapping confirmed. Continue with the source data below.'); } catch (err) { setError(err instanceof Error ? err.message : 'Could not confirm mapping.') } }

  const runAnomalyDetection = async () => {
    if (!form.company_id || !form.jurisdiction) {
      setError('Please select a company and enter jurisdiction before running anomaly detection.')
      return
    }

    setDetectingAnomalies(true)
    setError('')
    setAnomalies([])

    try {
      const result = await detectAnomalies(form)
      setAnomalies(result.anomalies)
      if (result.anomalies.length === 0) {
        setMessage('✓ AI检测完成：未发现异常')
      } else {
        setMessage(`⚠️ AI检测完成：发现 ${result.anomalies.length} 个潜在问题`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'AI anomaly detection failed')
    } finally {
      setDetectingAnomalies(false)
    }
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setMessage('')

    // Run anomaly detection before saving
    if (anomalies.length === 0 && !detectingAnomalies) {
      await runAnomalyDetection()
    }

    try {
      if (isApprover) {
        // MVP Scenario 1: HQ enters + approves in one step; the backend rebuilds
        // summaries so the jurisdiction appears on the Dashboard immediately.
        await quickSubmitFinancialData(form)
        setMessage('Saved, approved and published. Opening the dashboard…')
        navigate('/dashboard')
      } else if (savedDraftId) {
        // Strict flow: a draft already exists for this entity/year — update it
        // (backend PUT) instead of creating a duplicate (which would 409).
        await updateFinancialData(savedDraftId, form)
        setMessage('Draft updated. Review the values, then submit for HQ approval.')
      } else {
        const created = await createFinancialData(form)
        setSavedDraftId(created.id)
        setMessage(`Saved ${created.jurisdiction} data as a draft. Review, then submit for HQ approval.`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save financial data.')
    }
  }

  const fillFormFromDraft = (draft: FinancialData) => {
    setSavedDraftId(draft.id)
    setSubmitted(false)
    setForm({
      company_id: draft.company_id, fiscal_year: draft.fiscal_year, jurisdiction: draft.jurisdiction, currency: draft.currency,
      revenue: draft.revenue === null ? null : Number(draft.revenue),
      pbt: draft.pbt === null ? null : Number(draft.pbt),
      covered_taxes: draft.covered_taxes === null ? null : Number(draft.covered_taxes),
      payroll: draft.payroll === null ? null : Number(draft.payroll),
      tangible_assets: draft.tangible_assets === null ? null : Number(draft.tangible_assets),
    })
  }

  const submitForApproval = async () => {
    if (!savedDraftId) return
    setError('')
    setMessage('')
    try {
      await submitFinancialData(savedDraftId)
      setSubmitted(true)
      setMessage('Submitted for HQ approval. It appears on the Dashboard once approved.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit for approval.')
    }
  }

  // Stage 3: one click moves the whole CSV import (all unsubmitted drafts for
  // this company + fiscal year) into HQ's approval queue.
  const submitAllDrafts = async () => {
    if (!form.company_id) return
    setSubmittingAll(true)
    setError('')
    setMessage('')
    try {
      const result = await batchSubmitFinancialData(form.company_id, form.fiscal_year)
      // Refresh the draft list so the batch button and the form reflect what's left.
      const rows = await listFinancialData()
      const drafts = rows.filter((row) => !row.is_submitted && !row.is_approved && row.company_id === form.company_id && row.fiscal_year === form.fiscal_year)
      setDraftCount(drafts.length)
      const draft = drafts[0]
      if (draft) {
        fillFormFromDraft(draft)
      } else {
        setSavedDraftId(null)
        setSubmitted(true)
      }
      setMessage(result.submitted_count > 0
        ? `已提交 ${result.submitted_count} 条数据，等待 HQ 审批。`
        : '没有待提交的草稿。')
    } catch (err) {
      setError(err instanceof Error ? err.message : '批量提交失败。')
    } finally {
      setSubmittingAll(false)
    }
  }

  return <section className="page-wrap entry-page"><div className="page-heading"><div><p className="eyebrow">Source data workspace</p><h1>Prepare source data</h1><p className="heading-copy">Confirm the suggested field mapping, then submit this entity's jurisdiction data for HQ review.</p></div></div>
    {error && <div className="alert alert-error" role="alert">{error}</div>}{message && <div className="alert alert-success" role="status">{message}</div>}
    <div className="workflow-grid">{showMappingStep && <article className="workflow-step"><div className="step-number">01</div><div><h2>Confirm field mapping</h2><p>AI suggestions are based on source field names. Review each target before confirming.</p></div><button className="button button-secondary" onClick={() => void startMapping()}>Suggest mappings</button>{mappings.length > 0 && <div className="mapping-list">{mappings.map((mapping, index) => <label key={`${mapping.source_field}-${index}`} className="mapping-row"><span>{mapping.source_field}</span><span aria-hidden="true">→</span><select value={mapping.target_field} onChange={(event) => setMappings((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, target_field: event.target.value } : item))}>{fields.map((field) => <option key={field} value={field}>{labels[field]}</option>)}</select><small>{Math.round(Number(mapping.confidence) * 100)}% confidence</small></label>)}<button className="button button-primary" onClick={() => void saveMapping()}>Confirm mapping</button></div>}</article>}
      <article className="workflow-step"><div className="step-number">{showMappingStep ? '02' : '01'}</div><div><h2>Enter financial data</h2><p>Values are stored as source data. The Safe Harbour engine runs on the server after HQ approval.</p></div><form className="data-form" onSubmit={submit}><label>Company<select required value={form.company_id} onChange={(event) => update('company_id', event.target.value)} disabled={isSubsidiary} title={isSubsidiary ? 'Your entity is bound to the account' : undefined}><option value="">Select company</option>{companies.filter((company) => !isSubsidiary || company.id === entityId).map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}</select></label><div className="form-grid">{fields.filter((field) => field !== 'fiscal_year' && field !== 'currency').map((field) => <label key={field}>{labels[field]}<input required={field === 'jurisdiction'} type={field === 'jurisdiction' ? 'text' : 'number'} min={field !== 'jurisdiction' && field !== 'pbt' ? 0 : undefined} step={field === 'jurisdiction' ? undefined : '0.01'} value={form[field] ?? ''} onChange={(event) => update(field, event.target.value)} placeholder={field === 'jurisdiction' ? 'e.g. Japan' : '0.00'} /></label>)}</div><div className="form-grid compact-grid"><label>Fiscal year<select value={form.fiscal_year} onChange={(event) => update('fiscal_year', event.target.value)}><option value="2024">2024</option><option value="2025">2025</option><option value="2026">2026</option><option value="2027">2027</option><option value="2028">2028</option></select></label><label>Currency<input value={form.currency} readOnly disabled title="Currency is fixed to EUR for MVP" style={{ background: '#f5f7fa', cursor: 'not-allowed' }} /></label></div>
        <div className="ai-detection-section">
          <button type="button" className="button button-secondary" onClick={() => void runAnomalyDetection()} disabled={detectingAnomalies || !form.company_id}>
            {detectingAnomalies ? '🤖 AI 正在扫描数据异常...' : '🤖 运行 AI 异常检测'}
          </button>
          {anomalies.length > 0 && (
            <div className="anomaly-list">
              <h4>⚠️ AI 检测到以下潜在问题：</h4>
              {anomalies.map((anomaly, idx) => (
                <div key={idx} className={`anomaly-item anomaly-${anomaly.severity}`}>
                  <span className="anomaly-icon">{anomaly.severity === 'error' ? '❌' : '⚠️'}</span>
                  <div>
                    <strong>{anomaly.field}</strong>
                    <p>{anomaly.message}</p>
                  </div>
                </div>
              ))}
              <p className="anomaly-disclaimer">注：AI仅预警，不会自动修改数值。请人工确认后再保存。</p>
            </div>
          )}
        </div>
        {isSubsidiary && submitted && <div className="alert alert-info" role="status">Submitted and awaiting HQ approval. HQ can return it if corrections are needed.</div>}
        {isSubsidiary && draftCount > 0 && (
          <div className="form-actions">
            <button type="button" className="button button-primary" onClick={() => void submitAllDrafts()} disabled={submittingAll} title={`提交本财年全部 ${draftCount} 条草稿到 HQ 审批队列`}>
              {submittingAll ? '正在提交全部草稿...' : `📤 提交全部 ${draftCount} 条草稿（FY ${form.fiscal_year}）`}
            </button>
          </div>
        )}
        <div className="form-actions"><button className="button button-primary" type="submit" disabled={!form.company_id || submitted}>{isApprover ? 'Save & publish to dashboard' : savedDraftId ? 'Update draft' : 'Save source data'}</button>{isSubsidiary && savedDraftId && !submitted && <button type="button" className="button button-secondary" onClick={() => void submitForApproval()}>Submit for approval</button>}</div></form></article></div>
  </section>
}
