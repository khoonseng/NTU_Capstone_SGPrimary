# DEVELOPMENT/TEST ONLY — not used in production
import os
from dotenv import load_dotenv
from langchain_google_vertexai import VertexAIEmbeddings

load_dotenv()

embeddings_model = VertexAIEmbeddings(
    model_name="text-embedding-004",
    project=os.getenv("GCP_PROJECT_ID"),
    location="us-central1",
)

texts = [
    "What is Phase 2C in Singapore primary school registration?",
    "How does balloting work when a school is oversubscribed?",
]

vectors = embeddings_model.embed_documents(texts)
print(f"Number of embeddings: {len(vectors)}")
print(f"Embedding dimensions: {len(vectors[0])}")  # expect 768
print(f"First 5 values of embedding 1: {vectors[0][:5]}")
print(f"First 5 values of embedding 2: {vectors[1][:5]}")