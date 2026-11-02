"""Tests for the historical market data import CLI."""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.cli.import_market_data import (
    CSVImporter,
    run_import,
    ImportResult,
    VALID_TIMEFRAMES,
    REQUIRED_COLUMNS,
)


class TestCSVImporter:
    """Tests for the CSVImporter class."""
    
    @pytest.fixture
    def valid_csv_content(self):
        """Create a valid CSV content for testing."""
        return """timestamp,open,high,low,close,volume
2026-01-05T09:15:00+05:30,24000,24100,23950,24080,120000
2026-01-06T09:15:00+05:30,24080,24200,24000,24150,125000
2026-01-07T09:15:00+05:30,24150,24300,24100,24250,130000"""
    
    @pytest.fixture
    def csv_file(self, valid_csv_content):
        """Create a temporary CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(valid_csv_content)
            f.flush()
            yield f.name
        os.unlink(f.name)
    
    def test_importer_initialization(self):
        """Test importer initialization with valid parameters."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        assert importer.symbol == "^NSEI"
        assert importer.timeframe == "1d"
        assert importer.dry_run is True
        assert importer.on_conflict == "skip"
        assert importer.db is None
    
    def test_importer_invalid_timeframe(self):
        """Test importer rejects invalid timeframe."""
        with pytest.raises(ValueError, match="Invalid timeframe"):
            CSVImporter("^NSEI", "invalid", dry_run=True)
    
    def test_validate_csv_structure_valid(self, csv_file):
        """Test CSV structure validation with valid file."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        header, optional = importer.validate_csv_structure(csv_file)
        assert "timestamp" in header
        assert "open" in header
        assert "high" in header
        assert "low" in header
        assert "close" in header
        assert "volume" in header
    
    def test_validate_csv_structure_missing_columns(self):
        """Test CSV structure validation with missing required columns."""
        content = """timestamp,open,high,low
