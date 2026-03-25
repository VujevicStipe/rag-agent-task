import sys
from pathlib import Path
root = Path(__file__).parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.orchestrator import Orchestrator

app = FastAPI(title="Company Knowledge Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()


class QueryRequest(BaseModel):
    question: str


@app.post("/query")
def query(request: QueryRequest):
    context = orchestrator.run(request.question)
    return {
        "question": request.question,
        "answer": context.answer,
        "sources": context.sources,
        "is_answerable": context.is_answerable,
        "steps": [
            {"agent": s.agent, "details": s.details}
            for s in context.steps
        ]
    }


@app.get("/health")
def health():
    return {"status": "ok"}