# scripts/embed_knowledge_base.py
# Loads Markdown files from scripts/knowledge_base/, strips frontmatter,
# chunks content, embeds via Vertex AI, and inserts into BigQuery.

import os
import sys
import uuid
from pathlib import Path

import yaml
from dotenv import load_dotenv
from google.cloud import bigquery
from langchain_text_splitters import MarkdownTextSplitter

# Import the custom embeddings wrapper built on Day 1
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.services.embeddings import VertexGenAIEmbeddings

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET_ID = os.getenv("BQ_DATASET") + "_star"
VECTOR_TABLE_NAME = "advisor_knowledge_base"
TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{VECTOR_TABLE_NAME}"

KB_DIR = Path(__file__).parent / "knowledge_base"
DOMAIN = "moe_policy"

CHUNK_SIZE = 4000       # characters
CHUNK_OVERLAP = 600     # characters

# Files to skip
SKIP_PATTERNS = {"document_template.md", "copy"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def should_skip(filename: str) -> bool:
    if filename in SKIP_PATTERNS:
        return True
    if any(pattern in filename.lower() for pattern in SKIP_PATTERNS):
        return True
    return False


def parse_frontmatter(text: str) -> dict:
    """
    Extract YAML frontmatter between opening and closing --- fences.
    Returns empty dict if no valid frontmatter found.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return {}


def strip_frontmatter(text: str) -> str:
    """
    Remove the YAML frontmatter block, returning only the document body.
    """
    if not text.startswith("---"):
        return text
    end = text.find("---", 3)
    if end == -1:
        return text
    return text[end + 3:].strip()


def chunk_document(body: str) -> list[str]:
    """
    Split document body into overlapping chunks using MarkdownTextSplitter,
    which respects Markdown heading boundaries when possible.
    """
    splitter = MarkdownTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return splitter.split_text(body)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    bq_client = bigquery.Client(project=PROJECT_ID)

    embeddings_model = VertexGenAIEmbeddings(
        model="text-embedding-004",
        project=PROJECT_ID,
        location="us-central1",
    )

    # Clear existing moe_policy rows — ensures re-runs are idempotent
    print(f"Clearing existing '{DOMAIN}' rows from {TABLE_ID} ...")
    bq_client.query(
        f"DELETE FROM `{TABLE_ID}` WHERE domain = @domain",
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("domain", "STRING", DOMAIN)
            ]
        ),
    ).result()
    print("Cleared.\n")

    md_files = sorted(
        f for f in KB_DIR.glob("*.md")
        if not should_skip(f.name)
    )

    if not md_files:
        print(f"No Markdown files found in {KB_DIR}. Exiting.")
        return

    total_chunks = 0
    total_rows_inserted = 0
    total_errors = 0

    for md_file in md_files:
        print(f"Processing: {md_file.name}")
        raw_text = md_file.read_text(encoding="utf-8")

        # Parse frontmatter metadata
        frontmatter = parse_frontmatter(raw_text)
        topic = frontmatter.get("topic", md_file.stem)
        source_url = frontmatter.get("source_url", None)
        policy_year = frontmatter.get("policy_year", None)
        canonical_source = frontmatter.get("canonical_source", None)

        # Strip frontmatter — embed body only
        body = strip_frontmatter(raw_text)

        if not body:
            print(f"  ⚠️  Empty body after stripping frontmatter — skipping.")
            continue

        # Chunk the body
        chunks = chunk_document(body)
        print(f"  Chunks: {len(chunks)}")

        # Embed all chunks in one batch call
        embeddings = embeddings_model.embed_documents(chunks)

        # Build rows for BigQuery insertion
        rows = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            rows.append({
                "doc_id": str(uuid.uuid4()),
                "domain": DOMAIN,
                "topic": topic,
                "source_file": md_file.name,
                "source_url": source_url,
                "policy_year": policy_year,
                "canonical_source": canonical_source,
                "content": chunk,
                "embedding": embedding,
            })

        # Insert into BigQuery
        errors = bq_client.insert_rows_json(
            table=TABLE_ID,
            json_rows=rows
        )
        if errors:
            print(f"  ❌ Insert errors: {errors}")
            total_errors += len(errors)
        else:
            print(f"  ✅ Inserted {len(rows)} row(s)")
            total_rows_inserted += len(rows)

        total_chunks += len(chunks)
        print()

    # Summary
    print("─" * 50)
    print(f"Files processed:  {len(md_files)}")
    print(f"Chunks created:   {total_chunks}")
    print(f"Rows inserted:    {total_rows_inserted}")
    print(f"Insert errors:    {total_errors}")
    print("─" * 50)

    if total_errors > 0:
        print("\n⚠️  Some rows failed to insert. Check errors above.")
    else:
        print("\n✅ Ingestion complete. Run test_retrieval.py to verify.")


if __name__ == "__main__":
    main()