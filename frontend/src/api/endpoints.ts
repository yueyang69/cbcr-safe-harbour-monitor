import { api } from './client'
import type {
  BatchCommitResult,
  BatchRowInput,
  BatchUploadResult,
  Company,
  DashboardData,
  FinancialData,
  FinancialDataInput,
  JurisdictionSummary,
  MappingSuggestion,
  AnomalyDetectionResponse,
  SuggestMissingResponse,
  BriefingResponse,
  ChatResponse
} from '../types'

export async function getDashboard(fiscalYear?: number): Promise<DashboardData> {
  const { data } = await api.get<DashboardData>('/dashboard', { params: fiscalYear ? { fiscal_year: fiscalYear } : undefined })
  return data
}

export async function getSummary(id: string): Promise<JurisdictionSummary> {
  const { data } = await api.get<JurisdictionSummary>(`/summaries/${id}`)
  return data
}

export async function listSummaries(fiscalYear?: number): Promise<JurisdictionSummary[]> {
  const { data } = await api.get<JurisdictionSummary[]>('/summaries', { params: fiscalYear ? { fiscal_year: fiscalYear } : undefined })
  return data
}

export async function rebuildSummaries(fiscalYear: number): Promise<JurisdictionSummary[]> {
  const { data } = await api.post<JurisdictionSummary[]>('/summaries/rebuild', null, { params: { fiscal_year: fiscalYear } })
  return data
}

export async function listCompanies(): Promise<Company[]> {
  const { data } = await api.get<Company[]>('/companies')
  return data
}

// HQ-override request used ONLY by the demo identity switcher to enumerate
// entities. Real backend permissions stay strict — a subsidiary can still only
// ever read its own entity.
export async function listAllCompanies(): Promise<Company[]> {
  const { data } = await api.get<Company[]>('/companies', { headers: { 'X-User-Role': 'hq' } })
  return data
}

export async function suggestMapping(sourceFields: string[]): Promise<MappingSuggestion[]> {
  const { data } = await api.post<MappingSuggestion[]>('/mapping/suggest', { source_fields: sourceFields })
  return data
}

export async function confirmMapping(mappings: MappingSuggestion[]): Promise<MappingSuggestion[]> {
  const { data } = await api.post<MappingSuggestion[]>('/mapping/confirm', { mappings })
  return data
}

export async function createFinancialData(payload: FinancialDataInput): Promise<FinancialData> {
  const { data } = await api.post<FinancialData>('/financial-data', payload)
  return data
}

// MVP quick-test: upsert + auto-approve + rebuild, so the row shows on the
// Dashboard immediately. HQ/admin only (the approver enters and approves in one step).
export async function quickSubmitFinancialData(payload: FinancialDataInput): Promise<FinancialData> {
  const { data } = await api.post<FinancialData>('/financial-data/quick-submit', payload)
  return data
}

export async function listFinancialData(companyId?: string): Promise<FinancialData[]> {
  const { data } = await api.get<FinancialData[]>('/financial-data', { params: companyId ? { company_id: companyId } : undefined })
  return data
}

export async function submitFinancialData(id: string): Promise<FinancialData> {
  const { data } = await api.post<FinancialData>(`/financial-data/${id}/submit`)
  return data
}

export async function approveFinancialData(id: string): Promise<FinancialData> {
  const { data } = await api.post<FinancialData>(`/financial-data/${id}/approve`)
  return data
}

export async function returnFinancialData(id: string): Promise<FinancialData> {
  const { data } = await api.post<FinancialData>(`/financial-data/${id}/return`)
  return data
}

export async function updateFinancialData(id: string, payload: FinancialDataInput): Promise<FinancialData> {
  const { data } = await api.put<FinancialData>(`/financial-data/${id}`, payload)
  return data
}

export async function deleteFinancialData(id: string): Promise<void> {
  await api.delete(`/financial-data/${id}`)
}

// AI Service Endpoints
export async function detectAnomalies(payload: FinancialDataInput): Promise<AnomalyDetectionResponse> {
  const { data } = await api.post<AnomalyDetectionResponse>('/ai/anomaly-detection', payload)
  return data
}

export async function suggestMissingValue(companyId: string, fieldName: string): Promise<SuggestMissingResponse> {
  const { data } = await api.post<SuggestMissingResponse>('/ai/suggest-missing', { company_id: companyId, field_name: fieldName })
  return data
}

export async function generateBriefing(fiscalYear?: number): Promise<BriefingResponse> {
  const { data } = await api.post<BriefingResponse>('/ai/briefing', null, { params: fiscalYear ? { fiscal_year: fiscalYear } : undefined })
  return data
}

export async function chatAssistant(message: string, jurisdiction?: string): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>('/ai/chat', { message, jurisdiction })
  return data
}

// Stage 3 — CSV batch upload
export async function batchUploadCsv(file: File, companyId: string, fiscalYear: number): Promise<BatchUploadResult> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('company_id', companyId)
  formData.append('fiscal_year', String(fiscalYear))
  const { data } = await api.post<BatchUploadResult>('/financial-data/batch-upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  return data
}

export async function batchCommitCsv(payload: { company_id: string; fiscal_year: number; rows: BatchRowInput[] }): Promise<BatchCommitResult> {
  const { data } = await api.post<BatchCommitResult>('/financial-data/batch-commit', payload)
  return data
}
