# 🧠 Brain Cancer Graph RAG — v2

**v2 of this repository.** It evolves the original Brain_project (**v1**, on the `main`
branch) from a knowledge-graph *builder* into a full **Graph RAG** system: ask natural-language
questions about brain-cancer literature and get **LLM answers grounded in the graph**, with
PMID citations and the retrieved subgraph shown.

v1 turned PubMed abstracts into a Neo4j graph. **v2 adds the retrieval + generation layer**
that makes that graph *answer questions*.

## What's new vs v1

| | v1 (Brain_project) | **v2 (this)** |
|---|---|---|
| Graph build (PubMed → NER → Neo4j) | ✅ | ✅ (kept) |
| Abstract text + **embeddings** stored in the graph | ❌ | ✅ `:Abstract{text, embedding}` |
| **Vector index** (semantic search) | ❌ (Neo4j 4.4) | ✅ Neo4j 5 native vector index |
| Entity → source-abstract links | ❌ | ✅ `(:Entity)-[:MENTIONED_IN]->(:Abstract)` |
| **Hybrid retrieval** | ❌ | ✅ vector **+** graph-expansion **+** Text2Cypher |
| **LLM answer generation** (grounded, cited) | ❌ | ✅ pluggable local LLM (Ollama) |
| UI | stats + ingest | **chat** + sources + **subgraph viz** |

## Architecture

```
          ┌──────────────┐   /ask        ┌───────────────────────────────┐
 User ──▶ │  Streamlit    │ ───────────▶ │  FastAPI  (Graph RAG)          │
          │  chat + graph │ ◀─────────── │  retrieve → generate           │
          └──────────────┘   answer      └───────┬───────────────┬───────┘
                                                  │               │
                                   vector + graph │               │ chat
                                                  ▼               ▼
                                          ┌──────────────┐  ┌──────────────┐
                                          │  Neo4j 5     │  │  Ollama      │
                                          │  KG + vector │  │  local LLM   │
                                          └──────────────┘  └──────────────┘
```

Four containers (`docker-compose.yml`): **neo4j** (graph + vector index), **ollama** (local
LLM, GPU), **api** (FastAPI: ingestion + RAG), **streamlit-app** (chat UI).

## The Graph RAG flow (on `/ask`)

1. **Vector search** — embed the question with a biomedical sentence model
   (`S-PubMedBert-MS-MARCO`) and query Neo4j's vector index for the top-k most similar
   `:Abstract` nodes.
2. **Graph expansion** — from those abstracts, pull the entities mentioned in them and their
   typed relations (`ASSOCIATED_WITH`, `TREATS`, `MODULATES`, …) → a subgraph + textual facts.
3. **Text2Cypher** — the LLM writes a **read-only** Cypher query from the schema for
   structured/aggregate questions ("which genes associate with glioblastoma?"); it's executed
   and the rows join the context. (A write-guard rejects any `CREATE/DELETE/SET/…`.)
4. **Generate** — the LLM composes the answer **only from the retrieved context**, citing each
   claim with `[PMID:…]`. The UI shows the answer, clickable PubMed sources, and the subgraph.

## Run it

```bash
cp .env.example .env            # add HF_TOKEN if the NER model is gated
docker compose up -d --build

# pull a local model into Ollama (once); ~2GB, fits an 8GB GPU
docker compose exec ollama ollama pull qwen2.5:3b-instruct

# open the UI
#   Streamlit : http://localhost:8501
#   API docs  : http://localhost:8000/docs
#   Neo4j     : http://localhost:7474  (neo4j / password123)
```

In the UI: **sidebar → "Ingest / update graph"** (e.g. 20 articles) to build the graph, then
ask questions in the chat.

