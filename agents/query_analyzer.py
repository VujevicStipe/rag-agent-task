import os
from google import genai
from dotenv import load_dotenv
from agents.base import BaseAgent
from core.context import AgentContext

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

QUERY_TYPES = ["FACTUAL", "PROCEDURAL", "SUMMARIZATION"]

PROMPT_TEMPLATE = """You are a query analyzer for a company document assistant.

Given the user's question, you must:
1. Standardize the question (fix typos, make it formal and clear)
2. Classify the query type as one of: FACTUAL, PROCEDURAL, SUMMARIZATION
3. Extract key search terms

Definitions:
- FACTUAL: User wants a specific fact or piece of information 
  (e.g. deadlines, rules, who is responsible, yes/no questions, "what is", "who must")
- PROCEDURAL: User wants steps, a process, or a checklist 
  (e.g. "how to", "create a checklist", "what should happen", "what are the steps", 
  "what needs to be done", "what should be done", "what happens when")
- SUMMARIZATION: User wants a summary of a document or section
  (e.g. "summarize", "what does X document say", "overview of")

Respond ONLY in this exact format:
STANDARDIZED: <standardized question>
TYPE: <FACTUAL|PROCEDURAL|SUMMARIZATION>
TERMS: <comma separated key terms>

User question: {query}"""


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