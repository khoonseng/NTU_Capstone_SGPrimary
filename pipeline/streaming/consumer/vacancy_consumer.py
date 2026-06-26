"""Consume P1 vacancy snapshot events from Kafka and write to BigQuery.

Reads from the p1_vacancy_snapshots topic and inserts each event into
sg_moe.raw_p1_vacancy_snapshots in BigQuery.

Offset commit strategy: manual, synchronous, after confirmed BigQuery write.
This gives at-least-once delivery — if the process dies between write and commit,
the message is re-read and re-inserted on restart (idempotent by event_id).

The BigQuery table is created automatically on first run if it does not exist.

Usage:
    python vacancy_consumer.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from confluent_kafka import Consumer
from dotenv import load_dotenv
from google.cloud import bigquery

# schemas/ is two levels up from consumer/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from schemas.vacancy_snapshot import VacancySnapshot

load_dotenv(Path(__file__).resolve().parents[4] / ".env")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC                   = "p1_vacancy_snapshots"
CONSUMER_GROUP_ID       = os.getenv("KAFKA_CONSUMER_GROUP_ID", "sgprimary-vacancy-consumer")

GCP_PROJECT_ID  = os.getenv("GCP_PROJECT_ID", "test-sg-moe")
BQ_RAW_DATASET  = os.getenv("BQ_RAW_DATASET", "sg_moe")
BQ_TABLE_ID     = f"{GCP_PROJECT_ID}.{BQ_RAW_DATASET}.raw_p1_vacancy_snapshots"

# BigQuery schema — mirrors VacancySnapshot fields exactly.
# Table is auto-created on first run; existing table is left unchanged.
BQ_SCHEMA = [
    bigquery.SchemaField("event_id",           "STRING",    mode="REQUIRED"),
    bigquery.SchemaField("phase",              "STRING",    mode="REQUIRED"),
    bigquery.SchemaField("registration_year",  "INTEGER",   mode="REQUIRED"),
    bigquery.SchemaField("school_name",        "STRING",    mode="REQUIRED"),
    bigquery.SchemaField("snapshot_timestamp", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("snapshot_type",      "STRING",    mode="REQUIRED"),
    bigquery.SchemaField("vacancy_at_open",    "INTEGER",   mode="REQUIRED"),
    bigquery.SchemaField("vacancy_remaining",  "INTEGER",   mode="REQUIRED"),
    bigquery.SchemaField("applied_count",      "INTEGER",   mode="REQUIRED"),
    bigquery.SchemaField("pct_filled",         "FLOAT",     mode="REQUIRED"),
    bigquery.SchemaField("simulation_day",     "INTEGER",   mode="REQUIRED"),
]


def ensure_bq_table(client: bigquery.Client) -> None:
    """Create raw_p1_vacancy_snapshots if it does not already exist."""
    table = bigquery.Table(BQ_TABLE_ID, schema=BQ_SCHEMA)
    client.create_table(table, exists_ok=True)
    print(f"BigQuery table ready: {BQ_TABLE_ID}", flush=True)


def write_to_bigquery(client: bigquery.Client, snapshot: VacancySnapshot) -> bool:
    """Insert one snapshot row into BigQuery. Returns True on success."""
    errors = client.insert_rows_json(BQ_TABLE_ID, [snapshot.to_dict()])
    if errors:
        print(f"  BigQuery insert error: {errors}", flush=True)
        return False
    return True


def main() -> None:
    bq_client = bigquery.Client(project=GCP_PROJECT_ID)
    ensure_bq_table(bq_client)

    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id":          CONSUMER_GROUP_ID,
            "auto.offset.reset": "earliest",
            # Manual commit — offset only advances after confirmed BigQuery write.
            # Prevents data loss if the process dies between read and write.
            "enable.auto.commit": False,
        }
    )

    consumer.subscribe([TOPIC])
    print(
        f"Vacancy consumer listening on {KAFKA_BOOTSTRAP_SERVERS}  "
        f"topic={TOPIC}  group={CONSUMER_GROUP_ID}",
        flush=True,
    )

    try:
        while True:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                print(f"Consumer error: {message.error()}", flush=True)
                continue

            event = json.loads(message.value())
            snapshot = VacancySnapshot.from_dict(event)

            if write_to_bigquery(bq_client, snapshot):
                # Commit only after BigQuery confirms the write.
                consumer.commit(message=message, asynchronous=False)
                key = message.key().decode() if message.key() else snapshot.school_name
                print(
                    f"partition={message.partition()} offset={message.offset()} "
                    f"key={key} "
                    f"phase={snapshot.phase} day={snapshot.simulation_day} "
                    f"{snapshot.snapshot_type} vacancy={snapshot.vacancy_remaining}",
                    flush=True,
                )
            else:
                print(
                    f"  Skipping commit for offset={message.offset()} "
                    f"— BigQuery write failed. Message will be re-read on restart.",
                    flush=True,
                )
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
