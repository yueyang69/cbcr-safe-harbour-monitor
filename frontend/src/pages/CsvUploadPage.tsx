import { DragEvent, FormEvent, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { batchCommitCsv, batchUploadCsv, listCompanies } from '../api/endpoints'
import type { BatchCommitResult, BatchRowInput, BatchUploadResult, ColumnMappingInfo, Company, UserRole } from '../types'

const STANDARD_FIELDS = ['jurisdiction', 'fiscal_year', 'currency', 'revenue', 'pbt', 'covered_taxes', 'payroll', 'tangible_assets'] as const
const FIELD_LABELS: Record<string, string> = {
  jurisdiction: 'Jurisdiction', fiscal_year: 'Fiscal year', currency: 'Currency',
  revenue: 'Revenue', pbt: 'Profit before tax', covered_taxes: 'Covered taxes',
  payroll: 'Eligible payroll', tangible_assets: 'Eligible tangible assets',
}
type NumericField = 'revenue' | 'pbt' | 'covered_taxes' | 'payroll' | 'tangible_assets'
const NUMERIC_FIELDS: readonly NumericField[] = ['revenue', 'pbt', 'covered_taxes', 'payroll', 'tangible_assets']
const isNumericField = (field: string): field is NumericField => (NUMERIC_FIELDS as readonly string[]).includes(field)
const IGNORE_VALUE = '__ignore__'
const MANUAL_THRESHOLD = 0.6

export function CsvUploadPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [companies, setCompanies] = useState<Company[]>([])
  const [companyId, setCompanyId] = useState('')
  const [fiscalYear, setFiscalYear] = useState(2026)
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [committing, setCommitting] = useState(false)
  const [uploadResult, setUploadResult] = useState<BatchUploadResult | null>(null)
  const [mappings, setMappings] = useState<ColumnMappingInfo[]>([])
  const [commitResult, setCommitResult] = useState<BatchCommitResult | null>(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [parseErrors, setParseErrors] = useState<string[]>([])

  const userRole = (localStorage.getItem('cbcr-role') || 'hq') as UserRole
  const isSubsidiary = userRole === 'subsidiary'
  const entityId = localStorage.getItem('cbcr-entity')

  useEffect(() => {
    if (isSubsidiary && !entityId) {
      setError('请在右上角先选择实体（Select an entity）再上传 CSV。')
      return
    }
    listCompanies().then((items) => {
      setCompanies(items)
      const target = isSubsidiary && entityId ? items.find((item) => item.id === entityId) : items[0]
      if (target) setCompanyId(target.id)
    }).catch((err: Error) => setError(err.message))
  }, [isSubsidiary, entityId])

  const onFileChosen = (selected: File | null) => {
    if (!selected) return
    if (!/\.csv$/i.test(selected.name) && selected.type !== 'text/csv') {
      setError('仅支持 CSV 文件。')
      return
    }
    setError('')
    setUploadResult(null)
    setCommitResult(null)
    setMessage('')
    setFile(selected)
  }

  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    setDragging(false)
    onFileChosen(event.dataTransfer.files?.[0] ?? null)
  }

  const runUpload = async (event: FormEvent) => {
    event.preventDefault()
    if (!file || !companyId) {
      setError('请先选择文件和公司。')
      return
    }
    setUploading(true)
    setError('')
    setMessage('')
    try {
      const result = await batchUploadCsv(file, companyId, fiscalYear)
      setUploadResult(result)
      setMappings(result.columns)
      const unmapped = result.columns.filter((col) => !col.mapped_field).length
      setMessage(`解析成功：共 ${result.total_rows} 行数据，${result.columns.length} 列。${unmapped > 0 ? `有 ${unmapped} 列需要人工选择。` : '全部列已自动映射。'}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'CSV 解析失败。')
    } finally {
      setUploading(false)
    }
  }

  const updateMapping = (index: number, value: string) => {
    setMappings((current) => current.map((col, i) =>
      i === index ? { ...col, mapped_field: value === IGNORE_VALUE ? null : value } : col,
    ))
  }

  const buildRows = (): { rows: BatchRowInput[]; errors: string[] } => {
    if (!uploadResult) return { rows: [], errors: [] }
    const errors: string[] = []
    const rows = uploadResult.rows.map((raw, rowIndex) => {
      const row: BatchRowInput = { jurisdiction: '', currency: 'EUR', revenue: null, pbt: null, covered_taxes: null, payroll: null, tangible_assets: null }
      for (const col of mappings) {
        if (!col.mapped_field) continue
        const value = String(raw[col.csv_name] ?? '').trim()
        if (col.mapped_field === 'jurisdiction') row.jurisdiction = value
        else if (col.mapped_field === 'currency') row.currency = value.toUpperCase()
        else if (isNumericField(col.mapped_field)) {
          if (value === '') { row[col.mapped_field] = null; continue }
          const num = Number(value.replace(/,/g, ''))
          if (Number.isNaN(num)) {
            // A non-empty cell that is not a number (e.g. "八千五百万") must be
            // surfaced, never silently stored as null.
            errors.push(`第 ${rowIndex + 2} 行「${col.csv_name}」的值 "${value}" 无法解析为数字`)
            row[col.mapped_field] = null
          } else {
            row[col.mapped_field] = num
          }
        }
      }
      return row
    })
    return { rows, errors }
  }

  // Show unparseable cells as soon as the mapping changes, before the user clicks
  // "确认导入", so a bad value can be corrected rather than committed as blank.
  useEffect(() => {
    if (!uploadResult) { setParseErrors([]); return }
    setParseErrors(buildRows().errors)
  }, [uploadResult, mappings])

  const confirmCommit = async () => {
    const { rows, errors } = buildRows()
    if (errors.length > 0) {
      setError(`有 ${errors.length} 处数值无法解析，已阻止导入。请修正 CSV 后重新上传，或调整列映射。`)
      return
    }
    const blankJurisdiction = rows.filter((row) => !row.jurisdiction).length
    if (blankJurisdiction > 0) {
      setError(`有 ${blankJurisdiction} 行缺少 Jurisdiction，请检查列映射后重试。`)
      return
    }
    setCommitting(true)
    setError('')
    try {
      const result = await batchCommitCsv({ company_id: companyId, fiscal_year: fiscalYear, rows })
      setCommitResult(result)
      setMessage(`已导入 ${result.success_count} 条数据，请前往 Data entry 提交审批。`)
    } catch (err) {
      setError(err instanceof Error ? err.message : '数据导入失败。')
    } finally {
      setCommitting(false)
    }
  }

  return <section className="page-wrap entry-page"><div className="page-heading"><div><p className="eyebrow">Stage 3 — bulk ingest</p><h1>CSV bulk upload</h1><p className="heading-copy">上传 CSV，系统自动识别列名并映射到系统字段，人工复核后批量写入，再走提交→审批流程。</p></div></div>
    {error && <div className="alert alert-error" role="alert">{error}</div>}{message && <div className="alert alert-success" role="status">{message}</div>}
    <div className="workflow-grid">
      <article className="workflow-step"><div className="step-number">01</div><div><h2>Select file</h2><p>子公司只能上传自己实体的数据；请确认 CSV 首行为列名。</p></div>
        <form onSubmit={runUpload}>
          <div className="form-grid compact-grid">
            <label>Company<select value={companyId} onChange={(event) => setCompanyId(event.target.value)} disabled={isSubsidiary} title={isSubsidiary ? 'Your entity is bound to the account' : undefined}><option value="">Select company</option>{companies.filter((company) => !isSubsidiary || company.id === entityId).map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}</select></label>
            <label>Fiscal year<select value={fiscalYear} onChange={(event) => setFiscalYear(Number(event.target.value))}><option value="2024">2024</option><option value="2025">2025</option><option value="2026">2026</option><option value="2027">2027</option><option value="2028">2028</option></select></label>
          </div>
          <div
            className={`drop-zone${dragging ? ' drop-zone-active' : ''}`}
            onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
          >
            <input ref={fileInputRef} type="file" accept=".csv,text/csv" style={{ display: 'none' }} onChange={(event) => onFileChosen(event.target.files?.[0] ?? null)} />
            <p className="drop-zone-title">{file ? `📄 ${file.name}` : dragging ? '释放以上传' : '拖拽 CSV 到这里，或点击选择'}</p>
            <p className="drop-zone-hint">支持 UTF-8 / GBK 编码，首行为列名</p>
          </div>
          <div className="form-actions"><button className="button button-primary" type="submit" disabled={!file || !companyId || uploading}>{uploading ? '🤖 正在解析并映射列名...' : '解析并映射列名'}</button></div>
        </form>
      </article>

      <article className="workflow-step"><div className="step-number">02</div><div><h2>Review column mapping</h2><p>AI 建议基于列名与样本值。置信度低于 60% 的列必须人工选择。</p></div>
        {uploadResult && mappings.length > 0 && (
          <div className="mapping-list">
            {mappings.map((mapping, index) => (
              <label key={`${mapping.csv_name}-${index}`} className={`mapping-row${!mapping.mapped_field ? ' mapping-unmapped' : ''}`}>
                <span>{mapping.csv_name}</span><span aria-hidden="true">→</span>
                <select value={mapping.mapped_field ?? IGNORE_VALUE} onChange={(event) => updateMapping(index, event.target.value)}>
                  <option value={IGNORE_VALUE}>— 忽略此列 —</option>
                  {STANDARD_FIELDS.map((field) => <option key={field} value={field}>{FIELD_LABELS[field]}</option>)}
                </select>
                {mapping.mapped_field
                  ? <small className={mapping.confidence < MANUAL_THRESHOLD ? 'confidence-low' : 'confidence-ok'}>{mapping.mapped_field === 'ignore' ? '' : `${Math.round(mapping.confidence * 100)}%`}</small>
                  : <small className="confidence-missing">❌ 需人工选择</small>}
              </label>
            ))}
          </div>
        )}
        {parseErrors.length > 0 && (
          <div className="alert alert-error" role="alert">
            <strong>{parseErrors.length} 处数值无法解析为数字，导入已被阻止：</strong>
            <ul className="parse-error-list">{parseErrors.slice(0, 5).map((e) => <li key={e}>{e}</li>)}</ul>
          </div>
        )}
        {uploadResult && uploadResult.preview_data.length > 0 && (
          <div className="data-preview">
            <h4>数据预览（前 {uploadResult.preview_data.length} 行 / 共 {uploadResult.total_rows} 行）</h4>
            <div className="preview-table-wrap"><table className="preview-table"><thead><tr>{Object.keys(uploadResult.preview_data[0]).map((key) => <th key={key}>{key}</th>)}</tr></thead><tbody>{uploadResult.preview_data.map((row, idx) => <tr key={idx}>{Object.values(row).map((value, cellIdx) => <td key={cellIdx}>{String(value)}</td>)}</tr>)}</tbody></table></div>
          </div>
        )}
        {uploadResult && (
          <div className="form-actions"><button className="button button-primary" type="button" onClick={() => void confirmCommit()} disabled={committing}>{committing ? '正在写入...' : `确认导入 ${uploadResult.total_rows} 条（存为草稿）`}</button>
            <button className="button button-secondary" type="button" onClick={() => navigate('/data-entry')}>前往 Data entry 提交审批</button>
          </div>
        )}
      </article>
    </div>
  </section>
}
