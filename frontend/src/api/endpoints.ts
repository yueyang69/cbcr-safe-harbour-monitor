import { api } from './client'
import type {
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

export async function listFinancialData(companyId?: string): Promise<FinancialData[]> {
  const { data } = await api.get<FinancialData[]>('/financial-data', { params: companyId ? { company_id: companyId } : undefined })
  return data
}

export async function submitFinancialData(id: string): Promise<FinancialData> {
  const { data } = await api.post<FinancialData>(`/financial-data/${id}/submit`)
  return data
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
