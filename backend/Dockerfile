FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# data/ lives alongside backend/ in the repo (REPO_ROOT in app/core/config.py resolves
# to "/" inside this image), so it's duplicated into backend/data for the build context
# and copied to the path the app actually expects it at.
RUN rm -rf /data && cp -r data /data

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python -m app.ml.pipeline.seed && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
