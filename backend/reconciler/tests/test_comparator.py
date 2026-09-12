"""
Regression tests for the reconciliation comparator engine.
==========================================================
Each test uses in-memory data and targets the pure-function
comparator directly — no database or HTTP layer involved.
"""

import pytest
from reconciler.services.comparator import (
    reconcile_records,
    normalize_reference,
    safe_parse_decimal,
    DiscrepancyResult,
)
from decimal import Decimal


# ---------------------------------------------------------------------------
# Utility function tests
# ---------------------------------------------------------------------------

class TestNormalizeReference:
    """Tests for the reference normalization function."""

    def test_strips_whitespace(self):
        assert normalize_reference("  REC-001  ") == "rec001"

    def test_removes_dashes(self):
        assert normalize_reference("REC-001") == "rec001"

    def test_removes_underscores(self):
        assert normalize_reference("rec_001") == "rec001"

    def test_lowercases(self):
        assert normalize_reference("REC001") == "rec001"

    def test_handles_empty_string(self):
        assert normalize_reference("") == ""

    def test_handles_none_like(self):
        assert normalize_reference("") == ""

    def test_complex_normalization(self):
        """Different formatting should normalize to the same key."""
        variants = ["REC-001", " rec_001 ", "rec001", " REC 001 ", "REC_001"]
        normalized = [normalize_reference(v) for v in variants]
        assert all(n == "rec001" for n in normalized)


class TestSafeParseDecimal:
    """Tests for the decimal parsing function."""

    def test_plain_number(self):
        assert safe_parse_decimal("100.00") == Decimal("100.00")

    def test_currency_symbol(self):
        assert safe_parse_decimal("$1250.00") == Decimal("1250.00")

    def test_commas(self):
        assert safe_parse_decimal("$1,500.00") == Decimal("1500.00")

    def test_whitespace(self):
        assert safe_parse_decimal("  $120.50  ") == Decimal("120.50")

    def test_na_value(self):
        assert safe_parse_decimal("N/A") is None

    def test_null_value(self):
        assert safe_parse_decimal("NULL") is None

    def test_dash_value(self):
        assert safe_parse_decimal("-") is None

    def test_empty_string(self):
        assert safe_parse_decimal("") is None

    def test_none_value(self):
        assert safe_parse_decimal(None) is None


# ---------------------------------------------------------------------------
# Reconciliation pipeline tests
# ---------------------------------------------------------------------------

LOCATION_MAP = {
    "LOC-1": "ORG-1",
    "LOC-2": "ORG-1",
    "LOC-3": "ORG-2",
    "LOC-4": "ORG-2",
    "LOC-5": "ORG-3",
}


