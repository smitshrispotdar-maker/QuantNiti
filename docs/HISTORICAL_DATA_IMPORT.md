# QuantNiti — Historical Data Import CLI

**Date:** 2026-11-03  
**Status:** Implemented and tested

---

## 1. Overview

The Historical Data Import CLI (`python -m app.cli.import_market_data`) enables importing historical OHLCV data from CSV files into the QuantNiti `MarketBar` table for backtesting. It provides comprehensive validation, deduplication, gap detection, and safe database import with transaction safety.

---

## 2. Supported CSV Format

### Required Columns
| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | String | ISO 8601 timestamp with optional timezone (e.g., `2026-01-05T09:15:00+05:30`) |
| `open` | Float | Opening price (must be positive) |
| `high` | Float | High price (must be ≥ max(open, close)) |
| `low` | Float | Low price (must be ≤ min(open, close)) |
| `close` | Float | Closing price (must be positive) |

### Optional Columns
| Column | Type | Description |
|--------|------|-------------|
| `volume` | Float | Trading volume (must be non-negative, defaults to 0) |

### Example CSV
```csv
timestamp,open,high,low,close,volume
2026-01-05T09:15:00+05:30,24000,24100,23950,24080,120000
2026-01-06T09:15:00+05:30,24080,24200,24000,24150,125000
2026-01-07T09:15:00+05:30,24150,24300,24100,24250,130000
```

---

## 3. Timestamp Formats Supported

| Format | Example |
|--------|---------|
| ISO 8601 with timezone | `2026-01-05T09:15:00+05:30` |
| ISO 8601 UTC (Z suffix) | `2026-01-05T09:15:00Z` |
| ISO 8601 without timezone | `2026-01-05T09:15:00` |
| Space-separated with timezone | `2026-01-05 09:15:00+05:30` |
| Date only | `2026-01-05` |

All timestamps are normalized to timezone-naive UTC for storage in the database (consistent with existing `MarketBar.ts` column).

---

## 4. Validation Rules

| Rule | Behavior |
|------|----------|
| Positive prices | All OHLC values must be > 0 |
| OHLC consistency | `high >= max(open, close)`, `low <= min(open, close)` |
| High >= Low | `high >= low` |
| Non-negative volume | Volume must be ≥ 0 |
| Finite values | No NaN, infinity, or null values |
| Valid timestamp | Must parse as valid datetime |

Invalid rows are rejected and counted in the summary.

---

## 5. Data Quality Features

### Duplicate Detection
- Detects duplicate timestamps in input
- Keeps first occurrence, removes subsequent duplicates
- Reports count of duplicates removed

### Gap Detection

- **Intraday timeframes** (`1m`, `5m`, `15m`, `1h`): Detects missing timestamps based on timeframe frequency. Reports count of missing bars.
- **Daily timeframe** (`1d`): Gap detection is **skipped** because no exchange trading calendar is configured. Without a proper exchange calendar, weekends and exchange holidays cannot be distinguished from actual missing trading bars. The output will include a warning: `"Daily gap detection skipped: no exchange trading calendar configured; weekends/holidays not excluded"`.

### OHLC Validation
- Auto-fixes minor OHLC inconsistencies (reports as warnings)
- Rejects rows with unfixable violations

---

## 6. CLI Usage

```bash
# Dry run validation only
python -m app.cli.import_market_data \
  --file data.csv \
  --symbol ^NSEI \
  --timeframe 1d \
  --dry-run

# Import with skip-on-conflict (default)
python -m app.cli.import_market_data \
  --file data.csv \
  --symbol ^NSEI \
  --timeframe 1d

# Import and update existing records
python -m app.cli.import_market_data \
  --file data.csv \
  --symbol ^NSEI \
  --timeframe 1d \
  --on-conflict update
```

### Options
| Option | Required | Description |
|--------|----------|-------------|
| `--file` | Yes | Path to CSV file |
| `--symbol` | Yes | Trading symbol (e.g., `^NSEI`, `RELIANCE.NS`) |
| `--timeframe` | Yes | One of: `1m`, `5m`, `15m`, `1h`, `1d` |
| `--dry-run` | No | Validate only, no database writes |
| `--on-conflict` | No | `skip` (default) or `update` for existing records |

