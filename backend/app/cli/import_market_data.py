#!/usr/bin/env python3
"""
QuantNiti Historical Market Data Import CLI

Imports historical OHLCV data from CSV files into the MarketBar table for backtesting.

Usage:
    python -m app.cli.import_market_data --file data.csv --symbol ^NSEI --timeframe 1d [--dry-run]

CSV Format:
    timestamp,open,high,low,close,volume
    2026-01-05T09:15:00+05:30,24000,24100,23950,24080,120000

The script validates all data before import and provides a detailed summary.
"""

import argparse
import csv
import sys
import os
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models import MarketBar
from app.db import SessionLocal, engine
from app.services.market import (
    _validate_ohlc, 
    _detect_gaps_duplicates, 
    FREQ,
    _upsert_market_bars
)

# Supported timeframes
VALID_TIMEFRAMES = ["1m", "5m", "15m", "1h", "1d"]
REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close"]
OPTIONAL_COLUMNS = ["volume"]


@dataclass
class ImportResult:
    """Result of an import operation."""
    total_rows: int = 0
    accepted_rows: int = 0
    rejected_rows: int = 0
    duplicate_timestamps: int = 0
    existing_skipped: int = 0
    inserted: int = 0
    validation_errors: List[str] = None
    dry_run: bool = False
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []


