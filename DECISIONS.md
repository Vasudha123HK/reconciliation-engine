# Architectural Decisions & Technical Trade-offs

This document outlines key technical decisions made during the implementation of the AdosX Cross-System Reconciliation Engine.

---

### 1. Ingestion Strategy: Raw Storage vs. Eager Schema Casting
- **Decision:** Store all incoming CSV payload fields (`amount`, `quantity`, `status`) as raw strings / text fields in SQLite while normalizing references on demand.
- **Alternative:** Strict database column typing (`DecimalField`, `IntegerField`) and strict foreign key validation during ingestion.
- **Reasoning:** In real-world multi-system data feeds, records frequently contain messy strings like `"N/A"`, `"$1,500.00"`, `"NULL"`, or spaces. Strict database-level check constraints would cause ingestion pipeline crashes or silent row drops. Raw storage guarantees zero data loss during ingestion.

---

### 2. Multi-Tenancy Enforcement Layer
- **Decision:** Mandate explicit `org_id` query filtering at the Django API Service / View layer for every endpoint read.
- **Alternative:** Database row-level security (RLS), multi-schema routing, or complex auth middleware.
- **Reasoning:** The assessment requirement explicitly waived authentication while strictly mandating tenant boundary safety. Service-layer filtering ensures that no query can return un-scoped results across tenant boundaries.

---

### 3. Reconciliation Algorithm Design: Pure Domain Functions vs. SQL Outer Joins
- **Decision:** Implement reconciliation in a pure Python domain service (`comparator.py`) using dictionary lookup tables and regex normalization.
- **Alternative:** Perform full outer joins with SQL regex functions directly inside SQLite/PostgreSQL.
- **Reasoning:** Pure Python functions decouple business logic from the database layer, allowing unit tests to run fast in-memory without spinning up database fixtures or managing mock connections.

---

### 4. Decimal Precision vs. Floating Point Comparison
- **Decision:** Use Python's `decimal.Decimal` module for numeric amounts after stripping currency symbols and thousand separators.
- **Alternative:** Using standard Python `float()` casting.
- **Reasoning:** Standard IEEE-754 floating point arithmetic introduces binary representation imprecision (e.g. `100.10 + 0.20 = 100.29999999999998`), which causes false-positive `VALUE_MISMATCH` discrepancies on financial amounts. `Decimal` guarantees exact base-10 arithmetic precision.

---

### 5. Reference ID Normalization Scheme
- **Decision:** Canonicalize reference strings by stripping non-alphanumeric characters and converting to lowercase (e.g., `" REC-0145 "` -> `"rec0145"`).
- **Alternative:** Exact string matching or substring matching.
- **Reasoning:** System B exports frequently mangle System A reference keys with spaces, dashes, or casing variants. Canonical matching avoids false orphan and false missing flags.
