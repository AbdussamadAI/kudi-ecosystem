"""
RAG Document Ingestion Script
Chunks and embeds documents (e.g., Nigeria Tax Act 2025) into pgvector
via Supabase for retrieval-augmented generation.

Usage:
    python -m scripts.ingest_documents --file path/to/document.pdf --name "Nigeria Tax Act 2025"
"""

import argparse
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using PyMuPDF (fitz)."""
    import fitz

    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def extract_text_from_txt(file_path: str) -> str:
    """Read a plain text file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_text(file_path: str) -> str:
    """Extract text from a file based on its extension."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in (".txt", ".md"):
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use .pdf, .txt, or .md")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    Split text into overlapping chunks by sentences.
    Each chunk is roughly `chunk_size` words with `overlap` words of overlap.
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)

        # Clean up whitespace
        chunk_text = " ".join(chunk_text.split())

        if chunk_text.strip():
            chunks.append({
                "index": len(chunks),
                "content": chunk_text,
                "word_count": len(chunk_words),
                "char_count": len(chunk_text),
            })

        start += chunk_size - overlap

    return chunks


def embed_chunks(chunks: list[dict], model: SentenceTransformer) -> list[dict]:
    """Generate embeddings for each chunk."""
    texts = [c["content"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    for i, chunk in enumerate(chunks):
        chunk["embedding"] = embeddings[i].tolist()

    return chunks


def upload_to_supabase(chunks: list[dict], document_name: str):
    """Upload chunks with embeddings to Supabase document_embeddings table."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    # Delete existing chunks for this document (re-ingestion)
    supabase.table("document_embeddings").delete().eq("document_name", document_name).execute()

    batch_size = 50
    total = len(chunks)

    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]
        rows = []
        for chunk in batch:
            rows.append({
                "id": str(uuid.uuid4()),
                "document_name": document_name,
                "chunk_index": chunk["index"],
                "content": chunk["content"],
                "metadata": {
                    "word_count": chunk["word_count"],
                    "char_count": chunk["char_count"],
                },
                "embedding": chunk["embedding"],
            })

        supabase.table("document_embeddings").insert(rows).execute()
        print(f"  Uploaded {min(i + batch_size, total)}/{total} chunks")


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into KudiWise RAG")
    parser.add_argument("--file", required=True, help="Path to the document file (.pdf, .txt, .md)")
    parser.add_argument("--name", required=True, help="Document name (e.g., 'Nigeria Tax Act 2025')")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE, help=f"Words per chunk (default: {CHUNK_SIZE})")
    parser.add_argument("--overlap", type=int, default=CHUNK_OVERLAP, help=f"Overlap words (default: {CHUNK_OVERLAP})")
    args = parser.parse_args()

    file_path = args.file
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print(f"📄 Extracting text from: {file_path}")
    text = extract_text(file_path)
    print(f"   Extracted {len(text):,} characters")

    print(f"✂️  Chunking text (size={args.chunk_size}, overlap={args.overlap})")
    chunks = chunk_text(text, chunk_size=args.chunk_size, overlap=args.overlap)
    print(f"   Created {len(chunks)} chunks")

    print(f"🧠 Generating embeddings with {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    chunks = embed_chunks(chunks, model)
    print(f"   Embedded {len(chunks)} chunks (dim={len(chunks[0]['embedding'])})")

    print(f"☁️  Uploading to Supabase as '{args.name}'")
    upload_to_supabase(chunks, args.name)
    print(f"✅ Done! {len(chunks)} chunks ingested for '{args.name}'")


if __name__ == "__main__":
    main()
