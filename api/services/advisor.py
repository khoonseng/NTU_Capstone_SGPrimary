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
DATASET_ID = f"{settings.bq_dataset}_star"
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

You must only use information from the context provided below. \
Do not use your training knowledge to answer questions about specific schools, \
school lists, or school attributes. If the context does not contain the answer, \
say exactly: "I don't have that information in my knowledge base. For school \
discovery by location or type, please use the Schools or Recommendations page \
on this app.". Do not guess, infer, or supplement with outside knowledge.

When school balloting data is provided, include it in your response to help parents \
understand the specific schools they are considering. Always mention the most recent \
year's vacancy, applied, taken, subscription rate and ballot risk for each phase. \
If ballot risk is N/A, it means that the phase was not opened and signals high competition \
because all vacancies were taken in the earlier phase. Present this information to parents in \
a coherent manner instead of displaying N/A value which might confuse parents.


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

# Threshold above which we consider the question out of knowledge base scope
OUT_OF_SCOPE_DISTANCE = 0.65

def retrieve_policy_context_with_scores(
    question: str,
    top_k: int = 3
) -> tuple[list, float]:
    """
    Returns (docs, best_distance).
    Uses similarity_search_with_score to get distance values.
    """
    store = _get_vector_store()
    results = store.similarity_search_with_score(
        query=question,
        k=top_k,
        filter={"domain": "moe_policy"},
    )
    if not results:
        return [], 1.0
    docs = [r[0] for r in results]
    best_distance = min(r[1] for r in results)
    return docs, best_distance

def format_docs(docs: list[Document]) -> str:
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


# ── SQL School Context ─────────────────────────────────────────────────────────

def fetch_school_context(school_names: list[str]) -> str:
    """
    For each school name, fetch:
    1. Balloting history from mart_school_analysis (structured trend data)
    2. General info from dim_school + dim_school_generalinfo (attributes, contact)

    Returns formatted string for injection into the LLM prompt.
    Returns empty string if no data found for any school.
    """
    if not school_names:
        return ""

    client = bq.Client(project=PROJECT_ID)
    sections = []

    for school_name in school_names:
        school_upper = school_name.upper().strip()
        school_sections = []

        # --- Query 1: Balloting history ---
        ballot_query = f"""
            WITH latest_year AS (
                SELECT MAX(registration_year) AS max_year
                FROM `{PROJECT_ID}.{DATASET_ID}.mart_school_analysis`
                WHERE UPPER(TRIM(school_name_clean)) = @school_name
            )
            SELECT
                m.registration_year,
                m.phase_normalised,
                m.vacancy,
                m.applied,
                m.taken,
                m.subscription_rate,
                CASE 
                    WHEN m.vacancy = 0
                    THEN 'N/A' 
                    
                    ELSE
                        m.ballot_risk_level

                END as ballot_risk_level
            FROM `{PROJECT_ID}.{DATASET_ID}.mart_school_analysis` m
            JOIN latest_year l ON m.registration_year = l.max_year
            WHERE UPPER(TRIM(m.school_name_clean)) = @school_name
            ORDER BY m.phase_normalised
        """
        
        ballot_job = bq.QueryJobConfig(
            query_parameters=[
                bq.ScalarQueryParameter("school_name", "STRING", school_upper)
            ]
        )
        ballot_rows = list(client.query(ballot_query, job_config=ballot_job).result())

        if ballot_rows:
            year = ballot_rows[0]['registration_year']
            lines = [f"\n## {year} Balloting Data: {school_name}"]
            for r in ballot_rows:
                lines.append(
                    f"- Phase {r['phase_normalised']}: "
                    f"vacancy={r['vacancy']}, "
                    f"applied={r['applied']}, "
                    f"taken={r['taken']}, "
                    f"subscription_rate={r['subscription_rate']}, "
                    f"ballot_risk={r['ballot_risk_level']}"
                )
            school_sections.append("\n".join(lines))

        # --- Query 2: School general info (joined dim_school + dim_school_generalinfo) ---
        info_query = f"""
            SELECT
                s.school_name_clean,
                s.address,
                s.postal_code,
                s.zone_code,
                s.dgp_code,
                s.type_code,
                s.nature_code,
                s.session_code,
                s.sap_ind,
                s.autonomous_ind,
                s.gifted_ind,
                s.ip_ind,
                s.mothertongue1_code,
                s.mothertongue2_code,
                s.mothertongue3_code,
                s.school_status,
                s.school_status_description,
                g.url_address,
                g.mrt_desc,
                g.bus_desc,
                g.principal_name
            FROM `{PROJECT_ID}.{DATASET_ID}.dim_school` s
            LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.dim_school_generalinfo` g
                ON s.school_key = g.school_key
            WHERE UPPER(TRIM(s.school_name_clean)) = @school_name
            LIMIT 1
        """
        info_job = bq.QueryJobConfig(
            query_parameters=[
                bq.ScalarQueryParameter("school_name", "STRING", school_upper)
            ]
        )
        info_rows = list(client.query(info_query, job_config=info_job).result())

        if info_rows:
            r = info_rows[0]
            lines = [f"\n## School Information: {school_name}"]
            lines.append(f"  Address: {r['address']}, Singapore {r['postal_code']}")
            lines.append(f"  Zone: {r['zone_code']}, Estate: {r['dgp_code']}")
            lines.append(f"  Type: {r['type_code']}, Nature: {r['nature_code']}")
            lines.append(f"  Session: {r['session_code']}")
            lines.append(
                f"  Special programmes: "
                f"SAP={r['sap_ind']}, GEP={r['gifted_ind']}, "
                f"Autonomous={r['autonomous_ind']}, IP={r['ip_ind']}"
            )
            lines.append(
                f"  Mother tongue: {r['mothertongue1_code']}"
                + (f", {r['mothertongue2_code']}" if r['mothertongue2_code'] else "")
            )
            if r['mrt_desc']:
                lines.append(f"  MRT: {r['mrt_desc']}")
            if r['bus_desc']:
                lines.append(f"  Bus: {r['bus_desc']}")
            if r['principal_name']:
                lines.append(f"  Principal: {r['principal_name']}")
            if r['url_address']:
                lines.append(f"  Website: {r['url_address']}")
            lines.append(f"  Status: {r['school_status_description']}")
            school_sections.append("\n".join(lines))

        if school_sections:
            sections.extend(school_sections)

    return "\n".join(sections)


