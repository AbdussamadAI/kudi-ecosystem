"""
Embedding Pipeline
Handles document chunking, embedding generation, and vector storage
for the RAG system using the Nigeria Tax Act 2025 and other documents.
"""

import os
from pathlib import Path

from llama_index.core import (
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    Settings as LlamaSettings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from app.config import get_settings


settings = get_settings()

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIMENSION = 384
TABLE_NAME = "document_embeddings"


def get_embed_model() -> HuggingFaceEmbedding:
    return HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)


def get_vector_store() -> PGVectorStore:
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    return PGVectorStore.from_params(
        database=db_url.split("/")[-1].split("?")[0],
        host=db_url.split("@")[1].split(":")[0] if "@" in db_url else "localhost",
        port=db_url.split(":")[-1].split("/")[0] if db_url.count(":") > 1 else "5432",
        user=db_url.split("://")[1].split(":")[0],
        password=db_url.split(":")[2].split("@")[0] if db_url.count(":") > 2 else "",
        table_name=TABLE_NAME,
        embed_dim=EMBED_DIMENSION,
    )


def ingest_documents(documents_dir: str) -> VectorStoreIndex:
    """
    Ingest PDF/text documents from a directory into the vector store.
    Used to load the Nigeria Tax Act 2025 and other tax law documents.
    """
    embed_model = get_embed_model()
    LlamaSettings.embed_model = embed_model

    node_parser = SentenceSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    documents = SimpleDirectoryReader(
        input_dir=documents_dir,
        recursive=True,
    ).load_data()

    vector_store = get_vector_store()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        transformations=[node_parser],
        show_progress=True,
    )

    return index


def get_query_engine(similarity_top_k: int = 5):
    """
    Get a query engine for retrieving relevant tax law sections.
    Used by the AI assistant to ground responses in actual law text.
    """
    embed_model = get_embed_model()
    LlamaSettings.embed_model = embed_model

    vector_store = get_vector_store()
    index = VectorStoreIndex.from_vector_store(vector_store)

    return index.as_query_engine(
        similarity_top_k=similarity_top_k,
    )


def retrieve_context(query: str, top_k: int = 5) -> list[dict]:
    """
    Retrieve relevant document chunks for a given query.
    Returns a list of chunks with text and metadata.
    """
    embed_model = get_embed_model()
    LlamaSettings.embed_model = embed_model

    vector_store = get_vector_store()
    index = VectorStoreIndex.from_vector_store(vector_store)

    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)

    results = []
    for node in nodes:
        results.append({
            "text": node.get_content(),
            "score": node.get_score(),
            "metadata": node.metadata if hasattr(node, "metadata") else {},
        })

    return results