class CSVImporter:
    """Handles CSV import validation and database insertion."""
    
    def __init__(self, symbol: str, timeframe: str, dry_run: bool = False, on_conflict: str = "skip"):
        """
        Initialize the importer.
        
        Args:
            symbol: Trading symbol (e.g., ^NSEI, BTC-USD)
            timeframe: Timeframe (1m, 5m, 15m, 1h, 1d)
            dry_run: If True, validate only without writing to DB
            on_conflict: How to handle existing records - "skip" or "update"
        """
        if timeframe not in VALID_TIMEFRAMES:
            raise ValueError(f"Invalid timeframe: {timeframe}. Must be one of {VALID_TIMEFRAMES}")
        
        self.symbol = symbol.upper().replace("/", "-")
        self.timeframe = timeframe
        self.dry_run = dry_run
        self.on_conflict = on_conflict
        self.db = None
        
        if not dry_run:
            self.db = SessionLocal()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            if exc_type:
                self.db.rollback()
            else:
                self.db.commit()
            self.db.close()
    
    def validate_csv_structure(self, file_path: str) -> Tuple[List[str], List[str]]:
        """Validate CSV file structure and return (required_columns, optional_columns)."""
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            
        if not header:
            raise ValueError("CSV file is empty or has no header")
        
        header = [col.strip().lower() for col in header]
        
        missing_required = [col for col in REQUIRED_COLUMNS if col not in header]
        if missing_required:
            raise ValueError(f"Missing required columns: {missing_required}. Required: {REQUIRED_COLUMNS}")
        
        return header, [col for col in OPTIONAL_COLUMNS if col in header]
    
    def parse_timestamp(self, ts_str: str) -> datetime:
        """Parse timestamp string with timezone support."""
        ts_str = ts_str.strip()
        
        # Try parsing with timezone first
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except ValueError:
            pass
        
        # Try common formats
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse timestamp: {ts_str}")
    
    def validate_row(self, row: Dict[str, str], row_num: int) -> Tuple[Optional[Dict], List[str]]:
        """
        Validate a single CSV row.
        Returns (validated_data, errors_list). If errors, validated_data is None.
        """
        errors = []
        data = {}
        
        # Parse timestamp
        try:
            data['ts'] = self.parse_timestamp(row['timestamp'])
        except ValueError as e:
            errors.append(f"Row {row_num}: Invalid timestamp '{row['timestamp']}': {e}")
            return None, errors
        
        # Parse numeric fields
        for field in ['open', 'high', 'low', 'close']:
            try:
                value = float(row[field])
                if not np.isfinite(value):
                    errors.append(f"Row {row_num}: {field} is not finite: {row[field]}")
                    return None, [f"Row {row_num}: {field} is not finite"]
                if value <= 0:
                    errors.append(f"Row {row_num}: {field} must be positive, got {value}")
                    return None, [f"Row {row_num}: {field} must be positive"]
                data[field] = value
            except ValueError:
                errors.append(f"Row {row_num}: Invalid {field} value: {row[field]}")
                return None, errors
        
        # Validate OHLC relationships
        if not (data['high'] >= max(data['open'], data['close']) - 1e-8):
            errors.append(f"Row {row_num}: high ({data['high']}) < max(open={data['open']}, close={data['close']})")
        
        if not (data['low'] <= min(data['open'], data['close']) + 1e-8):
            errors.append(f"Row {row_num}: low ({data['low']}) > min(open={data['open']}, close={data['close']})")
        
        if data['high'] < data['low'] - 1e-8:
            errors.append(f"Row {row_num}: high ({data['high']}) < low ({data['low']})")
        
        # Volume (optional)
        if 'volume' in row:
            try:
                vol = float(row.get('volume', 0))
                if vol < 0:
                    errors.append(f"Row {row_num}: volume cannot be negative: {vol}")
                data['volume'] = max(0.0, vol)
            except ValueError:
                data['volume'] = 0.0
        else:
            data['volume'] = 0.0
        
        if errors:
            return None, errors
        
        return data, []
    
    def process_csv(self, file_path: str) -> Tuple[pd.DataFrame, List[str], Dict]:
        """
        Process and validate entire CSV file.
        Returns (validated_dataframe, validation_errors, stats_dict)
        """
        # Validate structure
        header, optional_cols = self.validate_csv_structure(file_path)
        has_volume = 'volume' in optional_cols
        
        # Read all rows
        rows = []
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        
        total_rows = len(rows)
        if total_rows == 0:
            return pd.DataFrame(), ["CSV file has no data rows"], {"total": 0, "valid": 0, "rejected": 0}
        
        # Validate each row
        valid_data = []
        validation_errors = []
        rejected_count = 0
        
        for i, row in enumerate(rows, start=1):
            validated, errors = self.validate_row(row, i)
            if validated:
                valid_data.append(validated)
            else:
                rejected_count += 1
                validation_errors.extend(errors)
        
        if not valid_data:
            return pd.DataFrame(), validation_errors, {"total": total_rows, "valid": 0, "rejected": rejected_count}
        
        # Create DataFrame
        df = pd.DataFrame(valid_data)
        df = df.set_index('ts')
        df = df.sort_index()
        
        # Check for duplicates in input
        dup_mask = df.index.duplicated(keep=False)
        duplicate_count = int(dup_mask.sum())
        
        if duplicate_count > 0:
            # Keep first occurrence
            df = df[~df.index.duplicated(keep='first')]
        
        # Detect gaps
        gaps, duplicates = [], []
        if len(df) >= 2:
            # For daily timeframe (1d), skip gap detection because we lack an exchange trading calendar.
            # Without a proper exchange calendar, we cannot distinguish weekends/holidays from actual gaps.
            # For intraday timeframes (1m, 5m, 15m, 1h), gap detection uses calendar frequency.
            if self.timeframe == "1d":
                gaps.append("Daily gap detection skipped: no exchange trading calendar configured; weekends/holidays not excluded")
            else:
                expected_freq = FREQ.get(self.timeframe)
                if expected_freq:
                    try:
                        expected_range = pd.date_range(start=df.index[0], end=df.index[-1], freq=expected_freq)
                        missing = expected_range.difference(df.index)
                        if len(missing) > 0:
                            gaps.append(f"{len(missing)} missing bar(s) detected (expected {len(expected_range)}, got {len(df)})")
                    except Exception:
                        pass
        
        # Check for remaining duplicates after deduplication
        remaining_dups = int(df.index.duplicated(keep=False).sum())
        if remaining_dups > 0:
            duplicates.append(f"{remaining_dups} duplicate timestamp(s) found after deduplication")
        
        stats = {
            "total": total_rows,
            "valid": len(df),
            "rejected": rejected_count,
            "duplicates_removed": duplicate_count,
        }
        
        all_errors = []
        if stats["rejected"] > 0:
            all_errors.append(f"Rejected {stats['rejected']} invalid rows")
        if stats["duplicates_removed"] > 0:
            all_errors.append(f"Removed {stats['duplicates_removed']} duplicate timestamp(s)")
        if gaps:
            all_errors.extend(gaps)
        
        return df, all_errors, stats
    
    def check_existing_records(self, df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
        """Check for existing records in database. Returns (existing_count, new_records_df)."""
        if self.db is None:
            return 0, df
        
        existing_count = 0
        new_records = []
        
        for ts, row in df.iterrows():
            existing = self.db.query(MarketBar).filter(
                MarketBar.symbol == self.symbol,
                MarketBar.timeframe == self.timeframe,
                MarketBar.ts == ts
            ).first()
            
            if existing:
                existing_count += 1
            else:
                new_records.append((ts, row))
        
        if new_records:
            new_df = pd.DataFrame([r[1] for r in new_records], index=[r[0] for r in new_records])
        else:
            new_df = pd.DataFrame()
        
        return existing_count, new_df
    
    def import_data(self, df: pd.DataFrame, source: str = "HISTORICAL") -> Tuple[int, int]:
        """
        Insert new records into database.
        Returns (inserted_count, skipped_count)
        """
        if self.db is None:
            return 0, 0
        
        inserted = 0
        skipped = 0
        
        for ts, row in df.iterrows():
            existing = self.db.query(MarketBar).filter(
                MarketBar.symbol == self.symbol,
                MarketBar.timeframe == self.timeframe,
                MarketBar.ts == ts
            ).first()
            
            if existing:
                if self.on_conflict == "update":
                    existing.open = float(row["open"])
                    existing.high = float(row["high"])
                    existing.low = float(row["low"])
                    existing.close = float(row["close"])
                    existing.volume = float(row["volume"]) if pd.notna(row["volume"]) else 0.0
                    existing.source = "HISTORICAL"
                skipped += 1
            else:
                bar = MarketBar(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    ts=ts,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]) if pd.notna(row["volume"]) else 0.0,
                    source="HISTORICAL"
                )
                self.db.add(bar)
                inserted += 1
        
        return inserted, skipped


