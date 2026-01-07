# Multi-stage Dockerfile for Spendah

# Backend stage
FROM python:3.11-slim as api

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ .

# Create data directory
RUN mkdir -p /app/data/imports/inbox /app/data/imports/processed /app/data/imports/failed

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


# Frontend build stage
FROM node:20-alpine as frontend-build

WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy frontend source
COPY frontend/ .

# Build the frontend
RUN npm run build


# Frontend serve stage
FROM node:20-alpine as frontend

WORKDIR /app

# Install serve to serve the static files
RUN npm install -g serve

# Copy built files from build stage
COPY --from=frontend-build /app/dist ./dist

# Expose port
EXPOSE 5173

# Serve the static files
CMD ["serve", "-s", "dist", "-l", "5173"]
