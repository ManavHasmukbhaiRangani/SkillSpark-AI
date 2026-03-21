# ── SkillPathForge AI — Backend Dockerfile ───────────────────────
# Python 3.11 slim — smaller image, faster pulls
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# ── System dependencies ───────────────────────────────────────────
# libgomp1  → required by spaCy / torch
# gcc       → required by some pip builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN python -m spacy download en_core_web_lg

# ── Application code ──────────────────────────────────────────────
COPY . .

# ── Environment ───────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]