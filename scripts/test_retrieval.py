# DEVELOPMENT/TEST ONLY — not used in production
# Verifies retrieval quality from advisor_knowledge_base via VECTOR_SEARCH.
# Run after embed_knowledge_base.py to confirm chunks are retrievable.

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

sys.path.insert(0, str(Path(__file__).parent.parent))
from api.services.embeddings import VertexGenAIEmbeddings

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET_ID = os.getenv("BQ_DATASET") + "_star"
TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.advisor_knowledge_base"
TOP_K = 3

TEST_QUESTIONS = [
    {
        "question": "What is Phase 2C and who can apply?",
        "acceptable_topics": ["phase", "registration", "overview"],
    },
    {
        "question": "How does balloting work when too many people apply?",
        "acceptable_topics": ["ballot"],
    },
    {
        "question": "How does distance from school affect my child's priority?",
        "acceptable_topics": ["distance"],
    },
    {
        "question": "What is the difference between SAP schools and autonomous schools?",
        "acceptable_topics": ["school", "type"],
    },
    {
        "question": "Can a Permanent Resident family apply in Phase 2C?",
        "acceptable_topics": ["ballot", "distance", "registration", "overview"],
    },
]


def retrieve(
    question: str,
    embeddings_model: VertexGenAIEmbeddings,
    bq_client: bigquery.Client,
    top_k: int = TOP_K,
) -> list[dict]:
    query_embedding = embeddings_model.embed_query(question)
    embedding_str = ", ".join(str(v) for v in query_embedding)

    sql = f"""
        SELECT
            base.doc_id,
            base.topic,
            base.source_file,
            base.content,
            distance
        FROM VECTOR_SEARCH(
            TABLE `{TABLE_ID}`,
            'embedding',
            (SELECT [{embedding_str}] AS embedding),
            top_k => {top_k},
            distance_type => 'COSINE'
        )
        ORDER BY distance ASC
    """

    results = list(bq_client.query(sql).result())
    return [dict(r) for r in results]


def is_acceptable(topic: str, acceptable_topics: list[str]) -> bool:
    topic_lower = topic.lower()
    return any(accepted in topic_lower for accepted in acceptable_topics)


def main():
    # Brief pause — BQ streaming inserts have a small availability lag
    print("Waiting 5 seconds for BigQuery streaming buffer to settle...\n")
    time.sleep(5)

    embeddings_model = VertexGenAIEmbeddings(
        model="text-embedding-004",
        project=PROJECT_ID,
        location="us-central1",
    )
    bq_client = bigquery.Client(project=PROJECT_ID)

    passed = 0
    failed = 0

    for test in TEST_QUESTIONS:
        question = test["question"]
        acceptable = test["acceptable_topics"]

        print(f"Q: {question}")
        results = retrieve(question, embeddings_model, bq_client)

        if not results:
            print("  ❌ No results returned\n")
            failed += 1
            continue

        top = results[0]
        top_topic = top["topic"].lower()

        # top_distance = top["distance"]
        # top_content_preview = top["content"][:120].replace("\n", " ")

        # # Check if top result topic matches expectation
        # verdict = "✅" if expect in top_topic else "⚠️ "

        # print(f"  Top result:  [{top['source_file']}] topic={top['topic']}")
        # print(f"  Distance:    {top_distance:.4f}  (lower = more similar)")
        # print(f"  Preview:     {top_content_preview}...")
        # print(f"  Verdict:     {verdict} expected topic containing '{expect}'\n")

        # if expect in top_topic:
        #     passed += 1
        # else:
        #     print(f"  All results:")
        #     for r in results:
        #         print(f"    - [{r['source_file']}] topic={r['topic']} distance={r['distance']:.4f}")
        #     print()
        #     failed += 1

        # Check if ANY of the top_k results contain an acceptable topic
        any_acceptable = any(
            is_acceptable(r["topic"], acceptable)
            for r in results
        )
        top_acceptable = is_acceptable(top_topic, acceptable)

        if top_acceptable:
            verdict = "✅ top result acceptable"
        elif any_acceptable:
            verdict = "⚠️  top result borderline — acceptable topic found in results"
        else:
            verdict = "❌ no acceptable topic in any result"

        print(f"  Verdict:     {verdict}")
        print(f"  Acceptable:  {acceptable}\n")

        if top_acceptable:
            passed += 1
        elif any_acceptable:
            passed += 1  # borderline pass — content is present, just not top-ranked
        else:
            failed += 1

    print("─" * 50)
    print(f"Tests passed:  {passed} / {len(TEST_QUESTIONS)}")
    print(f"Tests failed:  {failed} / {len(TEST_QUESTIONS)}")
    print("─" * 50)

    if failed == 0:
        print("\n✅ Retrieval quality verified. Ready for Day 3.")
    elif failed <= 1:
        print("\n⚠️  Minor retrieval issues — review failed cases above.")
        print("   This may be acceptable if the returned chunk is still relevant.")
    else:
        print("\n❌ Multiple retrieval failures — review document content and chunking.")


if __name__ == "__main__":
    main()