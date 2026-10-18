"""v2 ingestion: NER -> entities + typed relations (as v1), PLUS
- an :Abstract node per paper holding {pmid, title, text, embedding}
- (:Entity)-[:MENTIONED_IN]->(:Abstract) links
- a Neo4j native VECTOR INDEX on :Abstract(embedding)
so the graph supports both structured traversal and semantic (vector) retrieval."""
import re
import logging
from transformers import pipeline
from neo4j import Driver

import config
from rag.embeddings import embed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- NER model (lazy) ---
_ner = None
def _get_ner():
    global _ner
    if _ner is None:
        logger.info(f"Loading NER model {config.NER_MODEL}...")
        _ner = pipeline("ner", model=config.NER_MODEL,
                        aggregation_strategy="simple", token=config.HF_TOKEN)
    return _ner

# entity-type pair -> relation label (unchanged heuristic from v1)
RELATIONS_MAP = {
    ("SMALL_MOLECULE", "GENEPROD"): "MODULATES",
    ("SMALL_MOLECULE", "DISEASE"): "TREATS",
    ("GENEPROD", "DISEASE"): "ASSOCIATED_WITH",
    ("GENEPROD", "SUBCELLULAR"): "LOCALIZED_TO",
    ("GENEPROD", "CELL_TYPE"): "EXPRESSED_IN",
    ("CELL_LINE", "DISEASE"): "MODELS",
    ("CELL_TYPE", "DISEASE"): "AFFECTED_IN",
    ("TISSUE", "DISEASE"): "AFFECTED_BY",
}

def _san(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", label)


def ensure_vector_index(driver: Driver):
    """Create the abstract vector index once (Neo4j 5+)."""
    with driver.session() as s:
        s.run(
            f"""CREATE VECTOR INDEX {config.VECTOR_INDEX_NAME} IF NOT EXISTS
                FOR (a:Abstract) ON (a.embedding)
                OPTIONS {{ indexConfig: {{
                    `vector.dimensions`: {config.EMBED_DIM},
                    `vector.similarity_function`: 'cosine' }} }}"""
        )
    logger.info("Vector index ensured.")


def _entities_by_type(text: str):
    ner = _get_ner()
    try:
        ents = ner(text)
    except Exception as e:
        logger.error(f"NER error: {e}")
        return {}
    out = {}
    for e in ents:
        t = _san(e["entity_group"]); w = e["word"].strip()
        if len(w) < 2:
            continue
        out.setdefault(t, set()).add(w)
    return out


def _write_abstract(tx, pmid, title, text, embedding, ebt):
    # 1. the Abstract node (with embedding for vector search)
    tx.run(
        """MERGE (a:Abstract {pmid:$pmid})
           SET a.title=$title, a.text=$text, a.embedding=$emb""",
        pmid=pmid, title=title, text=text, emb=embedding,
    )
    # 2. entity nodes + MENTIONED_IN links
    for etype, words in ebt.items():
        for w in words:
            tx.run(
                f"""MERGE (n:{etype} {{name:$name}})
                    SET n:Entity
                    WITH n
                    MATCH (a:Abstract {{pmid:$pmid}})
                    MERGE (n)-[:MENTIONED_IN]->(a)""",
                name=w, pmid=pmid,
            )
    # 3. typed relations between co-mentioned entities (v1 heuristic)
    n_rel = 0
    for (s_t, t_t), rel in RELATIONS_MAP.items():
        s_t, t_t = _san(s_t), _san(t_t)
        if s_t in ebt and t_t in ebt:
            for sw in ebt[s_t]:
                for tw in ebt[t_t]:
                    tx.run(
                        f"""MATCH (s:{s_t} {{name:$s}}), (t:{t_t} {{name:$t}})
                            MERGE (s)-[r:{rel}]->(t)
                            SET r.source_pmid = $pmid""",
                        s=sw, t=tw, pmid=pmid,
                    )
                    n_rel += 1
    return n_rel


def process_buffer_to_neo4j(buffer, driver: Driver):
    """Process all unprocessed abstracts: NER + embedding + graph write."""
    ensure_vector_index(driver)
    rows = buffer.get_unprocessed()
    processed, queries = 0, 0
    for pmid, title, text in rows:
        ebt = _entities_by_type(text)
        emb = embed(text)                      # one vector per abstract
        with driver.session() as s:
            queries += s.execute_write(_write_abstract, pmid, title, text, emb, ebt)
        buffer.mark_processed(pmid)
        processed += 1
        logger.info(f"Processed PMID {pmid}: {sum(len(v) for v in ebt.values())} entities")
    return processed, queries
