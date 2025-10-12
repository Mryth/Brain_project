import streamlit as st
import requests
import time

# --- CONFIGURATION ---
API_URL = "http://api:8000"  # Nom du service dans docker-compose

# --- FONCTIONS UTILITAIRES ---
def get_stats():
    """Récupère et affiche les statistiques du graphe."""
    try:
        response = requests.get(f"{API_URL}/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erreur API (stats): {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Connexion à l'API impossible. Le service backend est-il en cours d'exécution ?")
        return None
    except Exception as e:
        st.error(f"Une erreur est survenue : {e}")
        return None

# --- INTERFACE UTILISATEUR ---
st.set_page_config(page_title="Brain Cancer Graph", layout="wide", initial_sidebar_state="collapsed")
st.title("🧠 Brain Cancer Knowledge Graph")
st.markdown("Interface pour interagir avec le pipeline de création du graphe de connaissances.")

# --- SECTION 1: MISE À JOUR DU GRAPHE ---
st.header("1. Mise à jour du Graphe")
with st.form("update_form"):
    n_articles = st.number_input(
        "Nombre d'articles PubMed à traiter",
        min_value=1, max_value=500, value=50,
        help="Choisissez un nombre d'articles à extraire de PubMed pour enrichir le graphe."
    )
    submitted = st.form_submit_button("🚀 Lancer la mise à jour")

if submitted:
    with st.spinner(f"Traitement de {n_articles} articles en cours... Cela peut prendre plusieurs minutes."):
        try:
            start_time = time.time()
            response = requests.post(f"{API_URL}/update-graph/{n_articles}", timeout=600) # Timeout long
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                st.success(f"**Mise à jour terminée en {end_time - start_time:.2f} secondes !**")
                st.json(data)
            else:
                st.error(f"Erreur de l'API : {response.status_code}")
                st.json(response.json())

        except requests.exceptions.Timeout:
            st.error("Le délai d'attente a été dépassé. Le traitement est probablement trop long.")
        except Exception as e:
            st.error(f"Erreur de connexion : {e}")

# --- SECTION 2: STATISTIQUES ET ACTIONS ---
st.header("2. État du Graphe et Actions")
stats_placeholder = st.empty()

def display_stats():
    stats = get_stats()
    if stats:
        with stats_placeholder.container():
            col1, col2 = st.columns(2)
            col1.metric("Nœuds dans le graphe", f"{stats.get('nodes', 0):,}")
            col2.metric("Relations dans le graphe", f"{stats.get('relationships', 0):,}")

# Affichage initial
display_stats()

col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 Rafraîchir les stats"):
        display_stats()
with col2:
    if st.button("🗑️ Vider le buffer d'articles"):
        try:
            response = requests.delete(f"{API_URL}/clear-buffer", timeout=30)
            if response.status_code == 200:
                st.success(f"Buffer vidé. {response.json().get('abstracts_deleted', 0)} articles supprimés.")
            else:
                st.error("Échec de la suppression du buffer.")
        except Exception as e:
            st.error(f"Erreur : {e}")

