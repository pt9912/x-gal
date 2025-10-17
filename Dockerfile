# Gateway Abstraction Layer (GAL) - Multi-stage Docker Build
FROM python:3.12-slim as builder

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim as production

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive

# Create non-root user for security
RUN groupadd -r gal && useradd -r -g gal gal

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    bash \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/gal/.local

# Copy application code
COPY --chown=gal:gal . .

# Make sure the user's local bin is in PATH
ENV PATH=/home/gal/.local/bin:$PATH

# Make CLI executable
RUN chmod +x gal-cli.py

# Create directories for generated configs
RUN mkdir -p generated examples/output && \
    chown -R gal:gal generated examples/output

# Switch to non-root user
USER gal

# Set Python path
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python gal-cli.py list-providers || exit 1

# Default command
ENTRYPOINT ["python", "gal-cli.py"]
CMD ["--help"]

# OCI Standard Labels
LABEL org.opencontainers.image.title="GAL - Gateway Abstraction Layer"
LABEL org.opencontainers.image.description="Provider-agnostic API Gateway configuration system supporting Envoy, Kong, APISIX, and Traefik"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="Dietmar Burkard"
LABEL org.opencontainers.image.url="https://github.com/pt9912/x-gal"
LABEL org.opencontainers.image.documentation="https://github.com/pt9912/x-gal/blob/main/README.md"
LABEL org.opencontainers.image.source="https://github.com/pt9912/x-gal"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.vendor="Dietmar Burkard"