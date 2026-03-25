from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ChunkResult:
    content: str
    filename: str
    section_title: str
    score: float
    chunk_index: int

@dataclass
class StepLog:
    agent: str
    details: dict

@dataclass
class AgentContext:
    original_query: str
    standardized_query: Optional[str] = None
    query_type: Optional[str] = None
    search_terms: Optional[list] = None
    retrieved_chunks: Optional[list] = None
    is_answerable: Optional[bool] = None
    sources: Optional[list] = None
    answer: Optional[str] = None
    steps: list = field(default_factory=list)