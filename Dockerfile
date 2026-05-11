FROM python:3.12-slim

WORKDIR /app

# System deps for Pillow font rendering + optional cairosvg
RUN apt-get update && apt-get install -y --no-install-recommends \
        fontconfig \
        fonts-dejavu-core \
        libcairo2 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for layer caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Source
COPY app /app/app
COPY make_blueprints /app/make_blueprints
COPY scripts /app/scripts
COPY seeds /app/seeds

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default to running niche history (cheap, env-driven smoke test)
CMD ["python", "-m", "app.niche_history"]
