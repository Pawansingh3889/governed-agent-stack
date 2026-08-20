# FloorMind — Multi-stage Docker build.
# Inspired by PyCon DE 2026: "Building Secure Environments for CLI Code Agents" (Nezbeda).
#
# Stage 1: builder  — install deps (including build tools)
# Stage 2: runtime  — copy only wheels + app (smaller image, no compiler)

# ---------------------------------------------------------------------------
# Stage 1: builder
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps required to compile C extensions (psycopg2, pyodbc, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    libpq-dev \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app

# Runtime-only system deps (no compiler, no -dev packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    unixodbc \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Data + log directories
RUN mkdir -p /app/data /app/logs

# Non-root user for security
RUN useradd -m -u 1000 floormind && \
    chown -R floormind:floormind /app

USER floormind

VOLUME ["/app/data", "/app/logs"]

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
