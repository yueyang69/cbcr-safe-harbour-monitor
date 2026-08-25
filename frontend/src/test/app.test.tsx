import { describe, expect, it, vi, afterEach } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { StatusBadge } from '../components/StatusBadge'
import { listAllCompanies, listFinancialData, quickSubmitFinancialData } from '../api/endpoints'
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
  deleteFinancialData: vi.fn().mockResolvedValue(undefined),
  login: vi.fn().mockResolvedValue({ role: 'admin', username: 'admin' }),
  listJurisdictions: vi.fn().mockResolvedValue(['Japan', 'Germany', 'United States']),
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

  it('reloads the page data when the entity switcher changes', async () => {
    localStorage.setItem('cbcr-role', 'subsidiary')
    localStorage.setItem('cbcr-entity', 'ent-1')
    vi.mocked(listAllCompanies).mockResolvedValue([
      { id: 'ent-1', name: 'Acme China A', country: 'CN', entity_type: 'subsidiary', parent_entity_id: null },
      { id: 'ent-2', name: 'Acme China B', country: 'CN', entity_type: 'subsidiary', parent_entity_id: null },
    ])
    vi.mocked(listFinancialData).mockResolvedValue([draftRow])
    const { AppRoutes } = await import('../App')
    render(<MemoryRouter initialEntries={['/data-entry']}><AppRoutes /></MemoryRouter>)

    await screen.findByText('Confirm field mapping')
    const callsBefore = vi.mocked(listFinancialData).mock.calls.length

    fireEvent.change(screen.getByLabelText('Current entity'), { target: { value: 'ent-2' } })
    await waitFor(() => expect(vi.mocked(listFinancialData).mock.calls.length).toBeGreaterThan(callsBefore))
  })
})

describe('jurisdiction whitelist', () => {
  it('offers a datalist of recognised countries/regions', async () => {
    localStorage.setItem('cbcr-role', 'hq')
    const { AppRoutes } = await import('../App')
    render(<MemoryRouter initialEntries={['/data-entry']}><AppRoutes /></MemoryRouter>)

    await screen.findByText('Confirm field mapping')
    expect(screen.getByLabelText('Jurisdiction')).toHaveAttribute('list', 'jurisdiction-datalist')
  })

  it('blocks a jurisdiction that is not on the whitelist', async () => {
    localStorage.setItem('cbcr-role', 'hq')
    const { AppRoutes } = await import('../App')
    render(<MemoryRouter initialEntries={['/data-entry']}><AppRoutes /></MemoryRouter>)

    await screen.findByText('Confirm field mapping')
    fireEvent.change(screen.getByLabelText('Jurisdiction'), { target: { value: 'TestReturn' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save & publish to dashboard' }))

    expect(await screen.findByText(/recognised country\/region/)).toBeVisible()
    expect(quickSubmitFinancialData).not.toHaveBeenCalled()
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

  it('shows admin-only delete controls and an all-records table', async () => {
    localStorage.setItem('cbcr-role', 'admin')
    localStorage.setItem('cbcr-admin-auth', '1')
    vi.mocked(listFinancialData).mockResolvedValue([pendingRow])
    const { AppRoutes } = await import('../App')
    render(<MemoryRouter initialEntries={['/approvals']}><AppRoutes /></MemoryRouter>)

    expect(await screen.findByRole('heading', { name: 'Approvals' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'All records' })).toBeVisible()
    expect(screen.getByText('Pending review')).toBeVisible()
    expect(screen.getAllByRole('button', { name: 'Delete' }).length).toBeGreaterThan(0)
  })

  it('opens a reason dialog when returning a submission', async () => {
    localStorage.setItem('cbcr-role', 'hq')
    vi.mocked(listFinancialData).mockResolvedValue([pendingRow])
    const { AppRoutes } = await import('../App')
    render(<MemoryRouter initialEntries={['/approvals']}><AppRoutes /></MemoryRouter>)

    await screen.findByText('Acme China A')
    fireEvent.click(screen.getByRole('button', { name: 'Return' }))
    expect(await screen.findByRole('dialog', { name: 'Return submission' })).toBeVisible()
    expect(screen.getByPlaceholderText(/Reason for returning/i)).toBeVisible()
  })
})

describe('returned draft resubmission for subsidiary', () => {
  it('surfaces the HQ return reason and offers combined update + resubmit', async () => {
    localStorage.setItem('cbcr-role', 'subsidiary')
    localStorage.setItem('cbcr-entity', 'ent-1')
    vi.mocked(listFinancialData).mockResolvedValueOnce([{ ...draftRow, return_reason: 'Revenue does not match the trial balance.' }])
    const { AppRoutes } = await import('../App')
    render(<MemoryRouter initialEntries={['/data-entry']}><AppRoutes /></MemoryRouter>)

    expect(await screen.findByText(/HQ returned your submission/)).toBeVisible()
    expect(screen.getByText(/trial balance/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Update & resubmit for approval' })).toBeVisible()
  })
})

describe('admin login page', () => {
  it('signs in as admin and lands on the approvals queue', async () => {
    localStorage.setItem('cbcr-role', 'hq')
    const { AppRoutes } = await import('../App')
    render(<MemoryRouter initialEntries={['/login']}><AppRoutes /></MemoryRouter>)

    await screen.findByRole('heading', { name: 'Sign in' })
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'admin' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'admin123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in as Admin' }))

    expect(await screen.findByRole('heading', { name: 'Approvals' })).toBeVisible()
    expect(localStorage.getItem('cbcr-role')).toBe('admin')
    expect(localStorage.getItem('cbcr-admin-auth')).toBe('1')
  })
})
