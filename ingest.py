import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ingestion.loader import load_documents
from ingestion.document_registry import build_registry, save_registry
from ingestion.chunker import chunk_all_documents
from ingestion.embedder import embed_and_store

DOCUMENTS_DIR = "documents"
REGISTRY_PATH = "data/registry.json"
CHROMA_PATH = "chroma_db"


def main():
    print("=" * 50)
    print(" INGESTION PIPELINE")
    print("=" * 50)

    # Step 1: Load documents
    print("\n[1] Loading documents...")
    documents = load_documents(DOCUMENTS_DIR)

    # Step 2: Build document registry
    print("\n[2] Building document registry...")
    registry = build_registry(documents)
    save_registry(registry, REGISTRY_PATH)

    # Step 3: Chunk documents
    print("\n[3] Chunking documents...")
    chunks = chunk_all_documents(documents)

    # Step 4: Embed and store
    print("\n[4] Embedding and storing in ChromaDB...")
    embed_and_store(chunks, CHROMA_PATH)

    print("\n" + "=" * 50)
    print(" INGESTION COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()