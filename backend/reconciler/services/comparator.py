"""
Core Reconciliation Engine
==========================
Pure-function comparison logic decoupled from Django ORM.
Operates on plain dicts/lists for easy unit testing.

Four-pass reconciliation pipeline:
  1. Duplicate detection in System B
  2. Missing in System B (exists in A, absent in B)
  3. Orphan in System B (exists in B, absent in A)
  4. Value mismatch between matched pairs
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class DiscrepancyResult:
    """Represents a single discrepancy found during reconciliation."""
    reason: str
    record_id: str
    location_id: str
    org_id: str
    system_a_value: Optional[str] = None
    system_b_value: Optional[str] = None
    field_name: str = ''
    details: str = ''


# ---------------------------------------------------------------------------
# Normalization Utilities
# ---------------------------------------------------------------------------

def normalize_reference(ref_string: str) -> str:
    """
    Strips whitespace, dashes, underscores, and standardizes reference IDs
    to a canonical lowercase alphanumeric form.

    Examples:
        " REC-0145 "  -> "rec0145"
        "rec_001"     -> "rec001"
        "REC001"      -> "rec001"
        " rec-001 "   -> "rec001"
    """
    if not ref_string:
        return ""
    return re.sub(r"[^a-zA-Z0-9]", "", ref_string.strip()).lower()


def safe_parse_decimal(value_str: str) -> Optional[Decimal]:
    """
    Parses numeric strings while tolerating currency symbols ($),
    commas, whitespace, and sentinel values (N/A, NULL, NONE, -).

    Returns None for unparseable or sentinel values.
    """
    if not value_str:
        return None

    cleaned = value_str.strip().upper()
    if cleaned in {"N/A", "NULL", "NONE", "-", ""}:
        return None

    # Strip currency symbols, spaces, and commas - keep digits, dots, minus
    numeric_str = re.sub(r"[^\d.\-]", "", value_str.strip())
    if not numeric_str:
        return None

    try:
        return Decimal(numeric_str)
    except (InvalidOperation, ValueError):
        return None


# ---------------------------------------------------------------------------
# Core Reconciliation Pipeline
# ---------------------------------------------------------------------------

def reconcile_records(
    records_a: list,
    records_b: list,
    location_org_map: dict,
) -> List[DiscrepancyResult]:
    """
    Runs the four-pass reconciliation pipeline.

    Args:
        records_a: List of dicts from System A, each with at minimum:
                   'record_id', 'location_id', 'amount', 'quantity', 'status', 'date'
        records_b: List of dicts from System B, each with at minimum:
                   'record_ref', 'location_id', 'amount', 'quantity', 'status', 'date'
        location_org_map: Dict mapping location_id -> org_id

    Returns:
        List of DiscrepancyResult instances describing all found discrepancies.
    """
    discrepancies: List[DiscrepancyResult] = []

    # Build System A lookup by normalized ID
    a_by_norm_id = {}
    for a in records_a:
        norm_id = normalize_reference(a.get("record_id", ""))
        if norm_id:
            a_by_norm_id[norm_id] = a

    # Build System B groups by normalized reference
    b_by_ref = defaultdict(list)
    for b in records_b:
        norm_ref = normalize_reference(b.get("record_ref", ""))
        if norm_ref:
            b_by_ref[norm_ref].append(b)

    matched_b_refs = set()

    # ------------------------------------------------------------------
    # Pass 1: Duplicate detection in System B
    # ------------------------------------------------------------------
    for norm_ref, b_entries in b_by_ref.items():
        if len(b_entries) > 1:
            # Determine org from location (use first entry's location)
            loc_id = b_entries[0].get("location_id", "")
            org_id = location_org_map.get(loc_id, "UNKNOWN")

            # Also check if there's a matching System A record for context
            a_record = a_by_norm_id.get(norm_ref)
            val_a = str(a_record.get("amount", "")) if a_record else None

            discrepancies.append(DiscrepancyResult(
                reason="DUPLICATE_IN_SYSTEM_B",
                record_id=a_record["record_id"] if a_record else b_entries[0].get("record_ref", norm_ref),
                location_id=loc_id,
                org_id=org_id,
                system_a_value=val_a,
                system_b_value="; ".join(
                    f'{e.get("record_ref", "").strip()}={e.get("amount", "")}'
                    for e in b_entries
                ),
                field_name="amount",
                details=f"System B has {len(b_entries)} entries for this record reference",
            ))
            matched_b_refs.add(norm_ref)

    # ------------------------------------------------------------------
    # Pass 2: Missing in System B
    # ------------------------------------------------------------------
    for a in records_a:
        norm_id = normalize_reference(a.get("record_id", ""))
        if not norm_id:
            continue

        b_entries = b_by_ref.get(norm_id, [])
        org_id = location_org_map.get(a.get("location_id", ""), "UNKNOWN")

        if not b_entries:
            discrepancies.append(DiscrepancyResult(
                reason="MISSING_IN_SYSTEM_B",
                record_id=a["record_id"],
                location_id=a.get("location_id", ""),
                org_id=org_id,
                system_a_value=str(a.get("amount", "")),
                system_b_value=None,
                field_name="record",
                details="Record exists in System A but has no corresponding entry in System B",
            ))
        elif len(b_entries) == 1 and norm_id not in matched_b_refs:
            # Single match - mark as matched and check values in Pass 4
            matched_b_refs.add(norm_id)

            # Pass 4: Value mismatch for 1-to-1 matches
            b_entry = b_entries[0]

            # Compare amount
            val_a_amt = safe_parse_decimal(str(a.get("amount", "")))
            val_b_amt = safe_parse_decimal(str(b_entry.get("amount", "")))

            if val_a_amt is not None and val_b_amt is not None and val_a_amt != val_b_amt:
                discrepancies.append(DiscrepancyResult(
                    reason="VALUE_MISMATCH",
                    record_id=a["record_id"],
                    location_id=a.get("location_id", ""),
                    org_id=org_id,
                    system_a_value=str(a.get("amount", "")),
                    system_b_value=str(b_entry.get("amount", "")),
                    field_name="amount",
                    details=f"Amount differs: A={val_a_amt}, B={val_b_amt}",
                ))

            # Compare quantity
            val_a_qty = safe_parse_decimal(str(a.get("quantity", "")))
            val_b_qty = safe_parse_decimal(str(b_entry.get("quantity", "")))

            if val_a_qty is not None and val_b_qty is not None and val_a_qty != val_b_qty:
                discrepancies.append(DiscrepancyResult(
                    reason="VALUE_MISMATCH",
                    record_id=a["record_id"],
                    location_id=a.get("location_id", ""),
                    org_id=org_id,
                    system_a_value=str(a.get("quantity", "")),
                    system_b_value=str(b_entry.get("quantity", "")),
                    field_name="quantity",
                    details=f"Quantity differs: A={val_a_qty}, B={val_b_qty}",
                ))

            # Compare status (string comparison, case-insensitive)
            status_a = str(a.get("status", "")).strip().lower()
            status_b = str(b_entry.get("status", "")).strip().lower()

            if status_a and status_b and status_a != status_b:
                discrepancies.append(DiscrepancyResult(
                    reason="VALUE_MISMATCH",
                    record_id=a["record_id"],
                    location_id=a.get("location_id", ""),
                    org_id=org_id,
                    system_a_value=str(a.get("status", "")),
                    system_b_value=str(b_entry.get("status", "")),
                    field_name="status",
                    details=f"Status differs: A='{status_a}', B='{status_b}'",
                ))
        elif norm_id not in matched_b_refs:
            # Already handled as duplicate in Pass 1
            matched_b_refs.add(norm_id)

    # ------------------------------------------------------------------
    # Pass 3: Orphan detection in System B
    # ------------------------------------------------------------------
    for norm_ref, b_entries in b_by_ref.items():
        if norm_ref not in matched_b_refs and norm_ref:
            # This System B reference doesn't resolve to any System A record
            if norm_ref not in a_by_norm_id:
                for orphan in b_entries:
                    org_id = location_org_map.get(
                        orphan.get("location_id", ""), "UNKNOWN"
                    )
                    discrepancies.append(DiscrepancyResult(
                        reason="ORPHAN_IN_SYSTEM_B",
                        record_id=orphan.get("record_ref", ""),
                        location_id=orphan.get("location_id", ""),
                        org_id=org_id,
                        system_a_value=None,
                        system_b_value=str(orphan.get("amount", "")),
                        field_name="record",
                        details="System B references a record that does not exist in System A",
                    ))

    return discrepancies
