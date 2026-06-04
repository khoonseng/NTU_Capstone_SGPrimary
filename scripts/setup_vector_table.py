from google.cloud import bigquery
from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET_ID = os.getenv("BQ_DATASET") + "_star"
VECTOR_TABLE_NAME = "advisor_knowledge_base"

client = bigquery.Client(project=PROJECT_ID)

schema = [
    bigquery.SchemaField("doc_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("domain", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("topic", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("source_file", "STRING"),
    bigquery.SchemaField("source_url", "STRING"),          # add this
    bigquery.SchemaField("policy_year", "INTEGER"),        # add this
    bigquery.SchemaField("canonical_source", "STRING"),    # add this
    bigquery.SchemaField("content", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
]


table_ref = client.dataset(DATASET_ID).table(VECTOR_TABLE_NAME)
table = bigquery.Table(table_ref, schema=schema)
table = client.create_table(table, exists_ok=True)
print(f"Table created: {table.full_table_id}")