2026-01-05T09:15:00+05:30,24000,24100,23950"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            fname = f.name
        
        try:
            importer = CSVImporter("^NSEI", "1d", dry_run=True)
            with pytest.raises(ValueError, match="Missing required columns"):
                importer.validate_csv_structure(fname)
        finally:
            os.unlink(fname)
    
    def test_parse_timestamp_iso_with_tz(self):
        """Test parsing ISO timestamp with timezone."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        ts = importer.parse_timestamp("2026-01-05T09:15:00+05:30")
        assert isinstance(ts, datetime)
        assert ts.year == 2026
        assert ts.month == 1
        assert ts.day == 5
        assert ts.hour == 9
        assert ts.minute == 15
    
    def test_parse_timestamp_iso_utc(self):
        """Test parsing ISO timestamp with Z suffix."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        ts = importer.parse_timestamp("2026-01-05T09:15:00Z")
        assert isinstance(ts, datetime)
        assert ts.hour == 9
    
    def test_parse_timestamp_no_tz(self):
        """Test parsing timestamp without timezone."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        ts = importer.parse_timestamp("2026-01-05 09:15:00")
        assert isinstance(ts, datetime)
        assert ts.hour == 9
    
    def test_parse_timestamp_date_only(self):
        """Test parsing date only."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        ts = importer.parse_timestamp("2026-01-05")
        assert isinstance(ts, datetime)
        assert ts.hour == 0
        assert ts.minute == 0
    
    def test_parse_timestamp_invalid(self):
        """Test parsing invalid timestamp raises error."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        with pytest.raises(ValueError, match="Unable to parse timestamp"):
            importer.parse_timestamp("invalid-timestamp")
    
    def test_validate_row_valid(self):
        """Test validating a valid row."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        row = {
            "timestamp": "2026-01-05T09:15:00+05:30",
            "open": "24000",
            "high": "24100",
            "low": "23950",
            "close": "24080",
            "volume": "120000"
        }
        validated, errors = importer.validate_row(row, 1)
        assert validated is not None
        assert errors == []
        assert validated["open"] == 24000.0
        assert validated["high"] == 24100.0
        assert validated["low"] == 23950.0
        assert validated["close"] == 24080.0
        assert validated["volume"] == 120000.0
    
    def test_validate_row_missing_volume(self):
        """Test validating row without volume (optional)."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        row = {
            "timestamp": "2026-01-05T09:15:00+05:30",
            "open": "24000",
            "high": "24100",
            "low": "23950",
            "close": "24080"
        }
        validated, errors = importer.validate_row(row, 1)
        assert validated is not None
        assert errors == []
        assert validated["volume"] == 0.0
    
    def test_validate_row_invalid_timestamp(self):
        """Test rejecting row with invalid timestamp."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        row = {
            "timestamp": "invalid",
            "open": "24000",
            "high": "24100",
            "low": "23950",
            "close": "24080"
        }
        validated, errors = importer.validate_row(row, 1)
        assert validated is None
        assert len(errors) > 0
        assert any("Invalid timestamp" in e for e in errors)
    
    def test_validate_row_negative_price(self):
        """Test rejecting row with negative price."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        row = {
            "timestamp": "2026-01-05T09:15:00+05:30",
            "open": "-24000",
            "high": "24100",
            "low": "23950",
            "close": "24080"
        }
        validated, errors = importer.validate_row(row, 1)
        assert validated is None
        assert any("positive" in e for e in errors)
    
    def test_validate_row_invalid_ohlc_high_low(self):
        """Test rejecting row with high < low."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        row = {
            "timestamp": "2026-01-05T09:15:00+05:30",
            "open": "24000",
            "high": "23900",  # high < low
            "low": "24000",
            "close": "24080"
        }
        validated, errors = importer.validate_row(row, 1)
        assert validated is None
        assert any("high" in e and "low" in e for e in errors)
    
    def test_validate_row_high_less_than_close(self):
        """Test rejecting row with high < close."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        row = {
            "timestamp": "2026-01-05T09:15:00+05:30",
            "open": "24000",
            "high": "24050",  # high < close
            "low": "23950",
            "close": "24080"
        }
        validated, errors = importer.validate_row(row, 1)
        assert validated is None
        assert any("high" in e and "close" in e for e in errors)
    
    def test_validate_row_negative_volume(self):
        """Test rejecting row with negative volume."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        row = {
            "timestamp": "2026-01-05T09:15:00+05:30",
            "open": "24000",
            "high": "24100",
            "low": "23950",
            "close": "24080",
            "volume": "-1000"
        }
        validated, errors = importer.validate_row(row, 1)
        assert validated is None
        assert any("negative" in e.lower() for e in errors)
    
    def test_validate_row_nan_values(self):
        """Test rejecting row with NaN values."""
        importer = CSVImporter("^NSEI", "1d", dry_run=True)
        row = {
            "timestamp": "2026-01-05T09:15:00+05:30",
            "open": "nan",
            "high": "24100",
            "low": "23950",
            "close": "24080"
        }
        validated, errors = importer.validate_row(row, 1)
        assert validated is None
        assert any("finite" in e.lower() for e in errors)


class TestProcessCSV:
    """Tests for the process_csv method."""
    
    @pytest.fixture
    def valid_csv_file(self):
        content = """timestamp,open,high,low,close,volume
2026-01-05T09:15:00+05:30,24000,24100,23950,24080,120000
2026-01-06T09:15:00+05:30,24080,24200,24000,24150,125000
2026-01-07T09:15:00+05:30,24150,24300,24100,24250,130000"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            yield f.name
        os.unlink(f.name)
    
    def test_process_csv_valid(self):
        """Test processing valid CSV file."""
        content = """timestamp,open,high,low,close,volume
