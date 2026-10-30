"""Central configuration (all overridable via environment variables)."""
import os

# --- Neo4j ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

# --- NER (entity extraction, unchanged from v1) ---
NER_MODEL = os.getenv("NER_MODEL", "Kushtrim/ModernBERT-base-biomedical-ner")
HF_TOKEN = os.getenv("HF_TOKEN")

# --- Embeddings (NEW in v2: for semantic / vector retrieval) ---
# A biomedical sentence embedder so abstracts & questions live in the same space.
EMBED_MODEL = os.getenv("EMBED_MODEL", "pritamdeka/S-PubMedBert-MS-MARCO")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))

# --- LLM (NEW in v2: pluggable, OpenAI-compatible) ---
# Defaults target a LOCAL Ollama server. Point these at OpenAI/Groq/vLLM by setting
# LLM_BASE_URL + LLM_API_KEY. The code only speaks the OpenAI chat-completions API.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")          # dummy for Ollama
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b-instruct")  # small, fits an 8GB GPU
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

# --- Retrieval knobs ---
VECTOR_TOP_K = int(os.getenv("VECTOR_TOP_K", "5"))       # abstracts from vector search
GRAPH_HOPS = int(os.getenv("GRAPH_HOPS", "1"))           # entity-graph expansion depth
ENABLE_TEXT2CYPHER = os.getenv("ENABLE_TEXT2CYPHER", "1") == "1"

VECTOR_INDEX_NAME = "abstract_embeddings"
