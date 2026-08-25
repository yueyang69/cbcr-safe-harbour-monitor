import { FormEvent, useEffect, useState } from 'react'
import { confirmMapping, createFinancialData, detectAnomalies, listCompanies, suggestMapping } from '../api/endpoints'
import type { AnomalyFlag, Company, FinancialDataInput, MappingSuggestion } from '../types'

const fields = ['jurisdiction', 'fiscal_year', 'currency', 'revenue', 'pbt', 'covered_taxes', 'payroll', 'tangible_assets'] as const
const labels: Record<typeof fields[number], string> = { jurisdiction: 'Jurisdiction', fiscal_year: 'Fiscal year', currency: 'Currency', revenue: 'Revenue', pbt: 'Profit before tax', covered_taxes: 'Covered taxes', payroll: 'Eligible payroll', tangible_assets: 'Eligible tangible assets' }
const sampleSourceFields = ['所在国家/地区', '报告期', '本位币', '全年营业收入', '税前利润', '已涵盖所得税', '合格员工薪酬', '合格有形资产']

export function DataEntryPage() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [mappings, setMappings] = useState<MappingSuggestion[]>([])
  const [message, setMessage] = useState(‘’)
  const [error, setError] = useState(‘’)
  const [form, setForm] = useState<FinancialDataInput>({ company_id: ‘’, fiscal_year: 2025, jurisdiction: ‘’, currency: ‘EUR’, revenue: null, pbt: null, covered_taxes: null, payroll: null, tangible_assets: null })
  const [anomalies, setAnomalies] = useState<AnomalyFlag[]>([])
  const [detectingAnomalies, setDetectingAnomalies] = useState(false)

  useEffect(() => { listCompanies().then((items) => { setCompanies(items); if (items[0]) setForm((current) => ({ ...current, company_id: items[0].id })) }).catch((err: Error) => setError(err.message)) }, [])
  const update = (key: keyof FinancialDataInput, value: string) => setForm((current) => ({ ...current, [key]: [‘revenue’, ‘pbt’, ‘covered_taxes’, ‘payroll’, ‘tangible_assets’].includes(key) ? (value === ‘’ ? null : Number(value)) : key === ‘fiscal_year’ ? Number(value) : value }))
  const startMapping = async () => { setError(‘’); setMessage(‘’); try { setMappings(await suggestMapping(sampleSourceFields)); } catch (err) { setError(err instanceof Error ? err.message : ‘Could not suggest mappings.’) } }
  const saveMapping = async () => { try { await confirmMapping(mappings); setMessage(‘Mapping confirmed. Continue with the source data below.’); } catch (err) { setError(err instanceof Error ? err.message : ‘Could not confirm mapping.’) } }

  const runAnomalyDetection = async () => {
    if (!form.company_id || !form.jurisdiction) {
      setError(‘Please select a company and enter jurisdiction before running anomaly detection.’)
      return
    }

    setDetectingAnomalies(true)
    setError(‘’)
    setAnomalies([])

    try {
      const result = await detectAnomalies(form)
      setAnomalies(result.anomalies)
      if (result.anomalies.length === 0) {
        setMessage(‘✓ AI检测完成：未发现异常’)
      } else {
        setMessage(`⚠️ AI检测完成：发现 ${result.anomalies.length} 个潜在问题`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : ‘AI anomaly detection failed’)
    } finally {
      setDetectingAnomalies(false)
    }
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError(‘’)
    setMessage(‘’)

    // Run anomaly detection before saving
    if (anomalies.length === 0 && !detectingAnomalies) {
      await runAnomalyDetection()
    }

    try {
      const created = await createFinancialData(form)
      setMessage(`Saved ${created.jurisdiction} data. Submit it for HQ approval after your review.`)
    } catch (err) {
      setError(err instanceof Error ? err.message : ‘Could not save financial data.’)
    }
  }

  const userRole = localStorage.getItem(‘user_role’) || ‘subsidiary’
  const isHQ = userRole === ‘hq’ || userRole === ‘admin’

  return <section className="page-wrap entry-page"><div className="page-heading"><div><p className="eyebrow">Subsidiary workspace</p><h1>Prepare source data</h1><p className="heading-copy">{isHQ ? ‘As HQ user, you can configure field mappings and enter data.’ : ‘Submit jurisdiction data for HQ review.’}</p></div></div>
    {error && <div className="alert alert-error" role="alert">{error}</div>}{message && <div className="alert alert-success" role="status">{message}</div>}
    <div className="workflow-grid">{isHQ && <article className="workflow-step"><div className="step-number">01</div><div><h2>Confirm field mapping</h2><p>AI suggestions are based on source field names. Review each target before confirming.</p></div><button className="button button-secondary" onClick={() => void startMapping()}>Suggest mappings</button>{mappings.length > 0 && <div className="mapping-list">{mappings.map((mapping, index) => <label key={`${mapping.source_field}-${index}`} className="mapping-row"><span>{mapping.source_field}</span><span aria-hidden="true">→</span><select value={mapping.target_field} onChange={(event) => setMappings((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, target_field: event.target.value } : item))}>{fields.map((field) => <option key={field} value={field}>{labels[field]}</option>)}</select><small>{Math.round(Number(mapping.confidence) * 100)}% confidence</small></label>)}<button className="button button-primary" onClick={() => void saveMapping()}>Confirm mapping</button></div>}</article>}
      <article className="workflow-step"><div className="step-number">{isHQ ? ‘02’ : ‘01’}</div><div><h2>Enter financial data</h2><p>Values are stored as source data. The Safe Harbour engine runs on the server after HQ approval.</p></div><form className="data-form" onSubmit={submit}><label>Company<select required value={form.company_id} onChange={(event) => update(‘company_id’, event.target.value)}><option value="">Select company</option>{companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}</select></label><div className="form-grid">{fields.filter((field) => field !== ‘fiscal_year’ && field !== ‘currency’).map((field) => <label key={field}>{labels[field]}<input required={field === ‘jurisdiction’} type={field === ‘jurisdiction’ ? ‘text’ : ‘number’} min={field !== ‘jurisdiction’ && field !== ‘pbt’ ? 0 : undefined} step={field === ‘jurisdiction’ ? undefined : ‘0.01’} value={form[field] ?? ‘’} onChange={(event) => update(field, event.target.value)} placeholder={field === ‘jurisdiction’ ? ‘e.g. Japan’ : ‘0.00’} /></label>)}</div><div className="form-grid compact-grid"><label>Fiscal year<select value={form.fiscal_year} onChange={(event) => update(‘fiscal_year’, event.target.value)}><option value="2024">2024</option><option value="2025">2025</option><option value="2026">2026</option><option value="2027">2027</option><option value="2028">2028</option></select></label><label>Currency<input value={form.currency} readOnly disabled title="Currency is fixed to EUR for MVP" style={{ background: ‘#f5f7fa’, cursor: ‘not-allowed’ }} /></label></div>
        <div className="ai-detection-section">
          <button type="button" className="button button-secondary" onClick={() => void runAnomalyDetection()} disabled={detectingAnomalies || !form.company_id}>
            {detectingAnomalies ? ‘🤖 AI 正在扫描数据异常...’ : ‘🤖 运行 AI 异常检测’}
          </button>
          {anomalies.length > 0 && (
            <div className="anomaly-list">
              <h4>⚠️ AI 检测到以下潜在问题：</h4>
              {anomalies.map((anomaly, idx) => (
                <div key={idx} className={`anomaly-item anomaly-${anomaly.severity}`}>
                  <span className="anomaly-icon">{anomaly.severity === ‘error’ ? ‘❌’ : ‘⚠️’}</span>
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
        <button className="button button-primary" type="submit" disabled={!form.company_id}>Save source data</button></form></article></div>
  </section>
}
