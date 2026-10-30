"""Graph RAG pipeline: retrieve (hybrid) -> build context -> generate grounded answer."""
import logging
from rag import llm, retriever
from rag.schema import ANSWER_SYSTEM

logger = logging.getLogger(__name__)
MAX_SNIPPET = 600  # chars of each abstract fed to the LLM


def _build_context(r):
    parts = []
    if r["facts"]:
        parts.append("## Graph facts (entity relations)\n" + "\n".join(r["facts"][:40]))
    if r["cypher_rows"]:
        parts.append("## Structured query results\nCypher: " + (r["cypher"] or "") +
                     "\n" + "\n".join(str(row) for row in r["cypher_rows"][:25]))
    if r["abstracts"]:
        snips = [f"[PMID:{a['pmid']}] {a.get('title','')}\n{(a.get('text') or '')[:MAX_SNIPPET]}"
                 for a in r["abstracts"]]
        parts.append("## Abstract snippets\n" + "\n\n".join(snips))
    return "\n\n".join(parts) if parts else "(no context retrieved)"


def answer(driver, question):
    r = retriever.hybrid_retrieve(driver, question)
    context = _build_context(r)
    user = f"Question: {question}\n\nContext:\n{context}\n\nAnswer with PMID citations."
    try:
        text = llm.complete(ANSWER_SYSTEM, user, max_tokens=800)
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        text = ("[LLM unavailable] Retrieved context is shown below; start the LLM backend "
                "(Ollama) to get a synthesized answer.\n\n" + context[:1500])
    sources = [{"pmid": a["pmid"], "title": a.get("title", ""),
                "score": round(a.get("score", 0), 3)} for a in r["abstracts"]]
    return {
        "answer": text,
        "sources": sources,
        "subgraph": r["subgraph"],
        "cypher": r["cypher"],
        "cypher_rows": r["cypher_rows"],
        "n_facts": len(r["facts"]),
    }
