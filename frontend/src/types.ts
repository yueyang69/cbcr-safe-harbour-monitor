export type UserRole = 'subsidiary' | 'hq' | 'reviewer' | 'admin'
export type EntityType = 'subsidiary' | 'branch'
export type ResultStatus = 'PASS' | 'FAIL' | 'WARNING' | 'INCOMPLETE'
export type NumericValue = string | number | null

export interface TestResult {
  result: ResultStatus
  explanation: string
  value?: NumericValue
  threshold?: NumericValue
  payroll_rate?: NumericValue
  asset_rate?: NumericValue
}

export interface Evaluation {
  tests: {
    de_minimis: TestResult
    simplified_etr: TestResult
    routine_profits: TestResult
  }
  final_result: ResultStatus
  warning: string | null
}

export interface DashboardJurisdiction {
  id: string
  jurisdiction: string
  revenue: NumericValue
  pbt: NumericValue
  evaluation: Evaluation | null
  status: ResultStatus
  warnings: string[]
}

export interface DashboardData {
  fiscal_year: number | null
  kpis: {
    jurisdiction_count: number
    pass_count: number
    warning_count: number
    incomplete_count: number
  }
  jurisdictions: DashboardJurisdiction[]
}

export interface JurisdictionSummary extends DashboardJurisdiction {
  fiscal_year: number
  covered_taxes: NumericValue
  payroll: NumericValue
  tangible_assets: NumericValue
  company_count: number
  included_count: number
}

export interface MappingSuggestion {
  source_field: string
  target_field: string
  confidence: string | number
}

export interface Company {
  id: string
  name: string
  country: string | null
  entity_type: EntityType
  parent_entity_id: string | null
}

export interface FinancialDataInput {
  company_id: string
  fiscal_year: number
  jurisdiction: string
  currency: string
  revenue: number | null
  pbt: number | null
  covered_taxes: number | null
  payroll: number | null
  tangible_assets: number | null
}

export interface FinancialData extends FinancialDataInput {
  id: string
  is_submitted: boolean
  is_approved: boolean
  requires_manual_confirmation: boolean
  ai_anomaly_flags?: AnomalyFlag[] | null
  missing_suggestion?: Record<string, unknown> | null
}

// AI Service Types
export interface AnomalyFlag {
  type: 'ratio_anomaly' | 'volatility_anomaly' | 'missing_critical'
  field: string
  message: string
  severity: 'warning' | 'error'
}

export interface AnomalyDetectionResponse {
  anomalies: AnomalyFlag[]
}

export interface SuggestMissingResponse {
  field_name: string
  suggested_value: number | null
  confidence: number
  explanation: string
}

export interface BriefingResponse {
  briefing: string
  generated_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  reply: string
}

// Stage 3 — CSV batch upload types
export interface ColumnMappingInfo {
  csv_name: string
  mapped_field: string | null
  confidence: number
  sample_values: string[]
}

export interface BatchUploadResult {
  columns: ColumnMappingInfo[]
  preview_data: Record<string, string>[]
  rows: Record<string, string>[]
  total_rows: number
  fiscal_year: number
}

export interface BatchRowInput {
  jurisdiction: string
  currency: string
  revenue: number | null
  pbt: number | null
  covered_taxes: number | null
  payroll: number | null
  tangible_assets: number | null
}

export interface BatchCommitResult {
  success_count: number
  failed_rows: { row_index: number; error: string }[]
}
