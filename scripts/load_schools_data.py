import pandas as pd
import os
import requests
import io
import time
from dotenv import load_dotenv
from datetime import datetime
from google.cloud import storage
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

load_dotenv()

# --- Configuration ---
RESOURCE_ID = os.getenv("DATA_GOV_SCHOOLS_DATASET_ID")
BASE_URL = os.getenv("DATA_GOV_BASE_URL")
API_KEY = os.getenv("DATA_GOV_API_KEY")

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME") 
current_date = datetime.now().strftime("%Y%m%d")
DESTINATION_BLOB_NAME = f"raw/data_gov/schools_data_{current_date}.csv"

DATASET_ID = os.getenv("BQ_DATASET") 
TABLE_ID = "raw_schools"
# ---------------------

def fetch_all_records():
    all_records = []
    offset = 0
    limit = 400
    total = 1  # Placeholder to start the loop
    
    headers = {
        "x-api-key": API_KEY
    }

    print("Starting data extraction...")

    while len(all_records) < total:
        params = {
            "resource_id": RESOURCE_ID,
            "limit": limit
            # "offset": 100
        }
        
        response = requests.get(BASE_URL, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            records = data['result']['records']
            total = data['result']['total']  # Update the actual total (337)
            
            all_records.extend(records)
            print(f"Fetched {len(all_records)} / {total} records (Offset: {offset})")
            
            # Prepare for next page
            offset += limit
            
            # Brief pause to be polite to the server and avoid 429s
            time.sleep(12) 
        elif response.status_code == 429:
            print("Rate limited. Sleeping for 15 seconds...")
            time.sleep(15)
        else:
            print(f"Failed at offset {offset}: {response.text}")
            response.raise_for_status()

    return all_records

def run_pipeline():
    # 1. Fetch
    records = fetch_all_records()
    df = pd.DataFrame(records)
    
    # 2. Convert to CSV
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    
    # 3. Upload to GCS
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(DESTINATION_BLOB_NAME)
    blob.upload_from_string(csv_buffer.getvalue(), content_type='text/csv')
    
    # 4. Load to BigQuery
    bq_client = bigquery.Client(project=PROJECT_ID)
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        # skip_leading_rows=0,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
    )

    try:
        table_ref = bq_client.dataset(DATASET_ID).table(TABLE_ID)
        source_uri = f"gs://{BUCKET_NAME}/{DESTINATION_BLOB_NAME}"
        load_job = bq_client.load_table_from_uri(
            source_uri,
            table_ref,
            job_config=job_config
        )

        print(f"Starting job {load_job.job_id}...")
        load_job.result()  # Wait for job to complete

        destination_table = bq_client.get_table(table_ref)
        print(f"Loaded {destination_table.num_rows} rows into {DATASET_ID}.{TABLE_ID}.")

        print(f"Pipeline complete. All {len(df)} records loaded.")
    except GoogleAPIError as e:
        print(f"BigQuery API error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    run_pipeline()