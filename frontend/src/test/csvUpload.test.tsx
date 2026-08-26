import { beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { CsvUploadPage } from '../pages/CsvUploadPage'
import { batchCommitCsv, batchUploadCsv, listCompanies } from '../api/endpoints'
import type { BatchCommitResult, BatchUploadResult } from '../types'

vi.mock('../api/endpoints', () => ({
  listCompanies: vi.fn().mockResolvedValue([
    { id: 'ent-1', name: 'Acme Japan', country: 'JP', entity_type: 'subsidiary', parent_entity_id: null },
  ]),
  batchUploadCsv: vi.fn(),
  batchCommitCsv: vi.fn(),
}))

const uploadResult: BatchUploadResult = {
  fiscal_year: 2026,
  total_rows: 2,
  columns: [
    { csv_name: 'jurisdiction', mapped_field: 'jurisdiction', confidence: 1.0, sample_values: ['Japan', 'Germany'] },
    { csv_name: 'revenue', mapped_field: 'revenue', confidence: 1.0, sample_values: ['8500000', '4200000'] },
    { csv_name: 'unknown_col', mapped_field: null, confidence: 0, sample_values: ['85', '42'] },
  ],
  preview_data: [
    { jurisdiction: 'Japan', revenue: '8500000', unknown_col: '85' },
    { jurisdiction: 'Germany', revenue: '4200000', unknown_col: '42' },
  ],
  rows: [
    { jurisdiction: 'Japan', revenue: '8500000', unknown_col: '85' },
    { jurisdiction: 'Germany', revenue: '4200000', unknown_col: '42' },
  ],
}

beforeEach(() => {
  cleanup()
  localStorage.clear()
  localStorage.setItem('cbcr-role', 'hq')
  vi.mocked(batchUploadCsv).mockReset()
  vi.mocked(batchCommitCsv).mockReset()
})

describe('CsvUploadPage', () => {
  it('parses the CSV, renders the mapping table and commits rows on confirm', async () => {
    const user = userEvent.setup()
    vi.mocked(batchUploadCsv).mockResolvedValue(uploadResult)
    vi.mocked(batchCommitCsv).mockResolvedValue({ success_count: 2, failed_rows: [] } satisfies BatchCommitResult)

    const { container } = render(<MemoryRouter><CsvUploadPage /></MemoryRouter>)

    // Select a file (input is hidden, fire a change directly)
    const file = new File(['jurisdiction,revenue,unknown_col\nJapan,8500000,x'], 'demo.csv', { type: 'text/csv' })
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(fileInput, { target: { files: [file] } })

    const parseButton = screen.getByRole('button', { name: /解析并映射列名/ })
    await waitFor(() => expect(parseButton).toBeEnabled())
    await user.click(parseButton)

    // Mapping table + preview rendered, unmapped column flagged for manual pick
    expect(await screen.findByText(/数据预览（前 2 行/)).toBeVisible()
    expect(screen.getAllByText('unknown_col').length).toBeGreaterThan(0)
    expect(screen.getByText('❌ 需人工选择')).toBeVisible()

    // Manually map the unknown column to pbt, then confirm
    const comboboxes = screen.getAllByRole('combobox')
    const unknownSelect = comboboxes[comboboxes.length - 1]
    await user.selectOptions(unknownSelect, 'pbt')

    await user.click(screen.getByRole('button', { name: /确认导入 2 条/ }))

    await waitFor(() => {
      expect(batchCommitCsv).toHaveBeenCalledTimes(1)
    })
    const payload = vi.mocked(batchCommitCsv).mock.calls[0][0]
    expect(payload.company_id).toBe('ent-1')
    expect(payload.fiscal_year).toBe(2026)
    expect(payload.rows).toHaveLength(2)
    expect(payload.rows[0].jurisdiction).toBe('Japan')
    expect(payload.rows[0].revenue).toBe(8500000)
    expect(payload.rows[0].pbt).toBe(85)
  })

  it('blocks the commit and surfaces a live warning when a numeric cell is not a number', async () => {
    const user = userEvent.setup()
    vi.mocked(batchUploadCsv).mockResolvedValue({
      ...uploadResult,
      rows: [
        { jurisdiction: 'Japan', revenue: '八千五百万', unknown_col: 'x' },
        { jurisdiction: 'Germany', revenue: '4200000', unknown_col: 'y' },
      ],
    })

    const { container } = render(<MemoryRouter><CsvUploadPage /></MemoryRouter>)
    const file = new File(['jurisdiction,revenue\nJapan,八千五百万'], 'demo.csv', { type: 'text/csv' })
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(fileInput, { target: { files: [file] } })

    const parseButton = screen.getByRole('button', { name: /解析并映射列名/ })
    await waitFor(() => expect(parseButton).toBeEnabled())
    await user.click(parseButton)
    await screen.findByText(/数据预览（前 2 行/)

    // The unparseable cell is surfaced immediately and blocks the commit.
    const warnings = await screen.findAllByText(/无法解析为数字/)
    expect(warnings.length).toBeGreaterThan(0)
    await user.click(screen.getByRole('button', { name: /确认导入 2 条/ }))
    expect(batchCommitCsv).not.toHaveBeenCalled()
  })

  it('warns about blank jurisdictions before committing', async () => {
    const user = userEvent.setup()
    vi.mocked(batchUploadCsv).mockResolvedValue({
      ...uploadResult,
      rows: [
        { jurisdiction: '', revenue: '8500000', unknown_col: 'x' },
        { jurisdiction: 'Germany', revenue: '4200000', unknown_col: 'y' },
      ],
    })

    const { container } = render(<MemoryRouter><CsvUploadPage /></MemoryRouter>)
    const file = new File(['jurisdiction,revenue\n,8500000'], 'demo.csv', { type: 'text/csv' })
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(fileInput, { target: { files: [file] } })

    const parseButton = screen.getByRole('button', { name: /解析并映射列名/ })
    await waitFor(() => expect(parseButton).toBeEnabled())
    await user.click(parseButton)
    await screen.findByText(/数据预览（前 2 行/)

    await user.click(screen.getByRole('button', { name: /确认导入 2 条/ }))

    expect(await screen.findByText(/缺少 Jurisdiction/)).toBeVisible()
    expect(batchCommitCsv).not.toHaveBeenCalled()
  })

  it('prompts subsidiary users to pick an entity when none is bound', async () => {
    localStorage.setItem('cbcr-role', 'subsidiary')
    render(<MemoryRouter><CsvUploadPage /></MemoryRouter>)

    const alerts = await screen.findAllByRole('alert')
    expect(alerts.length).toBeGreaterThan(0)
    expect(alerts[0]).toHaveTextContent('请在右上角先选择实体')
  })
})