def run_import(
    file_path: str,
    symbol: str,
    timeframe: str,
    dry_run: bool = False,
    on_conflict: str = "skip"
) -> ImportResult:
    """
    Main import function.
    
    Args:
        file_path: Path to CSV file
        symbol: Trading symbol (e.g., ^NSEI)
        timeframe: Timeframe (1m, 5m, 15m, 1h, 1d)
        dry_run: If True, validate only
        on_conflict: "skip" or "update" for existing records
    
    Returns:
        ImportResult with summary statistics
    """
    result = ImportResult(dry_run=dry_run)
    
    # Validate file exists
    file_path = Path(file_path)
    if not file_path.exists():
        result.validation_errors.append(f"File not found: {file_path}")
        return result
    
    # Validate timeframe
    if timeframe not in VALID_TIMEFRAMES:
        result.validation_errors.append(f"Invalid timeframe: {timeframe}. Must be one of {VALID_TIMEFRAMES}")
        return result
    
    with CSVImporter(symbol, timeframe, dry_run=dry_run, on_conflict=on_conflict) as importer:
        try:
            # Process and validate CSV
            df, validation_errors, stats = importer.process_csv(str(file_path))
        except ValueError as e:
            result.validation_errors.append(str(e))
            return result
        
        result.total_rows = stats["total"]
        result.accepted_rows = stats["valid"]
        result.rejected_rows = stats["rejected"]
        result.duplicate_timestamps = stats.get("duplicates_removed", 0)
        result.validation_errors.extend(validation_errors)
        
        if stats["valid"] == 0:
            result.validation_errors.append("No valid rows to import")
            return result
        
        # Check existing records
        if not importer.dry_run:
            existing_count, new_df = importer.check_existing_records(df)
            result.existing_skipped = existing_count
            
            if len(new_df) == 0:
                result.validation_errors.append("All records already exist in database (use --on-conflict update to overwrite)")
                return result
            
            # Import new records
            inserted, skipped = importer.import_data(new_df, "HISTORICAL")
            result.inserted = inserted
            result.existing_skipped += skipped
        else:
            # Dry run - just report what would be imported
            if not importer.dry_run:
                existing_count, new_df = importer.check_existing_records(df)
                result.existing_skipped = existing_count
                result.inserted = len(df) - existing_count
            else:
                result.inserted = stats["valid"]
        
        return result


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Import historical market data from CSV into QuantNiti",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run validation only
  python -m app.cli.import_market_data --file data.csv --symbol ^NSEI --timeframe 1d --dry-run

  # Import with skip-on-conflict (default)
  python -m app.cli.import_market_data --file data.csv --symbol ^NSEI --timeframe 1d

  # Import and update existing records
  python -m app.cli.import_market_data --file data.csv --symbol ^NSEI --timeframe 1d --on-conflict update

