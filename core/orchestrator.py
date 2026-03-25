import json
from agents.query_analyzer import QueryAnalyzer
from agents.retriever import Retriever
from agents.response_generator import ResponseGenerator
from core.context import AgentContext

REGISTRY_PATH = "data/registry.json"


class Orchestrator:

    def __init__(self):
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)

        self.query_analyzer = QueryAnalyzer()
        self.retriever = Retriever()
        self.response_generator = ResponseGenerator(registry=registry)

    def run(self, query: str) -> AgentContext:
        context = AgentContext(original_query=query)

        context = self.query_analyzer.run(context)
        context = self.retriever.run(context)
        context = self.response_generator.run(context)

        return context