2026-01-05T09:15:00+05:30,24000,24100,23950,24080,120000
2026-01-06T09:15:00+05:30,24080,24200,24000,24150,125000"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            fname = f.name
        
        try:
            importer = CSVImporter("^NSEI", "1d", dry_run=True)
            df, errors, stats = importer.process_csv(fname)
            
            assert len(df) == 2
            assert stats["valid"] == 2
            assert stats["rejected"] == 0
            assert len(errors) == 1
            assert "Daily gap detection skipped" in errors[0]
            assert "open" in df.columns
            assert "high" in df.columns
            assert "low" in df.columns
            assert "close" in df.columns
            assert "volume" in df.columns
            assert isinstance(df.index, pd.DatetimeIndex)
            # Should be sorted
            assert df.index.is_monotonic_increasing
        finally:
            os.unlink(fname)
    
    def test_process_csv_with_duplicates(self):
        """Test CSV with duplicate timestamps gets deduplicated."""
        content = """timestamp,open,high,low,close,volume
2026-01-05T09:15:00+05:30,24000,24100,23950,24080,120000
2026-01-05T09:15:00+05:30,24050,24150,24000,24100,125000
2026-01-06T09:15:00+05:30,24080,24200,24000,24150,125000"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            fname = f.name
        
        try:
            importer = CSVImporter("^NSEI", "1d", dry_run=True)
            df, errors, stats = importer.process_csv(fname)
            
            assert len(df) == 2  # Duplicate removed
            assert stats["duplicates_removed"] == 2  # Both duplicate rows counted
            assert any("duplicate" in e.lower() for e in errors)
        finally:
            os.unlink(fname)
    
    def test_process_csv_unsorted(self):
        """Test that CSV gets sorted chronologically."""
        content = """timestamp,open,high,low,close,volume
2026-01-07T09:15:00+05:30,24150,24300,24100,24250,130000
2026-01-05T09:15:00+05:30,24000,24100,23950,24080,120000
2026-01-06T09:15:00+05:30,24080,24200,24000,24150,125000"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            fname = f.name
        
        try:
            importer = CSVImporter("^NSEI", "1d", dry_run=True)
            df, errors, stats = importer.process_csv(fname)
            
            assert df.index.is_monotonic_increasing
            assert df.index[0] < df.index[1] < df.index[2]
        finally:
            os.unlink(fname)
    
    def test_process_csv_gap_detection(self):
        """Test gap detection in time series for intraday timeframes."""
        # Use 1h timeframe to test gap detection (daily skips gap detection)
        content = """timestamp,open,high,low,close,volume
2026-01-05T09:15:00+05:30,24000,24100,23950,24080,120000
2026-01-05T11:15:00+05:30,24150,24300,24100,24250,130000"""  # Missing 10:15 bar
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            fname = f.name
        
        try:
            importer = CSVImporter("^NSEI", "1h", dry_run=True)
            df, errors, stats = importer.process_csv(fname)
            
            assert len(df) == 2
            # Gap should be detected for intraday timeframe
            gap_errors = [e for e in errors if "missing" in e.lower()]
            assert len(gap_errors) > 0
        finally:
            os.unlink(fname)
    
    def test_process_csv_invalid_rows_rejected(self):
        """Test that invalid rows are rejected and counted."""
        content = """timestamp,open,high,low,close,volume
2026-01-05T09:15:00+05:30,24000,24100,23950,24080,120000
invalid_timestamp,24000,24100,23950,24080,125000
2026-01-06T09:15:00+05:30,24080,24200,24000,24150,125000"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            fname = f.name
        
        try:
            importer = CSVImporter("^NSEI", "1d", dry_run=True)
            df, errors, stats = importer.process_csv(fname)
            
            assert len(df) == 2
            assert stats["rejected"] == 1
            assert stats["valid"] == 2
            assert stats["total"] == 3
            assert len(errors) > 0
        finally:
            os.unlink(fname)
    
    def test_process_csv_empty_file(self):
        """Test processing empty CSV file."""
        content = """timestamp,open,high,low,close,volume"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            fname = f.name
        
        try:
            importer = CSVImporter("^NSEI", "1d", dry_run=True)
            df, errors, stats = importer.process_csv(fname)
            
            assert len(df) == 0
            assert stats["valid"] == 0
            assert stats["total"] == 0
        finally:
            os.unlink(fname)