CSV Format:
  timestamp,open,high,low,close,volume
  2026-01-05T09:15:00+05:30,24000,24100,23950,24080,120000
  2026-01-06T09:15:00+05:30,24080,24200,24000,24150,125000

Supported timeframes: 1m, 5m, 15m, 1h, 1d
        """
    )
    
    parser.add_argument("--file", required=True, help="Path to CSV file")
    parser.add_argument("--symbol", required=True, help="Trading symbol (e.g., ^NSEI, BTC-USD)")
    parser.add_argument("--timeframe", required=True, choices=VALID_TIMEFRAMES, help="Timeframe")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, no database writes")
    parser.add_argument("--on-conflict", choices=["skip", "update"], default="skip", 
                        help="How to handle existing records (default: skip)")
    
    args = parser.parse_args()
    
    # Run import
    result = run_import(
        file_path=args.file,
        symbol=args.symbol,
        timeframe=args.timeframe,
        dry_run=args.dry_run,
        on_conflict=args.on_conflict
    )
    
    # Print summary
    print("\n" + "="*60)
    print("IMPORT SUMMARY")
    print("="*60)
    print(f"File:          {args.file}")
    print(f"Symbol:        {args.symbol}")
    print(f"Timeframe:     {args.timeframe}")
    print(f"Mode:          {'DRY RUN' if args.dry_run else 'IMPORT'}")
    print(f"Conflict:      {args.on_conflict}")
    print(f"Status:        {'DRY RUN' if args.dry_run else ('HISTORICAL' if not args.dry_run else 'N/A')}")
    print("-"*60)
    print(f"Total rows:    {result.total_rows}")
    print(f"Accepted:      {result.accepted_rows}")
    print(f"Rejected:      {result.rejected_rows}")
    print(f"Duplicates:    {result.duplicate_timestamps}")
    print(f"Existing skip: {result.existing_skipped}")
    print(f"Inserted:      {result.inserted}")
    print("-"*60)
    
    if result.validation_errors:
        print("\nValidation Issues:")
        for error in result.validation_errors:
            print(f"  - {error}")
    
    # Exit code
    if result.validation_errors and result.accepted_rows == 0:
        print("\n❌ Import failed: No valid data to import")
        sys.exit(1)
    elif result.validation_errors:
        print("\n⚠️  Import completed with warnings")
        sys.exit(0)
    else:
        print("\n✅ Import successful")
        sys.exit(0)


if __name__ == "__main__":
    main()