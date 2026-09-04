FROM python:3.11-slim

WORKDIR /app

# Install deps first (better caching)
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "networkx>=3.2" "numpy>=1.26" "pandas>=2.1" "scikit-learn>=1.4" \
    "fastapi>=0.110" "uvicorn>=0.29" "pydantic>=2.6" "python-dateutil>=2.9" "httpx>=0.27"

# Copy the app + data
COPY nexus ./nexus
COPY data ./data

# Render provides $PORT
ENV PORT=8000
EXPOSE 8000
CMD uvicorn nexus.api.main:app --host 0.0.0.0 --port ${PORT}
