FROM python:3.9-slim

# Setze das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere alle Skripte
COPY generate_jwks.py generate_jwt.py ./

# Installiere die cryptography-Bibliothek
RUN pip install --no-cache-dir cryptography==43.0.1

# Führe das Skript aus (default: generate_jwks.py)
CMD ["python3", "generate_jwks.py"]