**GPU note:** the `ollama` service requests the GPU (needs
[nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
on the host). No GPU? Comment out the `deploy.resources` block in `docker-compose.yml` —
Ollama will run the model on CPU (slower). Embeddings/NER run in the `api` container on CPU by
default (light enough).

## Configuration (env)

| Var | Default | Purpose |
|---|---|---|
| `LLM_MODEL` | `qwen2.5:3b-instruct` | local model name (any you've `ollama pull`ed) |
| `LLM_BASE_URL` / `LLM_API_KEY` | Ollama | **set these to use OpenAI/Groq instead** — no code change |
| `EMBED_MODEL` | `pritamdeka/S-PubMedBert-MS-MARCO` | biomedical sentence embedder |
| `VECTOR_TOP_K` | 5 | abstracts from vector search |
| `ENABLE_TEXT2CYPHER` | 1 | toggle the Text2Cypher branch |

**Pluggable LLM:** the code only speaks the OpenAI chat API (`rag/llm.py`), so switching from
local Ollama to OpenAI/Groq/vLLM is pure configuration (`LLM_BASE_URL` + `LLM_API_KEY` +
`LLM_MODEL`).

## What was validated

Against a **real Neo4j 5** container (with synthetic embeddings + a mocked LLM — the only
parts needing your GPU):
- ✅ vector index creation + **vector search ranks the right abstract first**
- ✅ ingestion writes (`:Abstract` + entities + `MENTIONED_IN` + typed relations)
- ✅ graph-expansion facts with PMIDs + subgraph
- ✅ Text2Cypher executes generated Cypher and returns rows
- ✅ full pipeline returns a grounded, `[PMID]`-cited answer with sources + subgraph
- ✅ write-guard blocks `DELETE/CREATE/…` from Text2Cypher
- ✅ all Python modules syntax-clean; docker-compose + Dockerfiles written

The **real LLM** (Ollama) isn't exercised here (this box's GPU driver wasn't available in the
build sandbox); it runs on your machine via `docker compose` as above.

## Interview questions (with answers)

**Q1. What is Graph RAG and why use it over plain (vector) RAG?**
Plain RAG retrieves text chunks by embedding similarity and feeds them to an LLM. **Graph RAG**
also uses a **knowledge graph**: it can follow *explicit relations* (gene→disease→drug), answer
*structured/multi-hop* questions, and give cleaner provenance. Here we do **both** — vector
search for fuzzy semantic recall **and** graph traversal/Text2Cypher for precise relational
facts — which covers more question types than either alone.

**Q2. How does the hybrid retrieval combine the two?**
Vector search finds the most *relevant abstracts*; graph expansion turns those into *entity
relations*; Text2Cypher answers *structured* asks. All three feed one context block to the
generator. Vector = recall, graph = precision/structure.

**Q3. Why store embeddings inside Neo4j instead of a separate vector DB?**
It keeps retrieval **unified** — one store for both the vectors and the relations, so after a
vector hit we traverse to neighbours in the *same* query engine (no cross-store joins). Neo4j
5's native vector index makes this first-class.

**Q4. How do you stop the LLM from hallucinating or running destructive Cypher?**
Two guards: (a) the answer prompt says *use only the provided context and cite PMIDs*, so
claims are grounded and checkable; (b) Text2Cypher is constrained to **read-only** and a regex
**write-guard** rejects any `CREATE/MERGE/DELETE/SET/DROP/LOAD` before execution.

**Q5. Why a biomedical embedding model instead of a general one?**
Questions and abstracts are dense biomedical language (gene names, mutations, drugs). A
PubMed-trained embedder (`S-PubMedBert`) puts *IDH1*, *glioma*, *temozolomide* in sensible
neighbourhoods, so semantic search retrieves the right papers far better than a generic model.

**Q6. Why a small local LLM, and how is it pluggable?**
Local = free, private, offline (patient-data-friendly). A ~3B instruct model fits an 8GB GPU
and is enough for Text2Cypher + grounded synthesis. `rag/llm.py` speaks the OpenAI API, so the
same code runs against Ollama **or** OpenAI/Groq by changing three env vars.

**Q7. What are the limits / next steps?**
Relations are heuristic (type-pair co-occurrence in an abstract), so some edges are noisy — a
relation-extraction model would sharpen them. The NER/relation quality caps answer quality.
Next: entity resolution (merge `TP53`/`p53`), a reranker over retrieved abstracts, and
evaluation (a Q&A set scored for answer faithfulness + citation correctness).

**Q8. How would you evaluate a Graph RAG system?**
Separate **retrieval** (did we fetch the right abstracts/subgraph? recall@k, Cypher
execution-accuracy) from **generation** (is the answer faithful to the context and are the
PMID citations correct?). Build a small gold Q&A set and score both; track hallucination rate.
