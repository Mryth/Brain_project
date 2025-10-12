# Utiliser une image Python 3.9 slim comme base
FROM python:3.9-slim

# Définir le répertoire de travail
WORKDIR /api

# Copier le fichier des dépendances
COPY requirements.txt requirements.txt

# Installer les dépendances
# On installe torch sans CUDA pour alléger l'image
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copier le reste de l'application
COPY . .

# Exposer le port de l'API
EXPOSE 8000

# Commande pour lancer l'application avec Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

