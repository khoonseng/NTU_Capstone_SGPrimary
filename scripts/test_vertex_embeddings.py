# DEVELOPMENT/TEST ONLY — not used in production
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from langchain_core.embeddings import Embeddings


class VertexGenAIEmbeddings(Embeddings):
    def __init__(self, *, model: str, project: str, location: str) -> None:
        if not project:
            raise ValueError("GCP_PROJECT_ID must be set in the environment.")

        self.model = model
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=texts,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        return [embedding.values for embedding in response.embeddings]

    def embed_query(self, text: str) -> list[float]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return response.embeddings[0].values

# ---------- MAIN ----------
if __name__ == "__main__":
    load_dotenv()

    embeddings_model = VertexGenAIEmbeddings(
        model="text-embedding-004",
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
