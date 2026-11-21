# Veltrionyx - container for Google Cloud Run (works on any Docker host)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ANONYMIZED_TELEMETRY=False \
    TOKENIZERS_PARALLELISM=false \
    HF_HOME=/opt/hf-cache

WORKDIR /app

# 1. CPU-only PyTorch. The default download includes GPU libraries and
#    makes the image about 2 GB bigger (slower start, more cost).
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

# 2. The other packages.
COPY requirements-deploy.txt .
RUN pip install -r requirements-deploy.txt

# 3. Download the MiniLM model into the image, so the app does not
#    download it every time a new copy starts.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# 4. From here the model is read from disk only.
ENV HF_HUB_OFFLINE=1

# 5. Your project (see .dockerignore for what is left out).
COPY . .

# Certificate list used to check the cloud database connection.
ENV MYSQL_SSL_CA=/etc/ssl/certs/ca-certificates.crt

# Cloud Run sets PORT, and the app reads it.
CMD ["python", "-m", "app.frontend.gradio_app"]
