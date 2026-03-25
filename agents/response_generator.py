import os
from google import genai
from dotenv import load_dotenv
from agents.base import BaseAgent
from core.context import AgentContext

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

NOT_FOUND_MESSAGE = """I was unable to find relevant information in the company documents to answer this question.

If you believe this information should be available, please check with your manager or HR directly."""

FACTUAL_PROMPT = """You are a company document assistant. Answer the question based ONLY on the provided document excerpts.
Do not use any external knowledge. If the excerpts do not contain enough information, say so clearly.

Document excerpts:
{context}

Question: {query}

Provide a clear, concise answer based only on the documents above."""

PROCEDURAL_PROMPT = """You are a company document assistant. The user needs step-by-step guidance or a checklist.
Based ONLY on the provided document excerpts, create a clear checklist or step-by-step guide.
Do not use any external knowledge.

Be concise and focused. Highlight only the most critical steps directly relevant to the question. 
Avoid listing every possible detail from the document. Aim for clarity over completeness.
If the user explicitly asks for details, a comprehensive list, or all steps — then provide the full list.

Document excerpts:
{context}

Request: {query}

Format your response as a checklist with checkboxes (□) or numbered steps."""

SUMMARIZATION_PROMPT = """You are a company document assistant. Summarize the provided document excerpts.
Base your summary ONLY on the provided content. Do not add external knowledge.

Document excerpts:
{context}

Request: {query}

If the document content is not interpretable, meaningful, or consists only of symbols or random words,
respond with a brief, user-friendly message stating that the document exists but cannot be summarized.
Suggest the user contact their manager or reach out via email at support@company.com if they believe
this document should contain meaningful content.

Otherwise, provide a structured summary of the document content."""


def build_context(chunks: list[dict], registry: dict) -> str:
    parts = []
    for chunk in chunks:
        filename = chunk["metadata"]["filename"]
        section = chunk["metadata"]["section_title"]
        content = chunk["document"]
        warning = registry.get(filename, {}).get("warning")

        header = f"[{filename} § {section}]"
        if warning:
            header += f" ⚠️ WARNING: This document is marked as '{warning}'"

        parts.append(f"{header}\n{content}")

    return "\n\n---\n\n".join(parts)


class ResponseGenerator(BaseAgent):

    def __init__(self, registry: dict):
        self.registry = registry

    def run(self, context: AgentContext) -> AgentContext:
        if not context.is_answerable:
            context.answer = NOT_FOUND_MESSAGE
            self.log_step(context, {
                "response_type": "NOT_FOUND",
                "sources": []
            })
            return context

        doc_context = build_context(context.retrieved_chunks, self.registry)
        query = context.standardized_query or context.original_query

        if context.query_type == "PROCEDURAL":
            prompt = PROCEDURAL_PROMPT.format(context=doc_context, query=query)
        elif context.query_type == "SUMMARIZATION":
            prompt = SUMMARIZATION_PROMPT.format(context=doc_context, query=query)
        else:
            prompt = FACTUAL_PROMPT.format(context=doc_context, query=query)

        response = client.models.generate_content(
            model="models/gemini-2.5-flash-lite",
            contents=prompt
        )

        context.answer = response.text

        self.log_step(context, {
            "response_type": context.query_type,
            "sources": context.sources
        })

        return context