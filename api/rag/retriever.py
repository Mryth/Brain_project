"""Hybrid retrieval over the knowledge graph:
  1. VECTOR  — semantic search over :Abstract embeddings (Neo4j native vector index)
  2. GRAPH   — expand the entities mentioned in those abstracts + their typed relations
  3. TEXT2CYPHER — the LLM writes a read-only Cypher query for structured/aggregate questions
Returns everything the generator and the UI need (snippets, facts, subgraph, cypher)."""
import re
import logging
import config
from rag.embeddings import embed
from rag import llm
from rag.schema import TEXT2CYPHER_SYSTEM

logger = logging.getLogger(__name__)

_WRITE = re.compile(r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP|LOAD|CALL\s+apoc\.\w+\.(create|delete))\b", re.I)


def _entity_label(labels):
    return next((l for l in labels if l != "Entity"), labels[0] if labels else "Entity")


# ---------- 1. vector search ----------
def vector_search(driver, question, k=None):
    k = k or config.VECTOR_TOP_K
    qv = embed(question)
    cy = """CALL db.index.vector.queryNodes($idx, $k, $qv) YIELD node, score
            RETURN node.pmid AS pmid, node.title AS title, node.text AS text, score
            ORDER BY score DESC"""
    with driver.session() as s:
        rows = s.run(cy, idx=config.VECTOR_INDEX_NAME, k=k, qv=qv).data()
    return rows


# ---------- 2. graph expansion ----------
def graph_context(driver, pmids):
    """Entities in the retrieved abstracts + their outgoing typed relations."""
    if not pmids:
        return {"facts": [], "nodes": [], "edges": []}
    cy = """
    MATCH (e:Entity)-[:MENTIONED_IN]->(a:Abstract) WHERE a.pmid IN $pmids
    OPTIONAL MATCH (e)-[r]->(e2:Entity)
    WHERE NOT type(r) = 'MENTIONED_IN'
    RETURN e.name AS src, labels(e) AS src_l,
           type(r) AS rel, e2.name AS dst, labels(e2) AS dst_l,
           r.source_pmid AS pmid
    LIMIT 200"""
    with driver.session() as s:
        rows = s.run(cy, pmids=pmids).data()
    facts, nodes, edges = [], {}, []
    for r in rows:
        sl = _entity_label(r["src_l"] or [])
        nodes[r["src"]] = sl
        if r["rel"] and r["dst"]:
            dl = _entity_label(r["dst_l"] or [])
            nodes[r["dst"]] = dl
            cite = f" [PMID:{r['pmid']}]" if r.get("pmid") else ""
            facts.append(f"({sl}) {r['src']} -[{r['rel']}]-> ({dl}) {r['dst']}{cite}")
            edges.append({"source": r["src"], "target": r["dst"], "label": r["rel"]})
    node_list = [{"id": n, "label": lbl} for n, lbl in nodes.items()]
    return {"facts": sorted(set(facts)), "nodes": node_list, "edges": edges}


# ---------- 3. text2cypher ----------
def text2cypher(driver, question):
    if not config.ENABLE_TEXT2CYPHER:
        return {"cypher": None, "rows": []}
    try:
        raw = llm.complete(TEXT2CYPHER_SYSTEM, question, temperature=0.0, max_tokens=300)
    except Exception as e:
        logger.warning(f"text2cypher LLM error: {e}")
        return {"cypher": None, "rows": []}
    cy = re.sub(r"^```(?:cypher)?|```$", "", raw.strip(), flags=re.I | re.M).strip()
    if not cy or _WRITE.search(cy):              # reject anything that writes
        logger.warning("text2cypher produced empty or write query; skipping.")
        return {"cypher": cy or None, "rows": []}
    try:
        with driver.session() as s:
            rows = s.run(cy).data()[:25]
        return {"cypher": cy, "rows": rows}
    except Exception as e:
        logger.warning(f"text2cypher execution failed: {e}")
        return {"cypher": cy, "rows": [], "error": str(e)}


# ---------- orchestrate ----------
def hybrid_retrieve(driver, question):
    abstracts = vector_search(driver, question)
    pmids = [a["pmid"] for a in abstracts]
    gc = graph_context(driver, pmids)
    t2c = text2cypher(driver, question)
    return {
        "abstracts": abstracts,
        "facts": gc["facts"],
        "subgraph": {"nodes": gc["nodes"], "edges": gc["edges"]},
        "cypher": t2c.get("cypher"),
        "cypher_rows": t2c.get("rows", []),
    }
