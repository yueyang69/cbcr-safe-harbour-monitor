import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { StatusBadge } from '../components/StatusBadge'

const dashboard = { fiscal_year: 2025, kpis: { jurisdiction_count: 1, pass_count: 1, warning_count: 0, incomplete_count: 0 }, jurisdictions: [] }
vi.mock('../api/endpoints', () => ({ getDashboard: vi.fn().mockResolvedValue(dashboard), rebuildSummaries: vi.fn() }))

describe('StatusBadge', () => {
  it('exposes the result as text and not color alone', () => {
    render(<StatusBadge status="WARNING" />)
    expect(screen.getByText('Risk warning')).toBeVisible()
  })
})

describe('app shell', () => {
  it('renders dashboard navigation and disclaimer', async () => {
    const { AppRoutes } = await import('../App')
    const { MemoryRouter } = await import('react-router-dom')
    render(<MemoryRouter initialEntries={['/dashboard']}><AppRoutes /></MemoryRouter>)
    expect(await screen.findByRole('heading', { name: 'Safe Harbour monitor' })).toBeVisible()
    expect(screen.getByText(/does not calculate GloBE Top-up Tax/i)).toBeVisible()
  })
})
