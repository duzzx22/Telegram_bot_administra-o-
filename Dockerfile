# Build stage
FROM python:3.11-slim as builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Criar usuário não-root
RUN useradd -m -u 1000 botuser

# Copiar dependências do builder
COPY --from=builder /root/.local /home/botuser/.local
COPY --chown=botuser:botuser main.py .

# Diretórios para dados
RUN mkdir -p data logs && chown -R botuser:botuser data logs

ENV PATH=/home/botuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

USER botuser

# Health check
HEALTHCHECK --interval=5m --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('data/management.db').cursor().execute('SELECT 1')"

CMD ["python", "-u", "main.py"]
