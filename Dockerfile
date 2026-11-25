FROM node:20-bookworm-slim AS frontend

WORKDIR /build/operations-and-maintenance
COPY operations-and-maintenance/package*.json ./
RUN npm ci
COPY operations-and-maintenance/ ./
RUN npm run build


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1 \
    HF_DATASETS_OFFLINE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY inference_service.py kylin_rag.py ./
COPY ["kylin_faq.index", "kylin_faq_meta.pkl", "银河麒麟桌面操作系统V11 2603常见问题(FAQ) .pdf", "./"]
COPY program2 ./program2
COPY scripts ./scripts
RUN mkdir -p /app/data/rag_store
COPY operations-and-maintenance ./operations-and-maintenance
COPY --from=frontend /build/operations-and-maintenance/dist ./operations-and-maintenance/dist

EXPOSE 8000 8001

WORKDIR /app/program2

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
