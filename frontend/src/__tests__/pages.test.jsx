import { render } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Dashboard from '../pages/Dashboard.jsx'
import Studio from '../pages/Studio.jsx'
import Builder from '../pages/Builder.jsx'
import Backtest from '../pages/Backtest.jsx'
import Paper from '../pages/Paper.jsx'
import Journal from '../pages/Journal.jsx'

// Mock the API module
vi.mock('../api.jsx', () => ({
  api: vi.fn(() => Promise.resolve({})),
  fmt: (n, d = 2) => (n == null ? '—' : Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })),
  pnlColor: (n) => (n >= 0 ? 'text-up' : 'text-down'),
  Badge: ({ status }) => <span data-testid="badge">{status}</span>,
  ErrorBox: ({ err }) => err ? <div data-testid="error">{err.message}</div> : null,
}))

import { fmt, pnlColor } from '../api.jsx'

const mockDraft = {
  schema_version: '1.0',
  name: 'Test Strategy',
  instruments: ['BTC-USD'],
  timeframe: '1d',
  indicators: [],
  entry_rules: [],
  exit_rules: [],
  risk: { max_position_pct: 25, stop_loss_pct: 5, take_profit_pct: null, max_drawdown_pct: 25 },
}

const mockSaved = { id: 1, version: 1, spec: mockDraft }

describe('Pages render without crashing', () => {
  it('renders Dashboard', () => {
    const { container } = render(<Dashboard />)
    expect(container).toBeInTheDocument()
  })

  it('renders Studio', () => {
    const setDraft = vi.fn()
    const setSaved = vi.fn()
    const { container } = render(<Studio setDraft={setDraft} draft={mockDraft} setSaved={setSaved} saved={mockSaved} />)
    expect(container).toBeInTheDocument()
  })

  it('renders Builder', () => {
    const setDraft = vi.fn()
    const setSaved = vi.fn()
    const { container } = render(<Builder setDraft={setDraft} draft={mockDraft} setSaved={setSaved} />)
    expect(container).toBeInTheDocument()
  })

  it('renders Backtest', () => {
    const setSaved = vi.fn()
    const { container } = render(<Backtest setSaved={setSaved} saved={mockSaved} draft={mockDraft} />)
    expect(container).toBeInTheDocument()
  })

  it('renders Paper', () => {
    const { container } = render(<Paper />)
    expect(container).toBeInTheDocument()
  })

  it('renders Journal', () => {
    const { container } = render(<Journal saved={mockSaved} />)
    expect(container).toBeInTheDocument()
  })
})

describe('API utilities', () => {
  it('fmt formats numbers correctly', () => {
    expect(fmt(1000)).toBe('1,000.00')
    expect(fmt(1000.5, 1)).toBe('1,000.5')
    expect(fmt(null)).toBe('—')
  })

  it('pnlColor returns correct color class', () => {
    expect(pnlColor(100)).toBe('text-up')
    expect(pnlColor(-50)).toBe('text-down')
    expect(pnlColor(0)).toBe('text-up')
  })
})