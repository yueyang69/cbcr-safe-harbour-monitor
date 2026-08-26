import { beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { DataEntryPage } from '../pages/DataEntryPage'
import { SessionContext } from '../session'
import { batchSubmitFinancialData, listCompanies, listFinancialData, submitFinancialData } from '../api/endpoints'
import type { Company, FinancialData } from '../types'

vi.mock('../api/endpoints', () => ({
  listCompanies: vi.fn(),
  listFinancialData: vi.fn(),
  batchSubmitFinancialData: vi.fn(),
  submitFinancialData: vi.fn(),
  quickSubmitFinancialData: vi.fn(),
  createFinancialData: vi.fn(),
  updateFinancialData: vi.fn(),
  deleteFinancialData: vi.fn(),
  detectAnomalies: vi.fn().mockResolvedValue({ anomalies: [] }),
  listJurisdictions: vi.fn().mockResolvedValue(['Japan', 'Germany', 'Netherlands', 'United States']),
  suggestMapping: vi.fn(),
  confirmMapping: vi.fn(),
}))

const company: Company = { id: 'ent-1', name: 'Demo Group', country: 'SG', entity_type: 'subsidiary', parent_entity_id: null }

const drafts: FinancialData[] = [
  { id: 'd1', company_id: 'ent-1', fiscal_year: 2026, jurisdiction: 'Japan', currency: 'EUR', revenue: 8500000, pbt: 1200000, covered_taxes: 450000, payroll: 3200000, tangible_assets: 15000000, is_submitted: false, is_approved: false, requires_manual_confirmation: false },
  { id: 'd2', company_id: 'ent-1', fiscal_year: 2026, jurisdiction: 'Germany', currency: 'EUR', revenue: 4200000, pbt: 380000, covered_taxes: 150000, payroll: 1800000, tangible_assets: 8000000, is_submitted: false, is_approved: false, requires_manual_confirmation: false },
  { id: 'd3', company_id: 'ent-1', fiscal_year: 2026, jurisdiction: 'Netherlands', currency: 'EUR', revenue: 6700000, pbt: 520000, covered_taxes: 210000, payroll: 2800000, tangible_assets: 12000000, is_submitted: false, is_approved: false, requires_manual_confirmation: false },
]

beforeEach(() => {
  cleanup()
  localStorage.clear()
  localStorage.setItem('cbcr-role', 'subsidiary')
  localStorage.setItem('cbcr-entity', 'ent-1')
  vi.mocked(listCompanies).mockResolvedValue([company])
  vi.mocked(listFinancialData).mockResolvedValue(drafts)
  vi.mocked(batchSubmitFinancialData).mockResolvedValue({ submitted_count: 3 })
  vi.mocked(submitFinancialData).mockResolvedValue({ ...drafts[1], is_submitted: true })
})

describe('DataEntryPage batch submit', () => {
  it('submits the whole CSV import with one click', async () => {
    const user = userEvent.setup()
    render(<MemoryRouter><SessionContext.Provider value={{ role: 'subsidiary', entityId: 'ent-1' }}><DataEntryPage /></SessionContext.Provider></MemoryRouter>)

    // First draft loads into the form and the batch button reports 3 remaining drafts
    await screen.findByDisplayValue('Japan')
    const button = await screen.findByRole('button', { name: /提交全部 3 条草稿/ })
    await user.click(button)

    await waitFor(() => {
      expect(batchSubmitFinancialData).toHaveBeenCalledWith('ent-1', 2026)
    })
    expect(await screen.findByText(/已提交 3 条数据/)).toBeVisible()
  })

  it('does not lock the page when a sibling row is already pending approval', async () => {
    // d1 was submitted earlier; d2/d3 are still drafts. The page must NOT freeze.
    vi.mocked(listFinancialData).mockResolvedValue([
      { ...drafts[0], is_submitted: true },
      drafts[1],
      drafts[2],
    ])
    const user = userEvent.setup()
    render(<MemoryRouter><SessionContext.Provider value={{ role: 'subsidiary', entityId: 'ent-1' }}><DataEntryPage /></SessionContext.Provider></MemoryRouter>)

    await screen.findByDisplayValue('Germany')
    const submitBtn = await screen.findByRole('button', { name: 'Submit for approval' })
    expect(submitBtn).toBeEnabled()
    await user.click(submitBtn)
    await waitFor(() => expect(submitFinancialData).toHaveBeenCalledWith('d2'))
  })
})
