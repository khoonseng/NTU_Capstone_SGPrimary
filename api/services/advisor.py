import os
from google.cloud import bigquery as bq
# from langchain_google_community import BigQueryVectorSearch
from langchain_google_community import BigQueryVectorStore
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

from api.services.embeddings import VertexGenAIEmbeddings
from api.config import settings

# ── Constants ──────────────────────────────────────────────────────────────────
PROJECT_ID = settings.gcp_project_id
DATASET_ID = f"{os.getenv('BQ_DATASET', 'sg_moe')}_star"
VECTOR_TABLE = "advisor_knowledge_base"
LOCATION = "us-central1"
GROQ_MODEL="llama-3.3-70b-versatile"
EMBEDDINGS_MODEL="text-embedding-004"

SYSTEM_PROMPT = """You are a helpful P1 school registration advisor for Singapore parents.
You help parents understand the P1 registration process, ballot risk, and school \
choices based on historical balloting data from 2019 to 2025.

Answer only questions related to Singapore primary school P1 registration, balloting, \
school selection, and related topics. For questions outside this scope, politely \
explain that you can only assist with P1 registration topics.

Use the context below to answer the question. If the context does not contain enough \
information to answer confidently, say so clearly rather than guessing.

MOE policy context:
{policy_context}

School balloting data:
{school_context}
"""


# ── Embeddings + Retriever ─────────────────────────────────────────────────────

def _get_embeddings_model() -> VertexGenAIEmbeddings:
    return VertexGenAIEmbeddings(
        model=EMBEDDINGS_MODEL,
        project=PROJECT_ID,
        location=LOCATION,
    )


def _get_vector_store() -> BigQueryVectorStore:
    # return BigQueryVectorSearch(
    #     project_id=PROJECT_ID,
    #     dataset_name=DATASET_ID,
    #     table_name=VECTOR_TABLE,
    #     location="US",
    #     embedding=_get_embeddings_model(),
    #     content_field="content",
    #     metadata_fields=["domain", "topic", "source_file", "source_url"],
    #     text_embedding_field="embedding",  # overrides default 'text_embedding'
    # )

    return BigQueryVectorStore(
        project_id=PROJECT_ID,
        dataset_name=DATASET_ID,
        table_name=VECTOR_TABLE,
        location="US",
        embedding=_get_embeddings_model(),
        content_field="content",
        embedding_field="embedding",
        doc_id_field="doc_id",
        extra_fields={
            "domain": "STRING",
            "topic": "STRING",
            "source_file": "STRING",
            "source_url": "STRING",
        },
        distance_type="COSINE",
    )


def retrieve_policy_context(question: str, top_k: int = 3) -> list[Document]:
    """
    Embed the question and retrieve top_k relevant MOE policy chunks
    from BigQuery vector search. Returns LangChain Document objects.
    """
    store = _get_vector_store()
    return store.similarity_search(
        query=question,
        k=top_k,
        filter={"domain": "moe_policy"},
    )


def format_docs(docs: list[Document]) -> str:
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


# ── SQL School Context ─────────────────────────────────────────────────────────

def fetch_school_context(school_name: str) -> str:
    """
    Query mart_school_analysis for recent balloting history for a given school.
    Returns formatted string for injection into the LLM prompt.
    Returns empty string if no data found.
    """
    client = bq.Client(project=PROJECT_ID)
    query = f"""
        SELECT
            registration_year,
            phase_normalised,
            vacancy,
            applied,
            taken,
            subscription_rate,
            ballot_risk_level,
            ballot_occurrences_last_3yr,
            subscription_rate_3yr_avg
        FROM `{PROJECT_ID}.{DATASET_ID}.mart_school_analysis`
        WHERE UPPER(TRIM(school_name_clean)) = UPPER(TRIM(@school_name))
          AND registration_year >= 2022
        ORDER BY registration_year DESC, phase_normalised
        LIMIT 20
    """
    job_config = bq.QueryJobConfig(
        query_parameters=[
            bq.ScalarQueryParameter("school_name", "STRING", school_name)
        ]
    )
    rows = list(client.query(query, job_config=job_config).result())

    if not rows:
        return ""

    lines = [f"School: {school_name}"]
    for r in rows:
        lines.append(
            f"  {r['registration_year']} {r['phase_normalised']}: "
            f"vacancy={r['vacancy']}, applied={r['applied']}, "
            f"taken={r['taken']}, "
            f"subscription_rate={r['subscription_rate']}, "
            f"ballot_risk={r['ballot_risk_level']}, "
            f"ballot_occurrences_last_3yr={r['ballot_occurrences_last_3yr']}, "
            f"subscription_rate_3yr_avg={r['subscription_rate_3yr_avg']}"
        )
    return "\n".join(lines)


# ── LLM Chain ─────────────────────────────────────────────────────────────────

def _get_chain():
    llm = ChatGroq(
        model=GROQ_MODEL,
        api_key=settings.groq_api_key,
        max_tokens=500,
        temperature=0.3,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{question}"),
    ])
    return prompt | llm | StrOutputParser()


# ── Public interface ───────────────────────────────────────────────────────────

def run_advisor(
    question: str,
    school_name: str | None = None,
    conversation_history: list[dict] | None = None,  # unused in Week 4
) -> dict:
    """
    Main entry point for the advisor service.
    Returns dict with answer, sources, school_context_used, disclaimer.
    """
    # 1. Retrieve policy context
    policy_docs = retrieve_policy_context(question)
    policy_context = format_docs(policy_docs)
    sources = [
        {
            "topic": d.metadata.get("topic", ""),
            "source_file": d.metadata.get("source_file", ""),
            "source_url": d.metadata.get("source_url", ""),
        }
        for d in policy_docs
    ]

    # 2. Fetch SQL school context if school_name provided
    school_context = "No specific school data requested."
    school_context_used = False
    if school_name:
        fetched = fetch_school_context(school_name)
        if fetched:
            school_context = fetched
            school_context_used = True

    # 3. Run the LangChain chain
    chain = _get_chain()
    answer = chain.invoke({
        "question": question,
        "policy_context": policy_context,
        "school_context": school_context,
    })

    return {
        "answer": answer,
        "sources": sources,
        "school_context_used": school_context_used,
        "disclaimer": (
            "This assessment is based on historical balloting data (2019–2025) "
            "and MOE published guidelines. Always verify with MOE's official "
            "P1 registration portal before making decisions."
        ),
    }