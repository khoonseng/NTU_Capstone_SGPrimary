# Setup Guide for the Data Pipeline

## (1) Setting up the environment and prerequisites

### Prerequisites

- Python 3.11+
- GCP account with billing enabled
- dbt Core with BigQuery adapter (see [environment.yml](environment.yml))

### GCP setup

1. Create a GCP project and enable BigQuery and Cloud Storage APIs
2. Create a service account with roles: `Storage Admin`, `BigQuery Admin`
3. Download the JSON key and save to `keys/` (this folder is gitignored)
4. Create a GCS bucket for raw data storage
5. Create initial BigQuery dataset: `sg_moe`
- other datasets will be created via dbt [`sg_moe_seeds`, `sg_moe_staging`, `sg_moe_star`]
### Running the ingestion scripts

**Prerequisites:** Python 3.11+, GCP service account with Storage Admin and BigQuery Admin roles, `.env` file configured.

### Environment variables required (`.env`)

```bash
# GCP configurations
GOOGLE_APPLICATION_CREDENTIALS=./keys/your-service-account.json
GCS_BUCKET_NAME=your-gcs-bucket-name
BQ_DATASET=your-bigquery-dataset-name
GCP_PROJECT_ID=your-gcp-project-id

# data.gov.sg API configurations
DATA_GOV_BASE_URL=https://data.gov.sg/api/action/datastore_search
DATA_GOV_SCHOOLS_DATASET_ID=d_688b934f82c1059ed0a6993d2a829089
DATA_GOV_API_KEY=your-datagov-api-key
```


```bash
# Set up conda environment
conda env create -f environment.yml

# Activate conda environment
conda activate sgprimary

# Extract School metadata from data.gov.sg API into BigQuery
python scripts/load_schools_data.py

# Extract Balloting history — single year (validation)
python scripts/scrape_sgschooling.py

# Extract Balloting history — full range
python scripts/scrape_sgschooling.py 2009 2025

# Load Balloting history into BigQuery
python scripts/load_sgschooling_data.py
```

### Re-scraping a specific year

If a parsing bug is found and a year needs to be re-scraped, delete the partition first to avoid duplicates:

```sql
DELETE FROM `your-project.sg_moe.raw_sgschooling_balloting`
WHERE registration_year = 2025
```

Then re-run the scraper for that year.


### dbt setup

Configure `sg_primary_dbt/profiles.yml` (gitignored — not committed to repo):

```yaml
sg_primary_dbt:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: your-gcp-project-id
      dataset: your-bigquery-dataset-name
      keyfile: ../keys/your-service-account.json
      location: your-desired-region
      threads: 4
```

### Running the full pipeline

```bash
cd sg_primary_dbt

# Load seed reference tables
dbt seed

# Install dependencies (e.g. dbt utils)
dbt deps

# Run all models
dbt run

# Run all tests
dbt test

# Run seeds + models + tests together (recommended)
dbt build
```

---

## (2) Executing the full run

```bash
# 1. Activate conda environment
conda activate sgprimary

# 2. Ingest raw data
python scripts/load_schools_data.py
python scripts/scrape_sgschooling.py 2009 2025
python scripts/load_sgschooling_data.py 2009 2025

# 3. Build dbt pipeline
cd sg_primary_dbt
dbt deps
dbt build
```

---