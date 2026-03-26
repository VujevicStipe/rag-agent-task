# Company Knowledge Assistant

RAG multi-agent sustav koji odgovara na pitanja o internim dokumentima tvrtke.

---

## Problemi i kako su riješeni

Skup dokumenata uključuje nekoliko problematičnih fajlova koji testiraju kako sustav reagira na rubne slučajeve.

### Dokumenti s besmislenim sadržajem

`krzth_monkey_document.md` sadrži samo izmišljene riječi, a `symbolic_reference.md` samo simbole. Kada korisnik pita "Summarize the Krzth Monolithic Reference document", similarity search nije mogao pronaći taj dokument jer embedding izmišljenih riječi nema semantičko značenje — umjesto toga, vraćao je chunkove iz `zulmar_policy.md` koji ima sličan nonsense vokabular.

Rješenje je jednostavno: pri chunkingu dodajemo `section_title` kao prefix u sadržaj svakog chunka. Naslov "Krzth Monolithic Reference" je jedini smisleni tekst u tom dokumentu i dovoljan je da similarity search pronađe pravi dokument. ResponseGenerator zatim prepoznaje da sadržaj nije interpretabilan i vraća user-friendly poruku.

### Zulmar policy

`zulmar_policy.md` ima izmišljene pojmove ali validnu strukturu dokumenta. Sustav odgovara prema dokumentu i navodi source. Procjena je li sadržaj realan nije odgovornost RAG sustava — njegova jedina odgovornost je biti vjeran posrednik između korisnika i dokumenata.

### WIP dokument

`expense_policy_wip.md` je nepotpuna verzija s napomenom "do not use" na kraju. Pri ingestionu, document registry skenira svaki dokument za warning signale i sprema rezultat u `registry.json`. Kada retriever pronađe chunk iz flagganog dokumenta, warning se prikazuje uz source u odgovoru. Identični chunkovi između WIP i finalne verzije su deduplicirani automatski od strane ChromaDB-a po content hashu.

### Duplikati

`hr_onboarding.md` i `onboarding_process.md` su identični, kao i `kickoff.md` i `project_kickoff.md`. Svi fajlovi ulaze u ingestion — sustav ne filtrira ručno.

ChromaDB deduplificira identične chunkove pri ingestionu po content hashu. Ovo je važno iz perspektive kvalitete retrievala — bez deduplication, isti sadržaj koji se pojavljuje u više fajlova bi dobivao umjetno veći weight u similarity searchu samo zbog ponavljanja, što bi iskrivilo rezultate prema tim temama bez stvarnog razloga.

---

## Arhitektura

3 agenta u jednom procesu, sekvencijalni pipeline koordiniran Orchestratorom. Odlučio sam se za jedan proces umjesto microservices arhitekture — za ovaj scope je dovoljno, a granice između agenata su čiste i mogu se razbiti na zasebne servise ako zatreba.

```
User Query
    ↓
[1] QueryAnalyzer   — standardizira pitanje, klasificira tip, ekstraktira search terme
    ↓
[2] Retriever       — vector search u ChromaDB, threshold check, source filtering
    ↓
[3] ResponseGenerator — generira odgovor prema tipu pitanja, navodi sources
    ↓
Odgovor + Sources + Step log
```

### QueryAnalyzer
- Standardizira pitanje — typo, neformalni jezik ili skraćenice se normaliziraju prije embedanja
- Klasificira tip: `FACTUAL` / `PROCEDURAL` / `SUMMARIZATION`
- Ekstraktira ključne termine za search
- Embeda standardizirano pitanje, ne originalno

### Retriever
- Embeda query istim modelom kao ingestion (`gemini-embedding-001`) — konzistentni vektorski prostor
- Vector search u ChromaDB, top K = 7
- Odbacuje chunkove ispod similarity thresholda 0.70
- Prikazuje samo sources unutar 10% od top scorea
- Čita registry i dodaje warning uz source ako je dokument flaggan

### ResponseGenerator
- `FACTUAL` → direktan, koncizan odgovor
- `PROCEDURAL` → checklist s checkboxima
- `SUMMARIZATION` → strukturirani summary
- Ako `is_answerable = False` → "Information not available"
- Uvijek navodi sources s postotkom sličnosti

---

## UI Dashboard

Web sučelje za interakciju sa sustavom. Prikazuje agent pipeline uživo, sources s postocima sličnosti, warning za flaggane dokumente i history zadnjih pitanja. Komunicira s FastAPI serverom na portu 8000.

![Dashboard](./assets/task-agent-mockup.png)

## Stack

| Komponenta | Tehnologija |
|---|---|
| Embeddings | `gemini-embedding-001` |
| LLM | `gemini-2.5-flash` |
| Vector store | ChromaDB (lokalno) |
| Backend | FastAPI |
| UI | Vanilla HTML/CSS/JS |

Isti embedding model koristi se i pri ingestionu i pri queryju. Različiti modeli stvaraju različite vektorske prostore pa similarity search ne bi radio ispravno.

---

## Chunking strategija

Structure-based chunking po MD headinzima (`#`, `##`, `###`) s overlap od 3 linije između sekcija. Svaki chunk uključuje `section_title` kao prefix u sadržaj:

```
"Submission Deadline\n\nExpense claims must be submitted within 15 calendar days..."
```

Ovo je kritično za dokumente s neinterpretabilnim sadržajem gdje je naslov jedina smislena informacija.

---

## Pokretanje

### Preduvjeti
```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Kreiraj `.env` fajl:
```
GEMINI_API_KEY=your_key_here
```

### Ingestion (jednom)
```bash
python ingest.py
```

### CLI
```bash
python main.py
```

### API + Dashboard
```bash
# Terminal 1
uvicorn api.server:app --reload --port 8000

# Terminal 2 — otvori dashboard.html u browseru
ui/dashboard.html
```

---

## Struktura projekta

```
rag_agent/
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
├── ingestion/
│   ├── loader.py
│   ├── chunker.py
│   ├── embedder.py
│   └── document_registry.py
├── api/
│   └── server.py
├── ui/
│   └── dashboard.html
├── evaluation/
│   └── run_eval.py
├── documents/
├── ingest.py
└── main.py
```

---

## Konfiguracija

`config/retrieval.yaml` — ključne vrijednosti bez diranja koda:

```yaml
similarity_threshold: 0.7
top_k: 7
source_margin: 0.1
support_email: support@company.com
```

Prompts su u `config/prompts/` — mogu se mijenjati bez restarta koda.