class TestReconcileRecords:
    """Core reconciliation engine tests — one test per discrepancy type."""

    def test_detects_record_missing_in_system_b(self):
        """Records in System A with no counterpart in System B."""
        records_a = [
            {"record_id": "REC-01", "amount": "100", "quantity": "5",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
        ]
        records_b = []

        results = reconcile_records(records_a, records_b, LOCATION_MAP)

        assert len(results) == 1
        assert results[0].reason == "MISSING_IN_SYSTEM_B"
        assert results[0].record_id == "REC-01"
        assert results[0].org_id == "ORG-1"

    def test_detects_orphan_record_in_system_b(self):
        """Records in System B that point to non-existent System A records."""
        records_a = []
        records_b = [
            {"record_ref": "REC-999", "amount": "250", "quantity": "3",
             "status": "pending", "date": "2024-01-01", "location_id": "LOC-3"},
        ]

        results = reconcile_records(records_a, records_b, LOCATION_MAP)

        assert len(results) == 1
        assert results[0].reason == "ORPHAN_IN_SYSTEM_B"
        assert results[0].org_id == "ORG-2"

    def test_detects_duplicate_entries_in_system_b(self):
        """Multiple System B entries referencing the same System A record."""
        records_a = [
            {"record_id": "REC-01", "amount": "100", "quantity": "5",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
        ]
        records_b = [
            {"record_ref": "REC-01", "amount": "100", "quantity": "5",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
            {"record_ref": " rec-01 ", "amount": "100", "quantity": "5",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
        ]

        results = reconcile_records(records_a, records_b, LOCATION_MAP)

        assert any(r.reason == "DUPLICATE_IN_SYSTEM_B" for r in results)

    def test_detects_value_mismatch(self):
        """Matched records with differing payload values."""
        records_a = [
            {"record_id": "REC-01", "amount": "100.00", "quantity": "5",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
        ]
        records_b = [
            {"record_ref": "REC-01", "amount": "120.00", "quantity": "5",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
        ]

        results = reconcile_records(records_a, records_b, LOCATION_MAP)

        assert len(results) == 1
        assert results[0].reason == "VALUE_MISMATCH"
        assert results[0].system_a_value == "100.00"
        assert results[0].system_b_value == "120.00"

    def test_detects_value_mismatch_with_currency_symbols(self):
        """Currency-formatted values should still be compared numerically."""
        records_a = [
            {"record_id": "REC-01", "amount": "$1,500.00", "quantity": "10",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
        ]
        records_b = [
            {"record_ref": "REC-01", "amount": "1500.00", "quantity": "10",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
        ]

        results = reconcile_records(records_a, records_b, LOCATION_MAP)

        # $1,500.00 and 1500.00 should match — no discrepancy
        assert len(results) == 0

    def test_tenant_boundary_isolation(self):
        """Discrepancies are correctly assigned to their owning org."""
        records_a = [
            {"record_id": "REC-01", "amount": "100", "quantity": "5",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
            {"record_id": "REC-02", "amount": "200", "quantity": "10",
             "status": "pending", "date": "2024-01-02", "location_id": "LOC-3"},
        ]
        records_b = []  # Both missing in System B

        results = reconcile_records(records_a, records_b, LOCATION_MAP)

        assert len(results) == 2

        org1_results = [r for r in results if r.org_id == "ORG-1"]
        org2_results = [r for r in results if r.org_id == "ORG-2"]

        # REC-01 at LOC-1 belongs to ORG-1
        assert len(org1_results) == 1
        assert org1_results[0].record_id == "REC-01"

        # REC-02 at LOC-3 belongs to ORG-2
        assert len(org2_results) == 1
        assert org2_results[0].record_id == "REC-02"

    def test_no_discrepancies_for_perfect_match(self):
        """Perfectly matching records should produce zero discrepancies."""
        records_a = [
            {"record_id": "REC-01", "amount": "100.00", "quantity": "5",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
        ]
        records_b = [
            {"record_ref": "REC-01", "amount": "$100.00", "quantity": "5",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
        ]

        results = reconcile_records(records_a, records_b, LOCATION_MAP)

        assert len(results) == 0

    def test_detects_quantity_mismatch(self):
        """Quantity differences should also be flagged."""
        records_a = [
            {"record_id": "REC-01", "amount": "100.00", "quantity": "5",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
        ]
        records_b = [
            {"record_ref": "REC-01", "amount": "100.00", "quantity": "8",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
        ]

        results = reconcile_records(records_a, records_b, LOCATION_MAP)

        assert any(r.reason == "VALUE_MISMATCH" and r.field_name == "quantity" for r in results)

    def test_detects_status_mismatch(self):
        """Status differences should be flagged."""
        records_a = [
            {"record_id": "REC-01", "amount": "100.00", "quantity": "5",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
        ]
        records_b = [
            {"record_ref": "REC-01", "amount": "100.00", "quantity": "5",
             "status": "pending", "date": "2024-01-01", "location_id": "LOC-1"},
        ]

        results = reconcile_records(records_a, records_b, LOCATION_MAP)

        assert any(r.reason == "VALUE_MISMATCH" and r.field_name == "status" for r in results)

    def test_mixed_discrepancies(self):
        """Multiple discrepancy types in a single reconciliation run."""
        records_a = [
            {"record_id": "REC-01", "amount": "100", "quantity": "5",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
            {"record_id": "REC-02", "amount": "200", "quantity": "10",
             "status": "pending", "date": "2024-01-02", "location_id": "LOC-3"},
            {"record_id": "REC-03", "amount": "300", "quantity": "15",
             "status": "completed", "date": "2024-01-03", "location_id": "LOC-5"},
        ]
        records_b = [
            # REC-01: value mismatch
            {"record_ref": "REC-01", "amount": "150", "quantity": "5",
             "status": "completed", "date": "2024-01-01", "location_id": "LOC-1"},
            # REC-02: missing — not present
            # REC-03: duplicate
            {"record_ref": "REC-03", "amount": "300", "quantity": "15",
             "status": "completed", "date": "2024-01-03", "location_id": "LOC-5"},
            {"record_ref": "rec_03", "amount": "300", "quantity": "15",
             "status": "completed", "date": "2024-01-03", "location_id": "LOC-5"},
            # Orphan
            {"record_ref": "REC-999", "amount": "500", "quantity": "1",
             "status": "completed", "date": "2024-01-04", "location_id": "LOC-1"},
        ]

        results = reconcile_records(records_a, records_b, LOCATION_MAP)

        reasons = {r.reason for r in results}
        assert "VALUE_MISMATCH" in reasons
        assert "MISSING_IN_SYSTEM_B" in reasons
        assert "DUPLICATE_IN_SYSTEM_B" in reasons
        assert "ORPHAN_IN_SYSTEM_B" in reasons
