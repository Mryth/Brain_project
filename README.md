# 🧠 Brain Cancer Knowledge Graph

Une application web full-stack pour construire un graphe de connaissances à partir de la littérature scientifique biomédicale. L'application extrait les résumés d'articles de PubMed, utilise un modèle NLP pour identifier des entités pertinentes (gènes, maladies, molécules), et modélise leurs relations dans une base de données graphe Neo4j.

## 📋 Table des matières

- [Architecture](#-architecture)
- [Stack Technique](#-stack-technique)
- [Installation](#-installation-et-lancement)
- [Utilisation](#-utilisation)
- [Structure du Projet](#-structure-du-projet)
- [Dépannage](#-dépannage)
- [Auteur](#-auteur)

## 🏛️ Architecture

L'application est construite sur une architecture microservices conteneurisée avec Docker, assurant une séparation claire des responsabilités et une facilité de déploiement.

### Composants

1. **Frontend (Streamlit)**
   - Interface utilisateur web simple et interactive
   - Lancement du traitement des données
   - Visualisation des statistiques du graphe
   - Communication avec le backend via HTTP

2. **Backend (API FastAPI)**
   - Cœur logique de l'application
   - API REST exposant des endpoints pour :
     - Extraction des données de PubMed
     - Orchestration du traitement NLP (NER)
     - Génération et exécution des requêtes Cypher

3. **Base de Données (Neo4j)**
   - Stockage des entités médicales (nœuds)
   - Modélisation des relations (arêtes)
   - Analyse de réseaux complexes
   - Découverte de connexions cachées

## 🛠️ Stack Technique

- **Orchestration** : Docker & Docker Compose
- **Frontend** : Streamlit
- **Backend** : FastAPI (Python 3.9)
- **Base de Données** : Neo4j 4.4
- **NLP / Machine Learning** :
  - Librairie `transformers` (Hugging Face)
  - Modèle NER : `Kushtrim/ModernBERT-base-biomedical-ner`
- **Communication API** : Librairie `requests`

## 🚀 Installation et Lancement

Ce projet est entièrement conteneurisé. Les seules dépendances requises sont `Git`, `Docker` et `Docker Compose`.

### 1️⃣ Prérequis (Linux)

Pour éviter les problèmes de permissions avec Docker, ajoutez votre utilisateur au groupe `docker` :

```bash
sudo usermod -aG docker $USER
```

> **Note** : Vous devrez vous déconnecter et vous reconnecter pour que ce changement soit pris en compte.

### 2️⃣ Cloner le Dépôt

```bash
git clone https://github.com/VOTRE_NOM_UTILISATEUR/NOM_DU_REPO.git
cd NOM_DU_REPO
```

### 3️⃣ Configurer les Variables d'Environnement

Créez un fichier `.env` à la racine du projet pour stocker votre token Hugging Face :

```bash
touch .env
```

Ajoutez votre token dans ce fichier :

```env
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
```

> **Important** : Remplacez `hf_xxxxxxxxxxxxxxxxxxxx` par votre propre token d'accès Hugging Face.

### 4️⃣ Lancer l'Application

Construisez et démarrez tous les services avec Docker Compose :

```bash
docker-compose up --build -d
```

> **Note** : Le premier lancement peut prendre plusieurs minutes pour télécharger le modèle NLP. Les lancements suivants seront beaucoup plus rapides.

## 💻 Utilisation

Une fois les conteneurs démarrés, accédez aux différents services :

| Service | URL | Identifiants |
|---------|-----|--------------|
| **Interface Utilisateur** (Streamlit) | http://localhost:8501 | - |
| **Navigateur Neo4j** | http://localhost:7474 | User: `neo4j`<br>Password: `password123` |
| **Documentation API** (FastAPI) | http://localhost:8000/docs | - |

### Workflow

1. Accédez à l'interface Streamlit sur http://localhost:8501
2. Lancez l'extraction des données PubMed
3. Visualisez les statistiques du graphe généré
4. Explorez les relations dans Neo4j Browser

### Arrêter l'Application

Pour arrêter tous les conteneurs :

```bash
docker-compose down
```

Pour arrêter et supprimer les volumes (réinitialisation complète) :

```bash
docker-compose down -v
```

## 📊 Structure du Projet

```
.
├── docker-compose.yml
├── .env
├── frontend/
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
├── backend/
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── services/
└── README.md
```

## 🐛 Dépannage

### Le modèle NLP ne se télécharge pas
- Vérifiez que votre token Hugging Face est valide
- Assurez-vous que le fichier `.env` est bien à la racine du projet

### Problèmes de permissions Docker (Linux)
- Vérifiez que vous êtes dans le groupe docker : `groups $USER`
- Redémarrez votre session après avoir ajouté l'utilisateur au groupe

### Neo4j ne démarre pas
- Vérifiez que les ports 7474 et 7687 ne sont pas déjà utilisés
- Consultez les logs : `docker-compose logs neo4j`

### L'API FastAPI ne répond pas
- Vérifiez les logs : `docker-compose logs backend`
- Assurez-vous que le port 8000 est disponible

## 👤 Auteur

- GitHub: [@Mryth](https://github.com/Mryth)
