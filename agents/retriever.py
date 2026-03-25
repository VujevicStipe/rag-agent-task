import os
import json
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv
from agents.base import BaseAgent
from core.context import AgentContext

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SIMILARITY_THRESHOLD = 0.7
TOP_K = 5
SOURCE_MARGIN = 0.1
REGISTRY_PATH = "data/registry.json"
CHROMA_PATH = "chroma_db"


def load_registry() -> dict:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def deduplicate_chunks(chunks: list[dict], registry: dict) -> list[dict]:
    seen_hashes = {}
    unique = []

    for chunk in chunks:
        content = chunk["document"]
        content_hash = hash(content)
        filename = chunk["metadata"]["filename"]
        has_warning = registry.get(filename, {}).get("warning") is not None

        if content_hash not in seen_hashes:
            seen_hashes[content_hash] = {"chunk": chunk, "has_warning": has_warning}
            unique.append(chunk)
        else:
            existing = seen_hashes[content_hash]
            if existing["has_warning"] and not has_warning:
                unique.remove(existing["chunk"])
                seen_hashes[content_hash] = {"chunk": chunk, "has_warning": has_warning}
                unique.append(chunk)

    return unique


class Retriever(BaseAgent):

    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.collection = self.chroma_client.get_collection("documents")
        self.registry = load_registry()

    def run(self, context: AgentContext) -> AgentContext:
        query = context.standardized_query or context.original_query

        response = client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=query,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
        )
        query_embedding = response.embeddings[0].values

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=TOP_K,
            include=["documents", "metadatas", "distances"]
        )

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        total_chunks = self.collection.count()

        raw_chunks = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            similarity = 1 - dist
            raw_chunks.append({
                "document": doc,
                "metadata": meta,
                "similarity": similarity
            })

        deduped_chunks = deduplicate_chunks(raw_chunks, self.registry)

        top_score = deduped_chunks[0]["similarity"] if deduped_chunks else 0
        top_match = deduped_chunks[0]["metadata"]["filename"] if deduped_chunks else "none"
        top_section = deduped_chunks[0]["metadata"]["section_title"] if deduped_chunks else ""

        if top_score < SIMILARITY_THRESHOLD:
            context.is_answerable = False
            context.retrieved_chunks = []
            context.sources = []
        else:
            # filtriraj chunkove ispod thresholda
            filtered_chunks = [
                c for c in deduped_chunks
                if c["similarity"] >= SIMILARITY_THRESHOLD
            ]

            context.is_answerable = True
            context.retrieved_chunks = filtered_chunks
            context.sources = list(dict.fromkeys([
                f"{c['metadata']['filename']} § {c['metadata']['section_title']} ({round(c['similarity'] * 100, 1)}%)"
                for c in filtered_chunks
                if c["similarity"] >= top_score - SOURCE_MARGIN
            ]))

        self.log_step(context, {
            "total_chunks_searched": total_chunks,
            "top_match": f"{top_match} § {top_section}",
            "top_score": round(top_score, 4),
            "is_answerable": context.is_answerable,
            "sources_found": context.sources
        })

        return context