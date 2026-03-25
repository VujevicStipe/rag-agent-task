import os
import time
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def embed_and_store(chunks: list[dict], chroma_path: str = "chroma_db"):
    chroma_client = chromadb.PersistentClient(path=chroma_path)

    collection = chroma_client.get_or_create_collection(
        name="documents",
        metadata={"hnsw:space": "cosine"}
    )

    print(f"\nEmbedding {len(chunks)} chunks...")

    for i, chunk in enumerate(chunks):
        response = client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=chunk["content"],
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )

        embedding = response.embeddings[0].values

        collection.add(
            ids=[chunk["content_hash"]],
            embeddings=[embedding],
            documents=[chunk["content"]],
            metadatas=[{
                "filename": chunk["filename"],
                "section_title": chunk["section_title"],
                "chunk_index": chunk["chunk_index"]
            }]
        )

        print(f"[{i+1}/{len(chunks)}] {chunk['filename']} § {chunk['section_title']}")
        time.sleep(0.5)

    print(f"\nDone. {len(chunks)} chunks stored in ChromaDB.")
    return collection