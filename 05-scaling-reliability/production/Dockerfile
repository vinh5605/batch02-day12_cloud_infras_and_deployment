# ============================================================
# Stateless Agent — Dockerfile
#
# Build từ project root (context: ../.. trong docker-compose.yml):
#   docker build -f 05-scaling-reliability/production/Dockerfile -t agent-stateless .
# ============================================================
FROM python:3.11-slim

WORKDIR /app

COPY 05-scaling-reliability/production/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY 05-scaling-reliability/production/app.py .
COPY utils/mock_llm.py /app/utils/mock_llm.py

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