### Exit Codes
| Code | Meaning |
|------|---------|
| 0 | Success (or success with warnings) |
| 1 | Failed - no valid data to import |

---

## 8. Data Provenance

Imported data is stored with:
- `source`: `"HISTORICAL"` (distinguishes from `YAHOO FINANCE`, `MOCK GENERATOR`)
- `status`: `"HISTORICAL"`
- `label`: `"PAPER/SIMULATED"`

This ensures imported historical data is clearly distinguished from live, delayed, or simulated data.

---

## 9. Dry-Run Mode

```bash
python -m app.cli.import_market_data --file data.csv --symbol ^NSEI --timeframe 1d --dry-run
```

- Reads and validates entire CSV
- Detects duplicates, gaps, OHLC issues
- Checks for existing database records
- Reports what *would* be imported
- **No database connection required**
- Exits with code 0 if valid data exists, 1 if no valid data

---

## 10. Import Summary Output

```
============================================================
IMPORT SUMMARY
============================================================
File:          data.csv
Symbol:        ^NSEI
Timeframe:     1d
Mode:          IMPORT
Conflict:      skip
Status:        HISTORICAL
------------------------------------------------------------
Total rows:    100
Accepted:      98
Rejected:      2
Duplicates:    3
Existing skip: 5
Inserted:      90
------------------------------------------------------------

Validation Issues:
  - Rejected 2 invalid rows
  - Removed 3 duplicate timestamp(s)
  - 5 missing bar(s) detected
```

---

## 11. Tests

Run all tests:
```bash
# Backend tests (including 31 new import tests)
cd backend && source venv/bin/activate && python -m pytest tests/ -v

# Specific import tests
python -m pytest tests/test_import_market_data.py -v

# Frontend tests
cd ../frontend && npm test

# Build
npm run build
```

### Test Coverage
| Category | Tests |
|----------|-------|
| CSVImporter unit tests | 18 |
| Process CSV integration tests | 8 |
| Run import integration tests | 7 |
| ImportResult dataclass tests | 2 |
| **Total new tests** | **31** |

---

## 12. Known Limitations

| Limitation | Workaround |
|------------|------------|
| No Parquet support | Convert to CSV first |
| No exchange holiday calendar | Gap detection includes weekends/holidays |
| No volume for indices | Volume defaults to 0 for `^NSEI`, `^NSEBANK` |
| No automatic timezone conversion | Timestamps normalized to UTC-naive |
| No automatic symbol inference | Symbol must be explicitly provided |
| No batch import | Import one file at a time |

---

## 13. Files Created/Modified

| File | Change |
|------|--------|
| `backend/app/cli/__init__.py` | Created |
| `backend/app/cli/import_market_data.py` | Created (main CLI module) |
| `backend/tests/test_import_market_data.py` | Created (31 tests) |
| `docs/HISTORICAL_DATA_IMPORT.md` | Created (this document) |
| `docs/PHASE3_IMPLEMENTATION.md` | Updated |
| `docs/MARKET_DATA_IMPLEMENTATION.md` | Updated |

---

## 14. Verification Commands

```bash
# Backend tests
cd /Users/smitshrismackbook/Downloads/quantniti/backend
source venv/bin/activate
python -m pytest tests/test_import_market_data.py -v
python -m pytest tests/ -v

# Frontend tests
cd ../frontend
npm test
npm run build

# CLI dry run
python -m app.cli.import_market_data --file data.csv --symbol ^NSEI --timeframe 1d --dry-run
```

---

## 15. Database Integration

**No migration required.** The existing `MarketBar` table and unique constraint (`symbol`, `timeframe`, `ts`) are used. The import uses the existing `_upsert_market_bars` function with proper transaction handling.

---

## 15. Status

| Phase | Status |
|-------|--------|
| **3A: Dashboard Data Quality** | ✅ Complete |
| **3B: Historical CSV Import** | ✅ Complete |
| **3C: Configurable Watchlist** | ⏳ Planned |
| **3D: Cache TTL** | ⏳ Planned |
| **3E: Market Hours** | ⏳ Planned |

---

**All tests pass:**
- Backend: 251 tests (220 existing + 31 new import tests)
- Frontend: 16 tests
- Build: ✅ Successful