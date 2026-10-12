FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and source code
COPY pyproject.toml README.md ./
COPY proofqa/ ./proofqa/
COPY apps/ ./apps/
COPY docs/ ./docs/

# Install python dependencies and seed database
RUN pip install --no-cache-dir -e .
RUN python apps/shop_twin/backend/seed.py

EXPOSE 8000

ENV PORT=8000
ENV SHOP_DB_PATH=/app/apps/shop_twin/backend/seed.db

CMD ["python", "apps/shop_twin/backend/main.py", "8000"]
