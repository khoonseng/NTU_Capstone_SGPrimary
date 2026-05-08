# SGPrimary — P1 Ballot Insights & School Recommendation Engine

> A data engineering and AI capstone project built on Singapore's Primary 1 (P1) registration balloting data.
> Designed to help parents make informed school choices — and to demonstrate end-to-end data and AI engineering skills.

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![dbt](https://img.shields.io/badge/dbt-BigQuery-orange)](https://www.getdbt.com/)
[![BigQuery](https://img.shields.io/badge/Google-BigQuery-4285F4)](https://cloud.google.com/bigquery)
[![GCS](https://img.shields.io/badge/Google-Cloud%20Storage-4285F4)](https://cloud.google.com/storage)

---

## Table of Contents

- [Motivation](#motivation)
- [Project Goals](#project-goals)
- [Architecture Overview](#architecture-overview)
- [Data Sources](#data-sources)
- [Key Design Decisions](#key-design-decisions)
- [Repository Structure](#repository-structure)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Setup Guide](setup_guide.md)

---

## Motivation

As a parent preparing for my daughter's Primary 1 registration, I found the process of evaluating schools genuinely difficult. Balloting data is scattered across multiple websites, historical trends are not easily accessible, and there is no single tool that helps a parent reason about their actual chances of getting into a specific school.

This project is my attempt to solve that problem — for myself, and hopefully for other parents in my network.

It is also a portfolio project built during the **NTU SCTP Data Science and AI programme**, designed to demonstrate practical data engineering and AI skills to prospective recruiters. I am exploring roles in both **Data Engineering** and **AI Engineering**.

---

## Project Goals

1. **For parents** — provide a recommendation engine that surfaces schools with the lowest ballot difficulty based on distance, citizenship status, and school attributes, alongside an honest assessment of historical ballot trends.

2. **For portfolio** — demonstrate end-to-end data engineering skills: ingestion, transformation, data modelling, API development, and ML prediction.

3. **For learning** — apply RAG (Retrieval-Augmented Generation), vector databases, and ML prediction in a real-world Singapore context.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Data Sources                           │
|                                                             |
│  data.gov.sg API                sgschooling.com (scrape)    │
│  (school metadata)              (P1 balloting 2009–2025)    │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│      Google Cloud Storage (Data Lake for Raw Archive)       │
|                                                             |
│        gs://bucket/data_gov/schools_YYYYMMDD.csv            │
│        gs://bucket/sgschooling/sgschooling_YYYY.parquet     │
└──────────────┬──────────────────────┬───────────────────────┘
               │                      │
               ▼                      ▼
┌─────────────────────────────────────────────────────────────┐
│              BigQuery — schema: sg_moe (raw)                │
|                                                             |
│  raw_schools             raw_sgschooling_balloting          │
│                          (partitioned by registration_year) │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              dbt — schema: sg_moe_staging                   │
|                                                             |
│                 stg_all_schools                             │
│                 stg_primary_schools                         │
|                 stg_sgschooling_balloting                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌───────────────────────┐   ┌─────────────────────────────────┐
│ schema: sg_moe_seeds  |   │      schema: sg_moe_star        │
│                       │   │                                 │
│  phases               │   │  dim_school                     │
│  balloting_codes      │   │  dim_school_generalinfo         │
│  school_name_mapping  │   │  fact_balloting                 │
│  school_lifecycle     │   │  (partitioned + clustered)      │
│  school_statuses      │   │  mart_school_analysis           │
│                       │   │  (pre-aggregated feature store) │
└───────────────────────┘   └─────────────────────────────────┘
                                        │
                           ┌────────────┴────────────┐
                           ▼                         ▼
                    FastAPI (Week 2)         ML Model (Week 3-4)
                    /schools                 Ballot probability
                    /recommend               Subscription rate
                    /predict                 prediction for 2026
```

---

## Data Sources

### 1. data.gov.sg API — School Metadata
- **Dataset ID:** `d_688b934f82c1059ed0a6993d2a829089`
- **Content:** General information of schools — name, address, postal code, type, SAP/autonomous/gifted/IP indicators, mother tongue, zone, principal details
- **Ingestion:** Python script (`scripts/load_schools_data.py`) via API call
- **Update frequency:** Annual — re-run script when MOE updates school metadata
- **Raw table:** `sg_moe.raw_schools`
- **File format in GCS:** CSV (one file per extraction date, with the latest being loaded into raw table)

### 2. sgschooling.com — P1 Balloting History
- **URL pattern:** `https://sgschooling.com/year/{year}/all`
- **Content:** Per-school, per-phase balloting results including vacancy, applied, taken, and ballot scenario details
- **Years covered:** 2009–2025 (17 years)
- **Ingestion:** Python scraper (`scripts/scrape_sgschooling.py`) using BeautifulSoup
- **Raw table:** `sg_moe.raw_sgschooling_balloting` (range-partitioned by `registration_year`)
- **File format in GCS:** Parquet (one file per year)

#### Why sgschooling.com as the sole balloting source

Four potential sources were evaluated:

| Source | Coverage | Decision | Reason |
|---|---|---|---|
| sgschooling.com | 2009–2025 | ✅ Primary source | Longest history, single clean HTML table per year, scrapable |
| MOE website | 2025 only | ❌ Not ingested | 18 paginated HTML pages, government site scraping risk, data already in sgschooling |
| elite.com.sg | 2019–2025 | ❌ Not ingested | Full overlap with sgschooling, dropdown-driven scraping complexity |
| sgschoolkaki.com | 2025 only | ❌ Not ingested | Third-party aggregator, single year, no benefit over sgschooling |

Data accuracy from sgschooling.com extraction was manually verified against MOE published figures and other sources after ingestion.

---

## Key Design Decisions
With the MOE and balloting data, certain data issues were observed in the following areas:
#### (1) School Name Reconciliation
- School names differ between data.gov.sg and sgschooling.com.

#### (2) Phase Structure Change in 2022
- MOE merged Phases 2A(1) and 2A(2) into a single Phase 2A from 2022 onwards.

#### (3) Missing Vacancy and Applied Figures Pre-2019
- For phases 1, 2A(1), and 2A(2), MOE did not publish vacancy and applied counts before 2019.

#### (4) School Lifecycle — Mergers and Relocations
- Several primary schools have ceased or temporarily suspended P1 registration due to mergers or subjected to relocations.

These 4 key design decisions are documented here - ([Key Design Decisions](key_design.md)), along with other technical design considerations.

---

## Repository Structure

```
NTU_Capstone_SGPrimary/
├── keys/                          # GCP service account keys (gitignored)
├── scripts/
│   ├── load_schools_data.py       # data.gov.sg API → GCS → BigQuery
│   └── scrape_sgschooling.py      # sgschooling.com → Parquet → GCS
│   └── load_sgschooling_data.py   # GCS → BigQuery
├── sg_primary_dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml               # BigQuery connection (gitignored)
│   ├── models/
│   │   ├── staging/
│   │   │   ├── sources.yml
│   │   │   ├── stg_all_schools.sql
│   │   │   ├── stg_primary_schools.sql
│   │   │   └── stg_sgschooling_balloting.sql
│   │   └── star/
│   │       ├── schema.yml
│   │       ├── dim_school.sql
│   │       ├── dim_school_generalinfo.sql
│   │       ├── fact_balloting.sql
│   │       └── mart_school_analysis.sql
│   └── seeds/
│       ├── schema.yml
│       ├── balloting_codes.csv
│       ├── phases.csv
│       ├── school_lifecycle.csv
│       ├── school_name_mapping.csv
│       └── school_statuses.csv
└── README.md
```

---

### Schema overview

| Schema | Tables | Description |
|---|---|---|
| `sg_moe` | `raw_schools`, `raw_sgschooling_balloting` | Raw ingested data — immutable |
| `sg_moe_seeds` | `phases`, `balloting_codes`, `school_lifecycle`, `school_name_mapping`, `school_statuses` | Reference and mapping tables |
| `sg_moe_staging` | `stg_all_schools`, `stg_primary_schools`, `stg_sgschooling_balloting` | Cleaned and standardised — intermediate layer |
| `sg_moe_star` | `dim_school`, `dim_school_generalinfo`, `fact_balloting`, `mart_school_analysis` | Analytical and API-ready outputs |

### dbt DAG (Directed Acyclic Graph)

```
raw_schools                    raw_sgschooling_balloting
      │                                    │
      │                    + school_name_mapping (seed)
      │                    + phases (seed)
      ▼                                    ▼
stg_all_schools              stg_sgschooling_balloting
stg_primary_schools
      │                                    │
      ▼                                    ▼
dim_school  ◄──────────────────── fact_balloting
dim_school_generalinfo                     │
                                           ▼
                               mart_school_analysis
```

---

## Known Limitations

| Limitation | Impact | Notes |
|---|---|---|
| Vacancy and applied figures unavailable for phases 1, 2A(1), 2A(2) before 2019 | ML features for early phases incomplete pre-2019 | MOE policy — data was never published. `has_full_figures` flag marks affected rows |
| sgschooling.com data accuracy | Dependent on third-party site | Manually verified against MOE published figures. No official API exists for balloting data |
| School metadata is a point-in-time snapshot | Principal names, contact details go stale | SCD implementation deferred to future iteration when scheduled ingestion is built |
| Pre-2015 data should be treated with lower confidence for ML training | Older demand patterns may not predict 2026 behaviour | Consider year-weighting when training prediction model |
| 2021–2022 data may reflect COVID anomalies | Subscription rates may be atypically low | Flag these years when evaluating trend features |
| OneMap API integration for distance calculation not yet implemented | Parents currently select distance band manually | Planned for future iterations — will compute actual distances from postal code |

---

## Roadmap

| Week | Focus | Status |
|---|---|---|
| Week 1 | Data foundation — ingestion, BigQuery, dbt pipeline | ✅ Complete |
| Week 2 | FastAPI — `/schools`, `/recommend`, `/predict` endpoints. Cloud Run deployment | 🔜 Upcoming |
| Week 3 | ML model — ballot probability and subscription rate prediction for 2026 | 🔜 Upcoming |
| Week 4 | RAG layer — ChromaDB vector store, LLM-powered school advice, frontend | 🔜 Upcoming |

---


*Built as part of the NTU SCTP Data Science and AI programme capstone project.*
*Author: Khoon Seng | [GitHub](https://github.com/khoonseng)*
