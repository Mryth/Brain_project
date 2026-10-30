"""Graph schema description + prompt templates used by Text2Cypher and the answerer."""

# High-level schema shown to the LLM so it can write valid Cypher.
GRAPH_SCHEMA = """
Node labels:
  (:Abstract {pmid, title, text})          # a PubMed article; also carries an embedding
  (:Entity)                                # super-label on every extracted entity
  Entity sub-labels (NER types): GENEPROD, DISEASE, SMALL_MOLECULE, CELL_TYPE,
     CELL_LINE, TISSUE, SUBCELLULAR, ORGANISM, ... each with {name}

Relationships:
  (:Entity)-[:MENTIONED_IN]->(:Abstract)
  (:SMALL_MOLECULE)-[:MODULATES]->(:GENEPROD)
  (:SMALL_MOLECULE)-[:TREATS]->(:DISEASE)
  (:GENEPROD)-[:ASSOCIATED_WITH]->(:DISEASE)
  (:GENEPROD)-[:LOCALIZED_TO]->(:SUBCELLULAR)
  (:GENEPROD)-[:EXPRESSED_IN]->(:CELL_TYPE)
  (:CELL_LINE)-[:MODELS]->(:DISEASE)
  (:CELL_TYPE)-[:AFFECTED_IN]->(:DISEASE)
  (:TISSUE)-[:AFFECTED_BY]->(:DISEASE)
  (typed relations carry r.source_pmid)
"""

TEXT2CYPHER_SYSTEM = f"""You translate a biomedical question into ONE Neo4j Cypher query.
Rules:
- READ-ONLY. Never use CREATE/MERGE/DELETE/SET/REMOVE/DROP/LOAD.
- Use ONLY the schema below. Entity names are case-sensitive strings; match loosely with
  toLower(n.name) CONTAINS toLower($term) when matching a term from the question.
- Always RETURN a small, named result (LIMIT 25). Prefer returning entity names and the
  r.source_pmid when relevant.
- Output ONLY the Cypher query, no prose, no markdown fences.

Schema:
{GRAPH_SCHEMA}"""

ANSWER_SYSTEM = """You are a biomedical research assistant answering from a knowledge graph
built from PubMed abstracts on brain cancer. Use ONLY the provided context (graph facts +
abstract snippets). If the context is insufficient, say so plainly.
- Be concise and precise.
- Cite evidence with the PMID in square brackets, e.g. [PMID:12345678], right after the claim.
- Do not invent entities, relations, or PMIDs that are not in the context."""
