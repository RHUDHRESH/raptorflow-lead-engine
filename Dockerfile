# Raptorflow Lead Engine - Production Dockerfile
# Multi-stage build for optimal size and performance

# Stage 1: Backend build
FROM python:3.11-slim as backend-build

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app/backend

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Stage 2: Frontend build
FROM node:18-alpine as frontend-build

WORKDIR /app/frontend

# Copy package files
COPY package*.json ./
COPY next.config.js ./
COPY tailwind.config.ts ./
COPY postcss.config.js ./
COPY tsconfig.json ./

# Install dependencies
RUN npm ci --only=production

# Copy frontend source
COPY app/ ./app/
COPY components/ ./components/
COPY lib/ ./lib/
COPY public/ ./public/

# Build frontend
RUN npm run build

# Stage 3: Production runtime
FROM python:3.11-slim as production

# Install system dependencies including Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy backend from build stage
COPY --from=backend-build --chown=appuser:appuser /app/backend ./backend

# Copy frontend build from build stage
COPY --from=frontend-build --chown=appuser:appuser /app/frontend/.next/standalone ./
COPY --from=frontend-build --chown=appuser:appuser /app/frontend/.next/static ./.next/static
COPY --from=frontend-build --chown=appuser:appuser /app/frontend/public ./public

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 8000  # Backend API
EXPOSE 3000  # Frontend

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden)
CMD ["sh", "-c", "cd backend && python main.py & cd .. && node server.js"]

