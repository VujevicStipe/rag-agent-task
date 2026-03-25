# RAG Multi-Agent System — Architecture Decisions

## Stack

| Komponenta | Tehnologija | Razlog |
|---|---|---|
| Embeddings | `gemini-embedding-001` | Besplatan, top MTEB score |
| LLM | Gemini 2.5 Flash | Besplatan, dovoljan za generation |
| Vector store | ChromaDB | Lokalno, bez setup-a |
| Backend | FastAPI | REST API + jednostavno |
| UI | Vanilla HTML/CSS/JS | Nema framework overhead-a |

> **Kritično:** Isti embedding model koristi se i pri ingestionu i pri query-ju. Različiti modeli stvaraju različite vektorske prostore — similarity search ne bi radio ispravno.

---

## Arhitektura — 3 agenta + orchestrator, jedan proces

Agenti su **zasebne klase u zasebnim fajlovima** ali žive u jednom Python procesu.

Nije microservices jer je overkill za ovaj scope — ali arhitektura je dizajnirana s čistim granicama koje se **mogu razbiti na microservices** kada/ako zatreba.

Nema event busa — sekvencijalni pipeline s 3 agenta ne treba pub/sub. Orchestrator direktno poziva agente, što je čitljivije i dovoljno za ovaj scope.

```
Orchestrator
    → QueryAnalyzer
    → Retriever
    → ResponseGenerator
```

---

## AgentContext — shared state

Jedan objekt koji putuje kroz cijeli pipeline. Svaki agent ga prima, dopunjuje svoje polje, prosljeđuje dalje.

```python
@dataclass
class AgentContext:
    original_query: str
    standardized_query: str | None     # QueryAnalyzer
    query_type: str | None             # FACTUAL / PROCEDURAL / SUMMARIZATION
    search_terms: list | None          # QueryAnalyzer
    retrieved_chunks: list | None      # Retriever
    is_answerable: bool | None         # Retriever (threshold check)
    sources: list | None               # Retriever
    answer: str | None                 # ResponseGenerator
    steps: list                        # audit trail svakog agenta
```

---

## Agenti

### QueryAnalyzer
- **Standardizira pitanje** — štiti cijeli pipeline od lošeg inputa (typo, neformalni jezik, skraćenice)
- Klasificira tip pitanja: `FACTUAL` / `PROCEDURAL` / `SUMMARIZATION`
- Ekstraktira ključne termine za search
- Embeda **standardizirano** pitanje, ne originalno

### Retriever
- Vector search u ChromaDB
- Ako similarity score < threshold → `is_answerable = False`, nema LLM poziva
- Provjerava `registry.json` za svaki pronađeni source
- Post-retrieval deduplication — odbacuje flagged source ako postoji čista alternativa
- Vraća top K chunkova s metadata

### ResponseGenerator
- Ako `is_answerable = False` → vraća "Information not available in documents"
- `FACTUAL` → direktan odgovor
- `PROCEDURAL` → checklist / koraci
- `SUMMARIZATION` → strukturirani summary
- Odgovara **isključivo** na temelju retrieved chunkova — ne koristi vlastito znanje
- Uvijek navodi sources
- Ako source ima warning → napominje u odgovoru

---

## Klasifikacija tipa pitanja — zašto je bitna

Isti dokument, različit format ovisno o tipu:

```
FACTUAL:     "What is the deadline?"     → jedna rečenica
PROCEDURAL:  "Create onboarding checklist" → □ korak 1 □ korak 2...
SUMMARIZATION: "Summarize Krzth document" → strukturirani summary
```

---

## Sustav nije sudac istinitosti

Ako dokument postoji u bazi, sustav odgovara prema njemu i navodi source — bez obzira je li sadržaj smislen ili ne. Procjena istinitosti sadržaja nije odgovornost RAG sustava.

Primjer — `zulmar_policy.md`:
- Dokument postoji, ima strukturu, ima procedure
- Sustav odgovara prema njemu i navodi source
- Odgovor će biti besmislen — ali korektan

---

## Ingestion pipeline

```
ingest.py
    ↓
loader.py              → čita sve MD fajlove
    ↓
document_registry.py   → skenira svaki dokument za warning signale
                       → sprema data/registry.json
    ↓
chunker.py             → dijeli po MD headinzima (#, ##, ###) + 10-20% overlap
    ↓
embedder.py            → embeda svaki chunk (gemini-embedding-001)
                       → sprema u ChromaDB s metadata
```

### Chunk metadata

```python
{
    "filename": "expense_policy.md",
    "section_title": "Submission Deadline",
    "chunk_index": 3,
    "content": "..."
}
```

### Document registry

Pri ingestionu svaki dokument se skenira za warning signale u cijelom sadržaju:

```python
WARNING_SIGNALS = [
    "do not use",
    "not finished",
    "draft",
    "deprecated",
    "do not distribute",
    "work in progress",
    "superseded"
]
```

Output — `data/registry.json`:

```json
{
    "expense_policy.md":     { "warning": null },
    "expense_policy_wip.md": { "warning": "not finished" }
}
```

---

## Post-retrieval deduplication + warning handling

Retriever nakon vector searcha provjerava registry i deduplificira:

