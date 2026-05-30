import os
from google import genai
from google.genai import types
from langchain_core.embeddings import Embeddings


class VertexGenAIEmbeddings(Embeddings):
    """
    LangChain Embeddings adapter backed by google-genai Client with Vertex AI.
    Uses task_type distinction between document ingestion and query embedding
    for optimal retrieval quality with text-embedding-004.
    """

    def __init__(self, *, model: str, project: str, location: str) -> None:
        if not project:
            raise ValueError("GCP project must be provided.")
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