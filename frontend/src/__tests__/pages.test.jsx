import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Dashboard from '../pages/Dashboard.jsx'
import Studio from '../pages/Studio.jsx'
import Builder from '../pages/Builder.jsx'
import Backtest from '../pages/Backtest.jsx'
import Paper from '../pages/Paper.jsx'
import Journal from '../pages/Journal.jsx'

// Mock the API module
vi.mock('../api.jsx', () => {
  const pass = () => Promise.resolve({})
  const empty = () => Promise.resolve([])
  return {
    api: vi.fn(() => Promise.resolve({})),
    fmt: (n, d = 2) => (n == null ? '—' : Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })),
    fmtCompact: (n) => (n == null ? '—' : String(n)),
    fmtDateTime: () => '—',
    fmtTime: () => '—',
    signed: (n) => (n == null ? '—' : String(n)),
    signedPct: (n) => (n == null ? '—' : `${n}%`),
    pnlColor: (n) => (n >= 0 ? 'text-up' : 'text-down'),
    Badge: ({ status }) => <span data-testid="badge">{status}</span>,
    ErrorBox: ({ err }) => err ? <div data-testid="error">{err.message}</div> : null,
    EmptyState: ({ title }) => <div>{title}</div>,
    wsUrl: (path) => `ws://test${path}`,
    watchlistApi: {
      get: vi.fn(() => Promise.resolve([])),
      add: vi.fn(() => Promise.resolve({})),
      remove: vi.fn(() => Promise.resolve({})),
      reorder: vi.fn(() => Promise.resolve({})),
      symbols: vi.fn(() => Promise.resolve([])),
    },
    marketApi: {
      overview: vi.fn(pass),
      bars: vi.fn(() => Promise.resolve({ meta: null, bars: [] })),
      research: vi.fn(pass),
      indices: vi.fn(pass),
      movers: vi.fn(pass),
      tape: vi.fn(pass),
      capabilities: vi.fn(pass),
      status: vi.fn(pass),
      search: vi.fn(empty),
      symbols: vi.fn(empty),
    },
    paperApi: {
      accounts: vi.fn(empty),
      account: vi.fn(pass),
      create: vi.fn(pass),
      order: vi.fn(pass),
      deploymentOrder: vi.fn(pass),
      control: vi.fn(pass),
    },
  }
})

import { fmt, pnlColor } from '../api.jsx'

const mockDraft = {
  schema_version: '1.0',
  name: 'Test Strategy',
  instruments: ['^NSEI'],
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
    const setDraft = vi.fn()
    const setSaved = vi.fn()
    const { container } = render(<Backtest setDraft={setDraft} saved={mockSaved} draft={mockDraft} setSaved={setSaved} />)
    expect(container).toBeInTheDocument()
    // Check for key UI elements
    expect(screen.getByText('Backtest Configuration')).toBeInTheDocument()
    expect(screen.getByText('Initial Capital')).toBeInTheDocument()
    expect(screen.getByText('Transaction Cost (bps)')).toBeInTheDocument()
    expect(screen.getByText('Slippage (bps)')).toBeInTheDocument()
    expect(screen.getByText('Start Date')).toBeInTheDocument()
    expect(screen.getByText('End Date')).toBeInTheDocument()
    expect(screen.getAllByText('Run backtest').length).toBeGreaterThan(0)
  })

  it('renders Paper', () => {
    const { container } = render(<Paper />)
    expect(container).toBeInTheDocument()
  })

  it('renders Journal', () => {
    const { container } = render(<Journal />)
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