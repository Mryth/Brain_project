import os
import re
import logging
from transformers import pipeline
from neo4j import Driver
from .buffer import SQLiteBuffer

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION DU MODÈLE NER ---
HF_TOKEN = os.getenv("HF_TOKEN")
ner_pipeline = None # Initialisation à None

if not HF_TOKEN:
    logger.warning("Le token Hugging Face (HF_TOKEN) n'est pas défini. Le chargement du modèle est ignoré.")
else:
    try:
        logger.info("Chargement du modèle NER de Hugging Face...")
        ner_pipeline = pipeline(
            "ner",
            model="Kushtrim/ModernBERT-base-biomedical-ner",
            aggregation_strategy="simple",
            token=HF_TOKEN
        )
        logger.info("Modèle NER chargé avec succès.")
    except Exception as e:
        logger.error(f"Impossible de charger le modèle NER. L'API fonctionnera sans capacité NER. Erreur : {e}")

# --- DÉFINITION DES RELATIONS ---
RELATIONS_MAP = {
    ("SMALL_MOLECULE", "GENEPROD"): "MODULATES",
    ("SMALL_MOLECULE", "DISEASE"): "TREATS",
    ("GENEPROD", "DISEASE"): "ASSOCIATED_WITH",
    ("GENEPROD", "SUBCELLULAR"): "LOCALIZED_TO",
    ("GENEPROD", "CELL_TYPE"): "EXPRESSED_IN",
    ("CELL_LINE", "DISEASE"): "MODELS",
    ("CELL_TYPE", "DISEASE"): "AFFECTED_IN",
    ("TISSUE", "DISEASE"): "AFFECTED_BY"
}

# --- FONCTIONS UTILITAIRES ---
def _sanitize_label(label: str) -> str:
    return re.sub(r'[^A-Za-z0-9_]', '_', label)

def _generate_cypher_queries(abstract_text: str):
    if not ner_pipeline:
        logger.warning("Le pipeline NER n'est pas disponible, aucune requête Cypher ne sera générée.")
        return []

    try:
        entities = ner_pipeline(abstract_text)
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du pipeline NER : {e}")
        return []

    entities_by_type = {}
    for ent in entities:
        ent_type = _sanitize_label(ent["entity_group"])
        ent_word = ent["word"].strip()
        if ent_type not in entities_by_type:
            entities_by_type[ent_type] = set()
        entities_by_type[ent_type].add(ent_word)

    queries = []
    
    for ent_type, words in entities_by_type.items():
        for word in words:
            query = f"MERGE (n:{ent_type} {{name: $name}})"
            queries.append((query, {"name": word}))

    for (src_type, tgt_type), rel_label in RELATIONS_MAP.items():
        src_type_s = _sanitize_label(src_type)
        tgt_type_s = _sanitize_label(tgt_type)
        if src_type_s in entities_by_type and tgt_type_s in entities_by_type:
            query = (
                f"MATCH (a:{src_type_s}), (b:{tgt_type_s}) "
                f"WHERE a.name IN $src_names AND b.name IN $tgt_names "
                f"MERGE (a)-[:{rel_label}]->(b)"
            )
            params = {
                "src_names": list(entities_by_type[src_type_s]),
                "tgt_names": list(entities_by_type[tgt_type_s])
            }
            queries.append((query, params))
            
    return queries

def process_buffer_to_neo4j(buffer: SQLiteBuffer, driver: Driver):
    processed_count = 0
    total_queries = 0
    
    if not ner_pipeline:
        logger.error("Le pipeline NER n'a pas pu être chargé. Le traitement du buffer est annulé.")
        return 0, 0
    
    while True:
        batch = buffer.get_unprocessed_batch(batch_size=10)
        if not batch:
            break

        for article_id, abstract in batch:
            logger.info(f"Traitement de l'article {article_id}...")
            cypher_queries = _generate_cypher_queries(abstract)
            
            if cypher_queries:
                with driver.session() as session:
                    for query, params in cypher_queries:
                        try:
                            session.run(query, params)
                            total_queries += 1
                        except Exception as e:
                            logger.error(f"Erreur Cypher pour l'article {article_id}: {e} | Query: {query}")
            
            buffer.mark_as_processed(article_id)
            processed_count += 1
            
    return processed_count, total_queries


