from google.cloud import bigquery, storage
from scripts.utils import get_gcp_credentials, list_gcs_files
from dotenv import load_dotenv

load_dotenv()
creds = get_gcp_credentials()
bq_client = bigquery.Client(credentials=creds)
storage_client = storage.Client(credentials=creds)

list_gcs_files("sg-moe", creds)

query = """
    SELECT * FROM `test-sg-moe.raw.schools` LIMIT 10 
"""

results = bq_client.query(query)

for row in results:
    print(row)