# ── LLM Chain ─────────────────────────────────────────────────────────────────

def _get_chain():
    llm = ChatGroq(
        model=GROQ_MODEL,
        api_key=settings.groq_api_key,
        max_tokens=750,
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
    school_names: list[str] | None = None,     # changed from school_name
    conversation_history: list[dict] | None = None,  # unused in Week 4
) -> dict:
    """
    Main entry point for the advisor service.
    Returns dict with answer, sources, school_context_used, disclaimer.
    """
    # 1. Retrieve policy context
    # policy_docs = retrieve_policy_context(question)

    # 1. Retrieve policy context with distance check
    policy_docs, best_distance = retrieve_policy_context_with_scores(question)
    
    # If no schools selected and retrieval quality is poor,
    # return structured fallback without calling the LLM
    if best_distance > OUT_OF_SCOPE_DISTANCE and not school_names:
        return {
            "answer": (
                "I don't have specific information about that in my knowledge base. "
                "For school discovery by location, type, or special programmes, "
                "please use the Schools page on this app. "
                "For ballot risk by area and phase, please use the Recommendations page."
            ),
            "sources": [],
            "school_context_used": False,
            "disclaimer": (
                "This assessment is based on historical balloting data (2019–2025) "
                "and MOE published guidelines. Always verify with MOE's official "
                "P1 registration portal before making decisions."
            ),
        }


    policy_context = format_docs(policy_docs)
    sources = [
        {
            "topic": d.metadata.get("topic", ""),
            "source_file": d.metadata.get("source_file", ""),
            "source_url": d.metadata.get("source_url", ""),
        }
        for d in policy_docs
    ]

    # 2. Fetch SQL school context if school_names provided
    school_context = "No specific school data requested."
    school_context_used = False
    if school_names:
        fetched = fetch_school_context(school_names)
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

    # Append redirect sentence deterministically
    if school_context_used:
        answer += (
            "\n\nFor full historical trend data across all years, "
            "parents can visit the Recommendations page on this app."
        )

    return {
        "answer": answer,
        "sources": sources,
        "school_context_used": school_context_used,
        "disclaimer": (
            "This assessment is based on historical balloting data (2019–2025) "
            "and MOE published guidelines. Always verify with MOE's official "
            "P1 registration portal before making decisions."
        ),
        # Temporary debug fields — remove before deployment
        # "_debug_best_distance": round(best_distance, 4),
        # "_debug_school_names": school_names,
    }