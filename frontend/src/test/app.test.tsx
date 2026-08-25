import { describe, expect, it, vi, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { StatusBadge } from '../components/StatusBadge'
import { listFinancialData } from '../api/endpoints'
import type { FinancialData } from '../types'

const draftRow: FinancialData = {
  id: 'fd-1', company_id: 'ent-1', fiscal_year: 2025, jurisdiction: 'Japan', currency: 'EUR',
  revenue: 8000000, pbt: 500000, covered_taxes: 50000, payroll: 1000000, tangible_assets: 2000000,
  is_submitted: false, is_approved: false, requires_manual_confirmation: false, ai_anomaly_flags: null, missing_suggestion: null,
}
const pendingRow: FinancialData = { ...draftRow, id: 'fd-2', is_submitted: true }

vi.mock('../api/endpoints', () => ({
  getDashboard: vi.fn().mockResolvedValue({ fiscal_year: 2025, kpis: { jurisdiction_count: 1, pass_count: 1, warning_count: 0, incomplete_count: 0 }, jurisdictions: [] }),
  rebuildSummaries: vi.fn(),
  listCompanies: vi.fn().mockResolvedValue([{ id: 'ent-1', name: 'Acme China A', country: 'CN', entity_type: 'subsidiary', parent_entity_id: null }]),
  listAllCompanies: vi.fn().mockResolvedValue([{ id: 'ent-1', name: 'Acme China A', country: 'CN', entity_type: 'subsidiary', parent_entity_id: null }]),
  suggestMapping: vi.fn(),
  confirmMapping: vi.fn(),
  createFinancialData: vi.fn(),
  quickSubmitFinancialData: vi.fn().mockResolvedValue({}),
  detectAnomalies: vi.fn(),
  listFinancialData: vi.fn().mockResolvedValue([]),
  submitFinancialData: vi.fn().mockResolvedValue({}),
  approveFinancialData: vi.fn().mockResolvedValue({}),
  returnFinancialData: vi.fn().mockResolvedValue({}),
  updateFinancialData: vi.fn().mockResolvedValue({}),
  batchUploadCsv: vi.fn(),
  batchCommitCsv: vi.fn(),
}))

afterEach(() => { cleanup(); localStorage.clear(); vi.mocked(listFinancialData).mockResolvedValue([]) })

describe('StatusBadge', () => {
  it('exposes the result as text and not color alone', () => {
    render(<StatusBadge status="WARNING" />)
    expect(screen.getByText('Risk warning')).toBeVisible()
  })
})

describe('app shell', () => {
  it('renders dashboard navigation and disclaimer', async () => {
    const { AppRoutes } = await import('../App')
    render(<MemoryRouter initialEntries={['/dashboard']}><AppRoutes /></MemoryRouter>)
    expect(await screen.findByRole('heading', { name: 'Safe Harbour monitor' })).toBeVisible()
    expect(screen.getByText(/does not calculate GloBE Top-up Tax/i)).toBeVisible()
  })
})

describe('data entry for subsidiary', () => {
  it('shows the mapping step and locks the company dropdown to the bound entity', async () => {
    localStorage.setItem('cbcr-role', 'subsidiary')
    localStorage.setItem('cbcr-entity', 'ent-1')
    const { AppRoutes } = await import('../App')
    render(<MemoryRouter initialEntries={['/data-entry']}><AppRoutes /></MemoryRouter>)

    expect(await screen.findByText('Confirm field mapping')).toBeVisible()
    expect(screen.getByText('Source data workspace')).toBeVisible()

    const companySelect = await screen.findByLabelText('Company')
    expect(companySelect).toHaveValue('ent-1')
    expect(companySelect).toBeDisabled()
  })

  it('shows the HQ publish button so a save lands on the dashboard', async () => {
    localStorage.setItem('cbcr-role', 'hq')
    const { AppRoutes } = await import('../App')
    render(<MemoryRouter initialEntries={['/data-entry']}><AppRoutes /></MemoryRouter>)

    expect(await screen.findByText('Save & publish to dashboard')).toBeVisible()
    expect(screen.getByText('Confirm field mapping')).toBeVisible()
  })

  it('prompts to select an entity and skips fetching companies when no entity is bound', async () => {
    localStorage.setItem('cbcr-role', 'subsidiary')
    const { AppRoutes } = await import('../App')
    render(<MemoryRouter initialEntries={['/data-entry']}><AppRoutes /></MemoryRouter>)

    expect(await screen.findByText('Select an entity in the top-right before entering data.')).toBeVisible()
    expect(screen.getByText('Save source data').closest('button')).toBeDisabled()
  })

  it('resumes a saved draft and offers submit-for-approval', async () => {
    localStorage.setItem('cbcr-role', 'subsidiary')
    localStorage.setItem('cbcr-entity', 'ent-1')
    vi.mocked(listFinancialData).mockResolvedValueOnce([draftRow])
    const { AppRoutes } = await import('../App')
    render(<MemoryRouter initialEntries={['/data-entry']}><AppRoutes /></MemoryRouter>)

    expect(await screen.findByText('Submit for approval')).toBeVisible()
    expect(screen.getByText('Update draft')).toBeVisible()
  })
})

describe('HQ approval queue', () => {
  it('lists submitted rows awaiting review with approve/return actions', async () => {
    localStorage.setItem('cbcr-role', 'hq')
    vi.mocked(listFinancialData).mockResolvedValue([pendingRow])
    const { AppRoutes } = await import('../App')
    render(<MemoryRouter initialEntries={['/approvals']}><AppRoutes /></MemoryRouter>)

    expect(await screen.findByRole('heading', { name: 'Approvals' })).toBeVisible()
    expect(screen.getByText('Acme China A')).toBeVisible()
    expect(screen.getByText('Japan')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Approve' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Return' })).toBeVisible()
  })

  it('shows an empty state when nothing is awaiting review', async () => {
    localStorage.setItem('cbcr-role', 'hq')
    const { AppRoutes } = await import('../App')
    render(<MemoryRouter initialEntries={['/approvals']}><AppRoutes /></MemoryRouter>)

    expect(await screen.findByText('No submissions awaiting review')).toBeVisible()
  })
})
