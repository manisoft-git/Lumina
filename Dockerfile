FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends     gcc     libpq-dev     && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir eventlet gunicorn psycopg2-binary

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 lumina && chown -R lumina:lumina /app
USER lumina

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3     CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

EXPOSE 8080

# Production command with eventlet worker
CMD gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8080 --timeout 120 app:create_app()
