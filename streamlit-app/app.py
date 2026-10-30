"""Brain Cancer Graph RAG — Streamlit chat UI.
Ask questions, get grounded answers with PMID citations + the retrieved subgraph."""
import os
import tempfile
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://api:8000")

st.set_page_config(page_title="Brain Cancer Graph RAG", page_icon="🧠", layout="wide")
st.title("🧠 Brain Cancer Graph RAG")
st.caption("PubMed → knowledge graph + embeddings → hybrid retrieval (vector + graph + Text2Cypher) → grounded answer")

# ---------------- sidebar: ingest + stats ----------------
with st.sidebar:
    st.header("Knowledge base")
    n = st.number_input("Articles to ingest from PubMed", 1, 500, 20)
    if st.button("⤵️ Ingest / update graph", use_container_width=True):
        with st.spinner("Fetching PubMed, running NER + embeddings, writing Neo4j..."):
            try:
                r = requests.post(f"{API_URL}/update-graph/{int(n)}", timeout=1800)
                st.success(r.json() if r.ok else r.text)
            except Exception as e:
                st.error(f"Ingestion failed: {e}")
    st.divider()
    try:
        s = requests.get(f"{API_URL}/stats", timeout=30).json()
        c1, c2, c3 = st.columns(3)
        c1.metric("Nodes", s.get("nodes", "—"))
        c2.metric("Relations", s.get("relationships", "—"))
        c3.metric("Abstracts", s.get("abstracts", "—"))
    except Exception:
        st.info("Graph stats unavailable (is the API/Neo4j up?)")
    try:
        h = requests.get(f"{API_URL}/health", timeout=10).json()
        ok = h.get("llm_reachable")
        st.caption(f"LLM: `{h.get('llm_model')}` {'🟢 reachable' if ok else '🔴 unreachable'}")
    except Exception:
        st.caption("LLM backend: unknown")


def draw_subgraph(sg):
    nodes, edges = sg.get("nodes", []), sg.get("edges", [])
    if not nodes:
        st.info("No subgraph was retrieved for this question.")
        return
    try:
        from pyvis.network import Network
        palette = {"GENEPROD": "#4c8bf5", "DISEASE": "#e8710a", "SMALL_MOLECULE": "#34a853",
                   "CELL_TYPE": "#a142f4", "CELL_LINE": "#f4b400", "TISSUE": "#db4437"}
        net = Network(height="480px", width="100%", directed=True, bgcolor="#ffffff")
        for nd in nodes:
            net.add_node(nd["id"], label=nd["id"], title=nd["label"],
                         color=palette.get(nd["label"], "#9aa0a6"))
        for e in edges:
            net.add_edge(e["source"], e["target"], title=e["label"], label=e["label"])
        net.repulsion(node_distance=140)
        html = net.generate_html()
        st.components.v1.html(html, height=500, scrolling=True)
    except Exception as e:
        st.warning(f"Subgraph render failed ({e}); showing edges as text.")
        st.write([f"{e['source']} -[{e['label']}]-> {e['target']}" for e in edges])


# ---------------- chat ----------------
if "history" not in st.session_state:
    st.session_state.history = []

for turn in st.session_state.history:
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])

if q := st.chat_input("Ask about brain-cancer genes, mutations, treatments…"):
    st.session_state.history.append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        with st.spinner("Retrieving from the graph and generating…"):
            try:
                res = requests.post(f"{API_URL}/ask", json={"question": q}, timeout=600).json()
            except Exception as e:
                res = {"answer": f"Request failed: {e}", "sources": [], "subgraph": {}, "cypher": None}
        st.markdown(res.get("answer", "(no answer)"))
        st.session_state.history.append({"role": "assistant", "content": res.get("answer", "")})

        src = res.get("sources", [])
        if src:
            st.markdown("**Sources**")
            for s in src:
                st.markdown(f"- [PMID:{s['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{s['pmid']}/) "
                            f"· {s.get('title','')}  _(sim {s.get('score','')})_")
        with st.expander("🕸️ Retrieved subgraph", expanded=True):
            draw_subgraph(res.get("subgraph", {}))
        if res.get("cypher"):
            with st.expander("🔎 Text2Cypher query"):
                st.code(res["cypher"], language="cypher")
                if res.get("cypher_rows"):
                    st.write(res["cypher_rows"])
