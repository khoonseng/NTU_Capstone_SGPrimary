# SGPrimary — P1 Ballot Insights & School Recommendation Engine

> A data engineering and AI capstone project built on Singapore's Primary 1 (P1) registration balloting data.
> Designed to help parents make informed school choices — and to demonstrate end-to-end data and AI engineering skills.

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![dbt](https://img.shields.io/badge/dbt-BigQuery-orange)](https://www.getdbt.com/)
[![BigQuery](https://img.shields.io/badge/Google-BigQuery-4285F4)](https://cloud.google.com/bigquery)
[![GCS](https://img.shields.io/badge/Google-Cloud%20Storage-4285F4)](https://cloud.google.com/storage)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-29.4-2496ED)](https://www.docker.com/)
[![Cloud Run](https://img.shields.io/badge/Google-Cloud%20Run-4285F4)](https://cloud.google.com/run)

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
- [Setup Guide](#setup-guide)

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
                        FastAPI               ML Model (Week 3-4)
                        /health               Ballot probability
                        /schools              Subscription rate
                        /recommend            prediction for 2026
                        /predict
                           │
                           ▼
                    Docker Container
                    (Google Artifact Registry)
                           │
                           ▼
                    Google Cloud Run
                    (us-central1, serverless)
                    Public API endpoint
```

---

## Data Sources

### 1. data.gov.sg — School Metadata
- **Dataset:** [General Information of Schools](https://data.gov.sg/datasets?topics=education&query=primary+&resultId=d_688b934f82c1059ed0a6993d2a829089)
- **Provider:** Singapore Government, data.gov.sg
- **Content:** General information of schools - School name, address, postal code, type (government/government-aided), SAP/autonomous gifted/IP indicators, mother tongue, zone, principal and VP details
- **Ingestion:** Python script (`scripts/load_schools_data.py`) via API call
- **Update frequency:** Annual — re-run script when MOE updates school metadata
- **Raw table:** `sg_moe.raw_schools`
- **File format in GCS:** CSV (one file per extraction date, with the latest being loaded into raw table)
- **Licence:** Singapore Open Data Licence 1.0

### 2. sgschooling.com — P1 Balloting History *(primary source)*
- **Website:** [sgschooling.com](https://sgschooling.com) — built and maintained by **Junda Ong**, a Singaporean parent who created the site in 2019 while preparing for his own child's P1 registration
- **Content:** Per-school, per-phase P1 balloting results — vacancy, applied, taken, ballot scenarios and ballot chance statistics
- **Years covered:** 2009–2025 (17 years)
- **Ingestion:** Python scraper (`scripts/scrape_sgschooling.py`) using BeautifulSoup with polite request intervals
- **Raw table:** `sg_moe.raw_sgschooling_balloting`
- **File format in GCS:** Parquet (one file per year)
- **Attribution:** All balloting history data is sourced from sgschooling.com, which in turn sources from MOE's published P1 registration results. This project uses the data with permission from the site creator. For the most current and up-to-date balloting information, please visit [sgschooling.com](https://sgschooling.com) directly.

> **Note:** No official API exists for P1 balloting data on data.gov.sg. 
> sgschooling.com is the most comprehensive third-party aggregator of this 
> data, covering 17 years of history in a consistent, structured format. 
> Four potential sources were evaluated for the full comparison.

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

<br/>
These 4 key design decisions are documented here - ([Key Design Decisions](key_design.md)), along with other technical design considerations.

---

## API Endpoints

The SGPrimary API is built with FastAPI and deployed on Google Cloud Run.

**Base URL:** `{YOUR_CLOUD_RUN_URL}`

**Interactive docs:** `{base_url}/docs`

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness check — returns API version and status |
| `/schools` | GET | Returns active primary schools with optional attribute filters |
| `/recommend` | GET | Returns school recommendations based on location, phase, and balloting history |
| `/predict` | GET | Returns ballot risk assessment for a specific school and phase |

### `/schools` Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `zone_code` | string | No | Filter by zone: NORTH, SOUTH, EAST, WEST |
| `dgp_code` | string | No | Filter by estate e.g. ADMIRALTY |
| `type_code` | string | No | Filter by school type e.g. GOVERNMENT, GOVERNMENT-AIDED |
| `nature_code` | string | No | Filter by school nature e.g. CO-ED, BOYS, GIRLS |
| `sap_ind` | boolean | No | SAP school indicator |
| `autonomous_ind` | boolean | No | Autonomous school indicator |
| `gifted_ind` | boolean | No | Gifted programme indicator |
| `ip_ind` | boolean | No | Integrated Programme indicator |

### `/recommend` Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `zone_code` | string | At least one of zone_code or dgp_code | Filter by zone |
| `dgp_code` | string | At least one of zone_code or dgp_code | Filter by estate |
| `phase` | string | No | Phase: 2B, 2C, 2C(S), 3. If omitted, returns all phases with most recent year only |
| `has_balloting_3yr` | boolean | No | Requires phase. true = balloted in last 3 years, false = did not ballot |
| `type_code` | string | No | Filter by school type |
| `nature_code` | string | No | Filter by school nature |
| `sap_ind` | boolean | No | SAP school indicator |
| `autonomous_ind` | boolean | No | Autonomous school indicator |
| `gifted_ind` | boolean | No | Gifted programme indicator |
| `ip_ind` | boolean | No | Integrated Programme indicator |

### `/predict` Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `school_name` | string | Yes | Full school name e.g. ADMIRALTY PRIMARY SCHOOL |
| `phase` | string | Yes | Phase: 2B, 2C, 2C(S), 3 |

### Response Modes for `/recommend`

**Mode 1 — No phase selected:**
Returns all phases for matching schools. Each phase shows the most recent completed year plus the current year (2026) if registration data is available.

**Mode 2 — Phase selected:**
Returns the selected phase for matching schools with the last 3 completed years of history, trend features (`subscription_rate_3yr_avg`, `ballot_occurrences_last_3yr` etc.), and `reference_years` showing the exact years used for trend computation.


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
├── api/
│   ├── main.py                    # FastAPI app entry point, global exception handlers
│   ├── config.py                  # Settings via pydantic-settings, BigQuery client init
│   ├── constants.py               # Shared constants e.g. VALID_PHASES
│   ├── Dockerfile                 # Container definition for Cloud Run deployment
│   ├── requirements.txt           # API-specific Python dependencies
│   ├── routers/
│   │   ├── schools.py             # GET /schools
│   │   ├── recommend.py           # GET /recommend
│   │   └── predict.py             # GET /predict
│   ├── models/
│   │   ├── schools.py             # Pydantic response models for /schools
│   │   ├── recommend.py           # Pydantic response models for /recommend
│   │   └── predict.py             # Pydantic response models for /predict
│   ├── services/
│   │   ├── bigquery.py            # Shared BigQuery query execution helper
│   │   ├── recommend.py           # Business logic for /recommend
│   │   └── predict.py             # Business logic for /predict
│   └── postman/
│       └── SGPrimary_API.postman_collection.json
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
| Phases 1 and 2A excluded from /recommend and /predict | Parents with Phase 1 siblings or Phase 2A alumni connections cannot use ballot prediction | Planned for future iteration |
| `/predict` uses heuristic risk assessment only | ballot_risk_level is rule-based, not ML-predicted | ML model planned for Week 3 |

---

## Roadmap

| Week | Focus | Status |
|---|---|---|
| Week 1 | Data foundation — ingestion, BigQuery, dbt pipeline | ✅ Complete |
| Week 2 | FastAPI — `/health`, `/schools`, `/recommend`, `/predict` endpoints. Docker + Cloud Run deployment | ✅ Complete |
| Week 3 | ML model — ballot probability and subscription rate prediction for 2026 | 🔜 Upcoming |
| Week 4 | RAG layer — ChromaDB vector store, LLM-powered school advice, frontend | 🔜 Upcoming |

---

##  Setup Guide
- For Data Pipeline instructions, see [here](./setup_guide_data_pipeline.md)
- For API local development and Cloud Run deployment instructions, see [here](./setup_guide_api.md).

---


*Built as part of the NTU SCTP Data Science and AI programme capstone project.*
*Author: Khoon Seng | [GitHub](https://github.com/khoonseng)*
