FROM python:3.11-slim

# Empêche Python de créer des .pyc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances système (PostGIS client, build)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code applicatif
COPY . .

# Port exposé
EXPOSE 8000

# Lancement API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
