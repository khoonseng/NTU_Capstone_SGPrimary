import os
import uuid
from dotenv import load_dotenv
from google.cloud import bigquery
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.services.embeddings import VertexGenAIEmbeddings
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET_ID = os.getenv("BQ_DATASET") + "_star"
VECTOR_TABLE_NAME = "advisor_knowledge_base"

# Step 1: Insert one dummy document
bq_client = bigquery.Client(project=PROJECT_ID)
bq_table_id = f"{PROJECT_ID}.{DATASET_ID}.{VECTOR_TABLE_NAME}"

embeddings_model = VertexGenAIEmbeddings(
    model="text-embedding-004",
    project=PROJECT_ID,
    location="us-central1",
)

dummy_text = "Phase 2C is the open registration phase for Singapore primary schools."
dummy_embedding = embeddings_model.embed_documents([dummy_text])[0]

row = [{
    "doc_id": str(uuid.uuid4()),
    "domain": "moe_policy",
    "topic": "test_document",
    "source_file": "test",
    "content": dummy_text,
    "embedding": dummy_embedding,
}]

errors = bq_client.insert_rows_json(
    table=bq_table_id,
    json_rows=row
)

if errors:
    print(f"Insert errors: {errors}")
else:
    print("Insert successful")

# Step 2: Embed a query and run VECTOR_SEARCH manually
import time
time.sleep(3)  # BQ streaming insert has a small lag

query_embedding = embeddings_model.embed_query(
    "What is Phase 2C?"
)
embedding_str = ", ".join(str(v) for v in query_embedding)

sql = f"""
SELECT base.doc_id, base.content, base.domain, distance
FROM VECTOR_SEARCH(
    TABLE `test-sg-moe.sg_moe_star.advisor_knowledge_base`,
    'embedding',
    (SELECT [{embedding_str}] AS embedding),
    top_k => 3,
    distance_type => 'COSINE'
)
ORDER BY distance ASC
"""

results = list(bq_client.query(sql).result())
print(f"\nRetrieved {len(results)} document(s):")
for r in results:
    print(f"  - {r['content'][:80]}... (distance: {r['distance']:.4f})")

# Step 3: Call Groq with retrieved context
context = "\n\n".join([r["content"] for r in results])
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    max_tokens=200,
)

messages = [
    SystemMessage(content="You are a helpful Singapore P1 school registration advisor. Use the context below.\n\n" + context),
    HumanMessage(content="What is Phase 2C in Singapore primary school registration?"),
]

response = llm.invoke(messages)
print(f"\nLLM response:\n{response.content}")