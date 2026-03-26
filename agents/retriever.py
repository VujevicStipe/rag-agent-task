import os
import json
import yaml
import chromadb
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv
from agents.base import BaseAgent
from core.context import AgentContext

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

config = yaml.safe_load(Path("config/retrieval.yaml").read_text(encoding="utf-8"))
SIMILARITY_THRESHOLD = config["similarity_threshold"]
TOP_K = config["top_k"]
SOURCE_MARGIN = config["source_margin"]
REGISTRY_PATH = config["registry_path"]
CHROMA_PATH = config["chroma_path"]

FLAGGED_MESSAGE = Path("config/prompts/flagged_document.txt").read_text(encoding="utf-8").format(
    support_email=config.get("support_email", "support@company.com"),
    flagged_list="(see sources above)"
)


def load_registry() -> dict:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


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
            warning = self.registry.get(meta["filename"], {}).get("warning")
            raw_chunks.append({
                "document": doc,
                "metadata": meta,
                "similarity": similarity,
                "warning": warning
            })

        top_score = raw_chunks[0]["similarity"] if raw_chunks else 0
        top_match = raw_chunks[0]["metadata"]["filename"] if raw_chunks else "none"
        top_section = raw_chunks[0]["metadata"]["section_title"] if raw_chunks else ""

        if top_score < SIMILARITY_THRESHOLD:
            context.is_answerable = False
            context.retrieved_chunks = []
            context.sources = []
            context.flagged_sources = []
        else:
            filtered_chunks = [
                c for c in raw_chunks
                if c["similarity"] >= SIMILARITY_THRESHOLD
            ]

            context_chunks = [c for c in filtered_chunks if not c["warning"]]
            source_chunks = [c for c in filtered_chunks if c["similarity"] >= top_score - SOURCE_MARGIN]

            context.sources = list(dict.fromkeys([
                f"{c['metadata']['filename']} § {c['metadata']['section_title']} ({round(c['similarity'] * 100, 1)}%)"
                for c in source_chunks
                if not c["warning"]
            ]))

            context.flagged_sources = list(dict.fromkeys([
                f"{c['metadata']['filename']} § {c['metadata']['section_title']} ({round(c['similarity'] * 100, 1)}%) — {c['warning']}"
                for c in source_chunks
                if c["warning"]
            ]))

            if not context_chunks:
                context.is_answerable = False
                context.answer = FLAGGED_MESSAGE
                context.retrieved_chunks = []
            else:
                context.is_answerable = True
                context.retrieved_chunks = context_chunks

        self.log_step(context, {
            "total_chunks_searched": total_chunks,
            "top_match": f"{top_match} § {top_section}",
            "top_score": round(top_score, 4),
            "is_answerable": context.is_answerable,
            "sources_found": context.sources,
            "flagged_found": context.flagged_sources
        })

        return context