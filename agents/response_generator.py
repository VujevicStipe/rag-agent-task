import os
import yaml
from pathlib import Path
from google import genai
from dotenv import load_dotenv
from agents.base import BaseAgent
from core.context import AgentContext

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

config = yaml.safe_load(Path("config/retrieval.yaml").read_text(encoding="utf-8"))
support_email = config.get("support_email", "support@company.com")

NOT_FOUND_MESSAGE = Path("config/prompts/not_found.txt").read_text(encoding="utf-8")
FACTUAL_PROMPT = Path("config/prompts/response_factual.txt").read_text(encoding="utf-8")
PROCEDURAL_PROMPT = Path("config/prompts/response_procedural.txt").read_text(encoding="utf-8")
SUMMARIZATION_PROMPT = Path("config/prompts/response_summarization.txt").read_text(encoding="utf-8")
UNINTERPRETABLE = Path("config/prompts/uninterpretable_content.txt").read_text(encoding="utf-8").format(support_email=support_email)
FLAGGED_DOCUMENT_TEMPLATE = Path("config/prompts/flagged_document.txt").read_text(encoding="utf-8")


def build_context(chunks: list[dict]) -> str:
    parts = []
    for chunk in chunks:
        filename = chunk["metadata"]["filename"]
        section = chunk["metadata"]["section_title"]
        content = chunk["document"]
        header = f"[{filename} § {section}]"
        parts.append(f"{header}\n{content}")

    return "\n\n---\n\n".join(parts)


class ResponseGenerator(BaseAgent):

    def run(self, context: AgentContext) -> AgentContext:
        if not context.is_answerable:
            if not context.answer:
                context.answer = NOT_FOUND_MESSAGE
            self.log_step(context, {
                "response_type": "NOT_FOUND",
                "sources": []
            })
            return context

        doc_context = build_context(context.retrieved_chunks)
        query = context.standardized_query or context.original_query

        if context.flagged_sources:
            flagged_list = "\n".join(f"- {s}" for s in context.flagged_sources)
            doc_context += "\n\n" + FLAGGED_DOCUMENT_TEMPLATE.format(
                flagged_list=flagged_list,
                support_email=support_email
            )

        if context.query_type == "PROCEDURAL":
            prompt = PROCEDURAL_PROMPT.format(context=doc_context, query=query)
        elif context.query_type == "SUMMARIZATION":
            prompt = SUMMARIZATION_PROMPT.format(context=doc_context, query=query)
        else:
            prompt = FACTUAL_PROMPT.format(context=doc_context, query=query)

        prompt += "\n\n" + UNINTERPRETABLE

        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt
        )

        context.answer = response.text

        self.log_step(context, {
            "response_type": context.query_type,
            "sources": context.sources,
            "flagged_sources": context.flagged_sources
        })

        return context