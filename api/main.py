"""Brain Cancer Graph RAG API (v2).
Ingestion endpoints (build the graph + embeddings) + RAG endpoints (ask questions)."""
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from neo4j import GraphDatabase, exceptions

import config
from scripts.buffer import SQLiteBuffer
from scripts.extract import fetch_abstracts_pubmed
from scripts.process import process_buffer_to_neo4j, ensure_vector_index
from rag import pipeline, llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Brain Cancer Graph RAG API", version="2.0.0",
              description="PubMed -> knowledge graph + embeddings -> hybrid Graph RAG Q&A.")
buffer = SQLiteBuffer(db_path="buffer.db")


def get_driver():
    try:
        d = GraphDatabase.driver(config.NEO4J_URI,
                                 auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))
        d.verify_connectivity()
        return d
    except exceptions.ServiceUnavailable:
        raise HTTPException(503, "Neo4j unavailable.")
    except exceptions.AuthError:
        raise HTTPException(401, "Neo4j auth error.")


class Question(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok", "llm_backend": config.LLM_BASE_URL,
            "llm_model": config.LLM_MODEL, "llm_reachable": llm.available()}


@app.post("/update-graph/{n_articles}", summary="Ingest N PubMed articles -> graph + embeddings")
def update_graph(n_articles: int):
    if not (1 <= n_articles <= 500):
        raise HTTPException(400, "n_articles must be between 1 and 500.")
    extracted = fetch_abstracts_pubmed(n_articles, buffer)
    driver = get_driver()
    try:
        processed, queries = process_buffer_to_neo4j(buffer, driver)
    finally:
        driver.close()
    return {"abstracts_extracted": extracted, "abstracts_processed": processed,
            "cypher_queries_executed": queries}


@app.get("/stats", summary="Graph statistics")
def stats():
    driver = get_driver()
    try:
        with driver.session() as s:
            nodes = s.run("MATCH (n) RETURN count(n) AS c").single()["c"]
            rels = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
            abstracts = s.run("MATCH (a:Abstract) RETURN count(a) AS c").single()["c"]
        return {"nodes": nodes, "relationships": rels, "abstracts": abstracts}
    finally:
        driver.close()


@app.post("/ask", summary="Ask a question (hybrid Graph RAG)")
def ask(q: Question):
    if not q.question.strip():
        raise HTTPException(400, "Empty question.")
    driver = get_driver()
    try:
        ensure_vector_index(driver)          # idempotent; safe on every call
        return pipeline.answer(driver, q.question.strip())
    finally:
        driver.close()
