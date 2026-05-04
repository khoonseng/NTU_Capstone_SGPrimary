import os
import json
from google.oauth2 import service_account
from google.cloud import storage

def get_gcp_credentials():
    # Case 1: Cloud (env variable JSON)
    if os.getenv("GCP_SERVICE_ACCOUNT_JSON"):
        return service_account.Credentials.from_service_account_info(
            json.loads(os.getenv("GCP_SERVICE_ACCOUNT_JSON"))
        )
    
    # Case 2: Local (.env file path)
    return None  # default credentials will be used

def list_gcs_files(bucket_name, creds):
    client = storage.Client(credentials=creds)  # auto uses GOOGLE_APPLICATION_CREDENTIALS
    blobs = client.list_blobs(bucket_name)

    print(f"Files in bucket '{bucket_name}':")
    for blob in blobs:
        print(blob.name)