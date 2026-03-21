# Multi-stage Dockerfile for Spendah

# Backend stage
FROM python:3.11-slim as api

WORKDIR /app

RUN groupadd -r spendah && useradd -r -g spendah spendah

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

RUN mkdir -p /app/data/imports/inbox /app/data/imports/processed /app/data/imports/failed \
    && chown -R spendah:spendah /app

USER spendah

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


# Frontend build stage
FROM node:20-alpine as frontend-build

WORKDIR /app

ARG VITE_API_PORT=8000
ENV VITE_API_PORT=$VITE_API_PORT

COPY frontend/package*.json ./

RUN npm install

COPY frontend/ .

RUN npm run build


# Frontend serve stage
FROM node:20-alpine as frontend

WORKDIR /app

RUN addgroup -S spendah && adduser -S spendah -G spendah

RUN npm install -g serve

COPY --from=frontend-build --chown=spendah:spendah /app/dist ./dist

USER spendah

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5173/ || exit 1

CMD ["serve", "-s", "dist", "-l", "5173"]