| Scenarij | Akcija |
|---|---|
| Dva ista chunka, jedan flagged | Odbaci flagged, zadrži čisti |
| Dva ista chunka, oba flagged | Zadrži jedan, dodaj warning u context |
| Jedan chunk, flagged | Zadrži, ResponseGenerator dobiva warning info |
| Jedan chunk, clean | Normalan flow |

---

## Dokumenti

### Svi ulaze u ingestion (15 fajlova)

Sustav ne filtrira dokumente ručno — odluke prepuštamo sustavu.

### Trap dokumenti (namjerno besmisleni)

| Dokument | Tip | Ponašanje |
|---|---|---|
| `krzth_monkey_document.md` | Čisti nonsense tekst | Pronađen ali ne može se summarizirati |
| `symbolic_reference.md` | Samo simboli | Pronađen, nema interpretabilnog sadržaja |
| `zulmar_policy.md` | Izmišljeni pojmovi | Odgovara prema dokumentu, navodi source |
| `quantum_synergy_policy.md` | Buzzword nonsense | Odgovara prema dokumentu, navodi source |

### Duplikati

| Duplikat | Zadržati |
|---|---|
| `hr_onboarding.md` + `onboarding_process.md` | Oba ulaze, post-retrieval dedup rješava |
| `kickoff.md` + `project_kickoff.md` | Oba ulaze, post-retrieval dedup rješava |
| `expense_policy.md` + `expense_policy_wip.md` | Oba ulaze, WIP flagged u registry |

---

## Config izvan koda

```
config/
├── retrieval.yaml        ← chunk_size, top_k, similarity_threshold
└── prompts/
    ├── query_analyzer.txt
    ├── response_factual.txt
    ├── response_procedural.txt
    └── response_summarization.txt
```

Prompts i parametri su u fajlovima — ne u kodu. Mijenjaju se bez deployмента.

---

## Struktura projekta

```
project/
├── agents/
│   ├── base.py
│   ├── query_analyzer.py
│   ├── retriever.py
│   └── response_generator.py
├── core/
│   ├── context.py
│   └── orchestrator.py
├── config/
│   ├── retrieval.yaml
│   └── prompts/
│       ├── query_analyzer.txt
│       ├── response_factual.txt
│       ├── response_procedural.txt
│       └── response_summarization.txt
├── ingestion/
│   ├── loader.py
│   ├── chunker.py
│   ├── embedder.py
│   └── document_registry.py
├── data/
│   └── registry.json
├── api/
│   └── server.py
├── ui/
│   └── dashboard.html
├── evaluation/
│   └── run_eval.py
├── docs/
│   └── ARCHITECTURE.md
├── ingest.py
└── main.py
```

---

## Redoslijed implementacije

```
1. core/context.py
2. agents/base.py
3. agents/query_analyzer.py
4. agents/retriever.py
5. agents/response_generator.py
6. core/orchestrator.py
7. ingestion/loader.py
8. ingestion/document_registry.py
9. ingestion/chunker.py
10. ingestion/embedder.py
11. ingest.py        ← CLI za ingestion
12. main.py          ← CLI za query
13. api/server.py
14. ui/dashboard.html
15. evaluation/run_eval.py
```

---

## Što reći tech leadu

| Pitanje | Odgovor |
|---|---|
| Zašto ne microservices? | Svjesna odluka — overkill za ovaj scope, ali granice su čiste i mogu se razbiti |
| Zašto ne event bus? | Sekvencijalni pipeline ne treba pub/sub — direktni pozivi su čitljiviji i dovoljni |
| Zašto isti embedding model? | Različiti modeli = različiti vektorski prostori, similarity search ne radi |
| Zašto standardizacija pitanja? | Štiti cijeli pipeline — embedding lošeg pitanja = loš retrieval |
| Zašto nema Validator agenta? | Threshold check je jedan if uvjet — nije zaradio mjesto kao zasebni agent |
| Zašto registry.json? | Sustav sam detektira problematične dokumente, bez hardcodinga naziva fajlova |
| Zašto sustav odgovara na zulmar? | Sustav nije sudac istinitosti — vjeran je dokumentima, ne procjenjuje sadržaj |
| Kako bi skalirao? | ChromaDB → Pinecone, agenti → microservices, jedan embedding model ostaje |


## Final output format
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1] QueryAnalyzer
    → standardized: "What is the expense claim deadline?"
    → type: FACTUAL
    → terms: ["expense", "deadline", "submission"]

[2] Retriever
    → searched 847 chunks across 15 documents
    → top match: expense_policy.md § Submission Deadline (0.91)
    → is_answerable: True

[3] ResponseGenerator
    → type: FACTUAL
    → sources: expense_policy.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SOURCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 expense_policy.md § Submission Deadline

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ANSWER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Expense claims must be submitted within 15 calendar days...


context.steps.append({
    "agent": "QueryAnalyzer",
    "original_query": context.original_query,
    "standardized_query": context.standardized_query,
    "query_type": context.query_type,
    "search_terms": context.search_terms
})

context.steps.append({
    "agent": "Retriever",
    "chunks_searched": total_chunks,
    "top_match": top_chunk_filename,
    "top_score": top_score,
    "is_answerable": context.is_answerable
})

context.steps.append({
    "agent": "ResponseGenerator",
    "response_type": context.query_type,
    "sources": context.sources
})