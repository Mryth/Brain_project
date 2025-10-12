import os
from fastapi import FastAPI, HTTPException
from neo4j import GraphDatabase, exceptions
import logging

# Import des modules de script
from scripts.buffer import SQLiteBuffer
from scripts.extract import fetch_abstracts_pubmed
from scripts.process import process_buffer_to_neo4j

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Brain Cancer Knowledge Graph API",
    description="API pour extraire, traiter et charger des données biomédicales dans un graphe Neo4j.",
    version="1.0.0"
)

# Configuration Neo4j depuis les variables d'environnement
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

# Initialisation du buffer SQLite
buffer = SQLiteBuffer(db_path="buffer.db")

def get_neo4j_driver():
    """Crée et retourne un driver Neo4j."""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        return driver
    except exceptions.ServiceUnavailable:
        raise HTTPException(status_code=503, detail="Neo4j n'est pas disponible.")
    except exceptions.AuthError:
        raise HTTPException(status_code=401, detail="Erreur d'authentification Neo4j.")

@app.post("/update-graph/{n_articles}", summary="Met à jour le graphe")
async def update_graph(n_articles: int):
    """
    Orchestre le processus complet :
    1. Extrait N articles de PubMed et les stocke dans un buffer.
    2. Traite les articles du buffer (NER) et charge les résultats dans Neo4j.
    """
    if not (1 <= n_articles <= 500):
        raise HTTPException(status_code=400, detail="Le nombre d'articles doit être entre 1 et 500.")

    try:
        logger.info(f"Étape 1 : Extraction de {n_articles} articles de PubMed...")
        extracted_count = fetch_abstracts_pubmed(n_articles, buffer)
        logger.info(f"{extracted_count} abstracts extraits et stockés.")

        logger.info("Étape 2 : Traitement du buffer et chargement dans Neo4j...")
        driver = get_neo4j_driver()
        processed_count, queries_executed = process_buffer_to_neo4j(buffer, driver)
        driver.close()
        logger.info(f"{processed_count} abstracts traités. {queries_executed} requêtes exécutées.")

        return {
            "message": "Mise à jour du graphe terminée.",
            "abstracts_extracted": extracted_count,
            "abstracts_processed": processed_count,
            "cypher_queries_executed": queries_executed
        }
    except Exception as e:
        logger.error(f"Une erreur est survenue lors de la mise à jour : {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats", summary="Statistiques du graphe")
async def get_stats():
    """Retourne le nombre total de nœuds et de relations dans le graphe."""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
        return {"nodes": nodes, "relationships": rels}
    finally:
        driver.close()

@app.delete("/clear-buffer", summary="Vide le buffer d'abstracts")
async def clear_buffer_endpoint():
    """Supprime tous les abstracts de la base de données SQLite buffer."""
    count = buffer.clear_all()
    return {"status": "buffer_cleared", "abstracts_deleted": count}

