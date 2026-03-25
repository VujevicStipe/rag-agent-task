import os
from pathlib import Path
from google import genai
from dotenv import load_dotenv
from agents.base import BaseAgent
from core.context import AgentContext

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

QUERY_TYPES = ["FACTUAL", "PROCEDURAL", "SUMMARIZATION"]
PROMPT_TEMPLATE = Path("config/prompts/query_analyzer.txt").read_text(encoding="utf-8")


class QueryAnalyzer(BaseAgent):

    def run(self, context: AgentContext) -> AgentContext:
        prompt = PROMPT_TEMPLATE.format(query=context.original_query)

        response = client.models.generate_content(
            model="models/gemini-2.5-flash-lite",
            contents=prompt
        )

        result = self._parse_response(response.text)

        context.standardized_query = result["standardized"]
        context.query_type = result["type"]
        context.search_terms = result["terms"]

        self.log_step(context, {
            "original_query": context.original_query,
            "standardized_query": context.standardized_query,
            "query_type": context.query_type,
            "search_terms": context.search_terms
        })

        return context

    def _parse_response(self, text: str) -> dict:
        lines = text.strip().split("\n")
        result = {
            "standardized": "",
            "type": "FACTUAL",
            "terms": []
        }

        for line in lines:
            if line.startswith("STANDARDIZED:"):
                result["standardized"] = line.replace("STANDARDIZED:", "").strip()
            elif line.startswith("TYPE:"):
                query_type = line.replace("TYPE:", "").strip()
                result["type"] = query_type if query_type in QUERY_TYPES else "FACTUAL"
            elif line.startswith("TERMS:"):
                terms_str = line.replace("TERMS:", "").strip()
                result["terms"] = [t.strip() for t in terms_str.split(",")]

        return result