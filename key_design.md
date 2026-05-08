## Key Design Decisions

### (1) School Name Reconciliation

School names differ between data.gov.sg and sgschooling.com in two ways:
1. **Apostrophe character:** sgschooling uses typographic right single quote (`’`, U+2019); data.gov.sg uses straight ASCII apostrophe (`'`, U+0027)
2. **Name truncation:** sgschooling omits "SCHOOL" suffix for some schools (e.g. `CHIJ ST. NICHOLAS GIRLS’` vs `CHIJ ST. NICHOLAS GIRLS' SCHOOL`)

**Resolution:** A manually curated `school_name_mapping` seed file maps sgschooling raw names to canonical data.gov.sg names. The `REPLACE()` function in `stg_sgschooling_balloting.sql` handles the apostrophe character at the staging layer. This is the single source of truth for name canonicalisation — no downstream model repeats this logic.

### (2) Phase Structure Change in 2022

MOE merged Phases 2A(1) and 2A(2) into a single Phase 2A from 2022 onwards:
- **Pre-2022 phases:** 1, 2A(1), 2A(2), 2B, 2C, 2C(S), 3
- **2022 onwards:** 1, 2A, 2B, 2C, 2C(S), 3

**Resolution:** The `phases` seed file maps `phase_raw → phase_normalised`, with `2A(1)` → `2A` for pre-2022 years and `2A(2)` kept distinct. The staging model reference to this seed rather than using a CASE statement to ensure referential integrity via dbt test, so adding new phase mappings requires only a seed file update — no SQL changes.

### (3) Missing Vacancy and Applied Figures Pre-2019

For phases 1, 2A(1), and 2A(2), MOE did not publish vacancy and applied counts before 2019. This is a **policy decision**, not a data quality issue — `taken` is always populated since it is an administrative requirement.

**Resolution:** A `has_full_figures` boolean column in staging and the fact table distinguishes intentional NULLs from unexpected ones. dbt `not_null` tests apply the condition `WHERE has_full_figures = TRUE` so tests do not fail on legitimately missing data.

### (4) School Lifecycle — Mergers and Relocations

Several primary schools have ceased or temporarily suspended P1 registration due to mergers or subjected to relocations. A manually curated `school_lifecycle` seed tracks these events:

| Status | Meaning | Example |
|---|---|---|
| `active` | Currently accepting registration | Majority of schools |
| `relocated_gap` | Temporarily suspended, will resume | Pioneer Primary (suspend from 2021–2024, resume in 2025) |
| `merged` | Permanently ceased, absorbed into another school | Eunos Primary → Telok Kurau Primary |

**Key design choice:** Historical data for inactive schools is **retained** in all tables — it is valuable for trend analysis and the API surfaces merger/relocation context to parents. The `is_active` flag in `dim_school` is computed dynamically against `CURRENT_DATE()` so it self-updates when a relocated school resumes without requiring seed file changes.

### (5) dim_school Split into Two Tables

School attributes were split into two dimension tables based on rate of change:

| Table | Contents | Rationale |
|---|---|---|
| `dim_school` | 17 stable attributes (zone, type, SAP, autonomous, gifted, IP, mother tongue, lifecycle) | Used for analysis and ML features — stable, rarely changes |
| `dim_school_generalinfo` | 14 operational attributes (principal, VP names, contact, transport) | Used by API for parent-facing display — changes frequently, not used in ML |

This avoids storing frequently-changing operational data alongside analytical attributes, following normalisation principles. SCD (Slowly Changing Dimension) implementation is deferred to a future iteration when periodic ingestion is scheduled.

### (6) Surrogate Keys

`dbt_utils.generate_surrogate_key()` generates MD5-based surrogate keys for `dim_school`, `fact_balloting`, and `mart_school_analysis`. Keys are deterministic — the same input always produces the same hash — making pipelines idempotent and joins stable across `dbt run` executions.

School names were deliberately **not** used as natural primary keys because cross-source name mismatches (even after cleaning) could silently break joins.

### (7) BigQuery Partitioning and Clustering

| Table | Partition | Cluster | Rationale |
|---|---|---|---|
| `raw_sgschooling_balloting` | `registration_year` (int64, range) | — | Enables year-level partition pruning on load and query |
| `fact_balloting` | `registration_year` (int64, range) | `school_name_clean`, `phase_normalised` | API queries filter by school name and phase |
| `mart_school_analysis` | `registration_year` (int64, range) | `school_name_clean`, `phase_normalised` | Same query pattern as fact table |

Note: BigQuery integer range partitioning requires `"data_type": "int64"` in the dbt config — `"integer"` is not accepted despite being valid SQL syntax.

### (8) Over-enrolment Logic

Over-enrolment (`is_over_enrolled`) is computed at the **school level**, not the phase level:

```
total_taken (SUM across all phases) > total_vacancy (declared school capacity)
```

This correctly captures the scenario where a school admits more students than its declared capacity — which happens legitimately when Phase 1 sibling admissions exceed the planned allocation, or when MOE adjusts intakes mid-exercise.