class TestRunImport:
    """Tests for the main run_import function."""
    
    def test_run_import_file_not_found(self):
        """Test import with non-existent file."""
        result = run_import("/nonexistent/file.csv", "^NSEI", "1d", dry_run=True)
        assert result.accepted_rows == 0
        assert any("not found" in e.lower() for e in result.validation_errors)
    
    def test_run_import_invalid_timeframe(self):
        """Test import with invalid timeframe."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("timestamp,open,high,low,close\n2026-01-05,100,101,99,100")
            f.flush()
            fname = f.name
        
        try:
            result = run_import(fname, "^NSEI", "invalid", dry_run=True)
            assert result.accepted_rows == 0
            assert any("invalid timeframe" in e.lower() for e in result.validation_errors)
        finally:
            os.unlink(fname)
    
    def test_run_import_dry_run(self):
        """Test dry-run mode doesn't require database."""
        content = """timestamp,open,high,low,close,volume
2026-01-05T09:15:00+05:30,24000,24100,23950,24080,120000
2026-01-06T09:15:00+05:30,24080,24200,24000,24150,125000"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            fname = f.name
        
        try:
            result = run_import(fname, "^NSEI", "1d", dry_run=True)
            assert result.dry_run is True
            assert result.accepted_rows == 2
            assert result.inserted == 2  # In dry run, all valid rows count as inserted
        finally:
            os.unlink(fname)
    
    def test_run_import_on_conflict_update(self):
        """Test on-conflict update option."""
        content = """timestamp,open,high,low,close,volume
2026-01-05T09:15:00+05:30,24000,24100,23950,24080,120000"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            fname = f.name
        
        try:
            # Test with update conflict resolution
            result = run_import(fname, "^NSEI", "1d", dry_run=True, on_conflict="update")
            assert result.accepted_rows == 1
        finally:
            os.unlink(fname)
    
    def test_run_import_missing_required_columns(self):
        """Test import with missing required columns."""
        content = """timestamp,open,high,low\n2026-01-05T09:15:00+05:30,24000,24100,23950"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            fname = f.name
        
        try:
            result = run_import(fname, "^NSEI", "1d", dry_run=True)
            assert result.accepted_rows == 0
            assert any("missing required" in e.lower() for e in result.validation_errors)
        finally:
            os.unlink(fname)
    
    def test_run_import_empty_file(self):
        """Test import with empty file (header only)."""
        content = "timestamp,open,high,low,close,volume"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            fname = f.name
        
        try:
            result = run_import(fname, "^NSEI", "1d", dry_run=True)
            assert result.accepted_rows == 0
            assert result.total_rows == 0
        finally:
            os.unlink(fname)


class TestImportResult:
    """Tests for the ImportResult dataclass."""
    
    def test_default_values(self):
        result = ImportResult()
        assert result.total_rows == 0
        assert result.accepted_rows == 0
        assert result.rejected_rows == 0
        assert result.duplicate_timestamps == 0
        assert result.existing_skipped == 0
        assert result.inserted == 0
        assert result.validation_errors == []
        assert result.dry_run is False
    
    def test_custom_values(self):
        result = ImportResult(
            total_rows=100,
            accepted_rows=95,
            rejected_rows=5,
            validation_errors=["Error 1", "Error 2"],
            dry_run=True
        )
        assert result.total_rows == 100
        assert result.accepted_rows == 95
        assert result.rejected_rows == 5
        assert len(result.validation_errors) == 2
        assert result.dry_run is True


# Integration test with actual database (requires running PostgreSQL)
class TestDatabaseIntegration:
    """Integration tests that require a running database."""
    
    @pytest.mark.integration
    def test_import_with_database(self):
        """Test actual database import (requires running PostgreSQL)."""
        pytest.skip("Requires running PostgreSQL - run manually")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])