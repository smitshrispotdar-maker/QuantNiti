import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { DataQualityPanel } from '../pages/Dashboard.jsx'

// Mock the Badge component from api.jsx
vi.mock('../api.jsx', () => ({
  Badge: ({ status }) => <span data-testid="badge" className="badge">{status}</span>,
}))

const mockMetaNoQuality = {
  status: 'SIMULATED',
  source: 'MOCK GENERATOR',
  timeframe: '1d',
  last_bar: '2026-11-02T00:00:00',
  fetched_at: '2026-11-02T12:00:00',
}

const mockMetaWithQuality = {
  status: 'DELAYED',
  source: 'YAHOO FINANCE',
  timeframe: '1d',
  last_bar: '2026-11-02T00:00:00',
  fetched_at: '2026-11-02T12:00:00',
  data_quality: {
    issues: ['Fixed high < max(open, close) on some rows'],
    gaps: ['2 missing bar(s) detected'],
    duplicates: ['1 duplicate timestamp(s) found'],
    bar_count: 120,
    cached: false,
    cache_age_seconds: null,
  }
}

const mockMetaCached = {
  status: 'CACHED',
  source: 'YAHOO FINANCE',
  timeframe: '1d',
  last_bar: '2026-11-02T00:00:00',
  fetched_at: '2026-11-02T12:00:00',
  data_quality: {
    issues: [],
    gaps: [],
    duplicates: [],
    bar_count: 100,
    cached: true,
    cache_age_seconds: 3660, // 1h 1m
  }
}

const mockMetaWithIssues = {
  status: 'DELAYED',
  source: 'YAHOO FINANCE',
  timeframe: '1d',
  last_bar: '2026-11-02T00:00:00',
  fetched_at: '2026-11-02T12:00:00',
  data_quality: {
    issues: ['Fixed high < max(open, close) on some rows', 'Fixed low > min(open, close) on some rows'],
    gaps: ['5 missing bar(s) detected'],
    duplicates: ['3 duplicate timestamp(s) found'],
    bar_count: 50,
    cached: false,
    cache_age_seconds: null,
  }
}

describe('DataQualityPanel', () => {
  it('renders "Quality information unavailable" when no data_quality in meta', () => {
    render(<DataQualityPanel meta={mockMetaNoQuality} />)
    expect(screen.getByText('Data Quality')).toBeInTheDocument()
    expect(screen.getByText('Quality information unavailable')).toBeInTheDocument()
    // The status and source badges are still rendered even without data_quality
    expect(screen.getByText('SIMULATED')).toBeInTheDocument()
    expect(screen.getByText('MOCK GENERATOR')).toBeInTheDocument()
  })

  it('renders data quality metrics when data_quality is present', () => {
    render(<DataQualityPanel meta={mockMetaWithQuality} />)
    expect(screen.getByText('Data Quality')).toBeInTheDocument()
    expect(screen.getByText('120')).toBeInTheDocument() // bar_count
    expect(screen.getByText('1d')).toBeInTheDocument() // timeframe
    expect(screen.getByText('MISS')).toBeInTheDocument() // cache status (not cached)
    expect(screen.getByText('—')).toBeInTheDocument() // cache age
  })

  it('renders cached status correctly', () => {
    render(<DataQualityPanel meta={mockMetaCached} />)
    expect(screen.getByText('HIT')).toBeInTheDocument() // cache status (cached)
    expect(screen.getByText('1h')).toBeInTheDocument() // cache age ~1h
  })

  it('renders quality warnings when issues, gaps, or duplicates exist', () => {
    render(<DataQualityPanel meta={mockMetaWithIssues} />)
    expect(screen.getByText('Quality Warnings')).toBeInTheDocument()
    expect(screen.getByText('OHLC Issues (2)')).toBeInTheDocument()
    expect(screen.getByText('Timestamp Gaps (1)')).toBeInTheDocument()
    expect(screen.getByText('Duplicate Timestamps (1)')).toBeInTheDocument()
    expect(screen.getByText('Fixed high < max(open, close) on some rows')).toBeInTheDocument()
    expect(screen.getByText('5 missing bar(s) detected')).toBeInTheDocument()
    expect(screen.getByText('3 duplicate timestamp(s) found')).toBeInTheDocument()
  })

  it('limits displayed warnings to 3 items with "more" indicator', () => {
    const metaManyIssues = {
      status: 'DELAYED',
      source: 'YAHOO FINANCE',
      timeframe: '1d',
      last_bar: '2026-11-02T00:00:00',
      fetched_at: '2026-11-02T12:00:00',
      data_quality: {
        issues: ['Issue 1', 'Issue 2', 'Issue 3', 'Issue 4', 'Issue 5'],
        gaps: [],
        duplicates: [],
        bar_count: 100,
        cached: false,
        cache_age_seconds: null,
      }
    }
    render(<DataQualityPanel meta={metaManyIssues} />)
    expect(screen.getByText('OHLC Issues (5)')).toBeInTheDocument()
    expect(screen.getByText('Issue 1')).toBeInTheDocument()
    expect(screen.getByText('Issue 2')).toBeInTheDocument()
    expect(screen.getByText('Issue 3')).toBeInTheDocument()
    expect(screen.getByText('+2 more...')).toBeInTheDocument()
  })

  it('displays status and source badges', () => {
    render(<DataQualityPanel meta={mockMetaWithQuality} />)
    expect(screen.getByText('DELAYED')).toBeInTheDocument()
    expect(screen.getByText('YAHOO FINANCE')).toBeInTheDocument()
  })

  it('formats cache age correctly', () => {
    const metaShortCache = {
      status: 'CACHED',
      source: 'YAHOO FINANCE',
      timeframe: '1d',
      last_bar: '2026-11-02T00:00:00',
      fetched_at: '2026-11-02T12:00:00',
      data_quality: {
        issues: [],
        gaps: [],
        duplicates: [],
        bar_count: 100,
        cached: true,
        cache_age_seconds: 30, // 30 seconds
      }
    }
    const { container } = render(<DataQualityPanel meta={metaShortCache} />)
    expect(container.querySelector('[data-testid="cache-age"]').textContent).toBe('30s')

    const metaHourCache = {
      ...metaShortCache,
      data_quality: { ...metaShortCache.data_quality, cache_age_seconds: 3660 } // 1h 1m
    }
    const { container: container2 } = render(<DataQualityPanel meta={metaHourCache} />)
    expect(container2.querySelector('[data-testid="cache-age"]').textContent).toBe('1h')

    const metaDayCache = {
      ...metaShortCache,
      data_quality: { ...metaShortCache.data_quality, cache_age_seconds: 90000 } // 1 day 1h
    }
    const { container: container3 } = render(<DataQualityPanel meta={metaDayCache} />)
    expect(container3.querySelector('[data-testid="cache-age"]').textContent).toBe('1d')
  })

  it('shows correct status badge colors via className', () => {
    const { container } = render(<DataQualityPanel meta={mockMetaWithQuality} />)
    const badge = container.querySelector('[data-testid="badge"]')
    expect(badge).toBeInTheDocument()
  })
})