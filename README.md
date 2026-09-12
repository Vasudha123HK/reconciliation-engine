# AdosX Cross-System Data Reconciliation & Tenant Isolation Engine

A full-stack data reconciliation and discrepancy auditing system built with **Django REST Framework (Python)**, **React (Vite)**, and **SQLite**.

---

## 1. Features & Capabilities

1. **Resilient Data Ingestion:** Ingests imperfect CSV exports (`system_a.csv`, `system_b.csv`, `locations.csv`) storing raw data defensively without crashing or dropping malformed rows.
2. **Four-Pass Reconciliation Pipeline:**
   - **Pass 1:** `DUPLICATE_IN_SYSTEM_B` — Identifies multiple System B entries referencing the same System A record.
   - **Pass 2:** `MISSING_IN_SYSTEM_B` — Identifies System A records with no System B counterpart.
   - **Pass 3:** `ORPHAN_IN_SYSTEM_B` — Identifies System B entries referencing non-existent System A records.
   - **Pass 4:** `VALUE_MISMATCH` — Performs precision numeric/string comparisons on 1-to-1 matches (amount, quantity, status).
3. **Strict Multi-Tenant Boundary Protection:** All API queries mandate `org_id` parameters to prevent cross-tenant data leaks.
4. **Interactive Dashboard:** Dark-mode React dashboard with tenant selection dropdown, discrepancy reason filtering, record sorting, and stats breakdown cards.
5. **Comprehensive Regression Suite:** Unit tests for all 4 discrepancy types, reference normalization, currency parsing, and tenant isolation.

---

## 2. Project Architecture

```
reconciliation-engine/
├── backend/
│   ├── manage.py
│   ├── core/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── reconciler/
│   │   ├── models.py                   # Location, SystemARecord, SystemBRecord, Discrepancy
│   │   ├── services/
│   │   │   └── comparator.py           # 4-pass reconciliation logic & normalization
│   │   ├── management/
│   │   │   └── commands/
│   │   │       └── import_data.py      # Resilient CSV importer & reconciler trigger
│   │   ├── views.py                    # Multi-tenant API endpoints
│   │   ├── serializers.py              # DRF serializers
│   │   ├── urls.py
│   │   └── tests/
│   │       └── test_comparator.py      # Unit tests suite
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── App.jsx                     # Dashboard container
│   │   ├── components/
│   │   │   ├── DiscrepancyTable.jsx    # Discrepancy table presenter
│   │   │   ├── FilterBar.jsx           # Tenant & reason controls
│   │   │   └── StatsCards.jsx          # Summary stat breakdown cards
│   │   └── index.css                   # Custom design system
│   └── package.json
├── data/
│   ├── system_a.csv                    # System A raw records
│   ├── system_b.csv                    # System B raw records
│   └── locations.csv                   # Location to organization tenant mapping
├── DECISIONS.md                        # Technical decisions log
└── README.md                           # Setup & evaluation response
```

---

## 3. Setup & Running Instructions

### Prerequisites
- Python 3.10+
- Node.js v18+

### Step 1: Backend Setup & Data Ingestion

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py makemigrations reconciler
python manage.py migrate

# Ingest raw CSV data & run reconciliation
python manage.py import_data

# Start the Django development server (runs on http://127.0.0.1:8000)
python manage.py runserver 8000
```

### Step 2: Frontend Setup & Server Launch

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server (runs on http://localhost:5173)
npm run dev
```

### Step 3: Run Unit Tests

```bash
cd backend
python manage.py test reconciler
```

---

## 4. What Was Built vs. Deliberately Not Built

### What Was Built:
- Robust CSV parsing tolerating `N/A`, `NULL`, `$`, commas, and irregular whitespace.
- 4-pass reconciliation algorithm with canonical reference normalization (`" REC-001 "` -> `"rec001"`).
- Persisted Discrepancy models linked to location & organization identifiers.
- DRF API endpoints with strict `org_id` filtering.
- Modern React UI dashboard with dark mode styling, glassmorphism header, sorting, and stats cards.
- Automated unit test suite.

### What Was Deliberately Not Built:
- Complex User Auth / JWT login (waived in prompt scope).
- Server-side pagination (unnecessary for 120-row dataset).
- Custom WebSocket live updates (overkill for static CSV audit runs).

---

## 5. Mandatory Evaluation Questions

### Question 1: What is one thing the AI agent got wrong, and how did you detect it?
**Answer:** The initial draft of reference mapping relied on naive string comparison (`a["record_id"] == b["record_ref"]`). During testing with System B data containing values like `" REC-003 "` and `"rec_005"`, the engine incorrectly flagged them as `MISSING_IN_SYSTEM_B` and `ORPHAN_IN_SYSTEM_B`. I detected this by inspecting test outputs and refactored the logic to use a canonical normalization function (`normalize_reference()`) that strips all non-alphanumeric characters and converts strings to lowercase prior to dictionary grouping.

### Question 2: Which part of the codebase are you least confident about and why?
**Answer:** Handling edge cases in multi-field value comparison when both records contain non-standard sentinel values (e.g. comparing System A status `"cancelled"` vs System B status `""`). While `safe_parse_decimal()` handles numeric fields like amounts cleanly, non-numeric status/date fields rely on basic string matching. In production datasets, status taxonomies across disparate systems would require explicit mapping tables.

### Question 3: What would you fix or build first if given a second day?
**Answer:** I would implement:
1. **Asynchronous Batch Import:** Replace synchronous management command processing with Celery/Redis tasks for large multi-million row file uploads.
2. **CSV Export & Audit Report Generator:** Add a button in the UI allowing tenant administrators to download filtered discrepancy reports as CSV or PDF.
3. **Historical Reconciliation Runs:** Track audit run timestamps to show discrepancy trends over time.
