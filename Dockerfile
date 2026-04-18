# ============================================================
# Bantu-OS — Multi-stage build
# ============================================================
# Stage 1: Build shell binary
FROM rust:1.88-slim AS shell-builder

WORKDIR /build/shell
COPY shell/ ./
RUN cargo build --release
RUN cp /build/shell/target/release/bantu /bantu-shell

# Stage 2: Python runtime + C init + services
FROM python:3.11-slim

LABEL maintainer="Malibongwe Ndhlovu <malibongwendhlovu05@gmail.com>"
LABEL description="Bantu-OS: AI-native Linux OS — AI-powered OS layer for Linux"
HOMEPAGE="https://github.com/MB-Ndhlovu/Bantu-Os"

WORKDIR /app

# Install system deps needed for C init + Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        make \
        procps \
        socat \
        vim \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (layer caching)
COPY requirements.txt ./

# Install Python runtime deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY bantu_os/  ./bantu_os/
COPY init/       ./init/
COPY tests/      ./tests/
COPY Makefile    ./
COPY start.sh    ./
COPY README.md    ./

# Copy pre-built shell binary from Stage 1
COPY --from=shell-builder /bantu-shell /app/shell/target/release/bantu

# Build the C init
WORKDIR /app/init
RUN make clean && make
WORKDIR /app

# Health check — kernel server responds to ping
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "
import socket, os
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
try:
    sock.connect('/tmp/bantu.sock')
    sock.sendall(b'{\"cmd\":\"ping\"}\\n')
    resp = sock.recv(256)
    sock.close()
    import json; assert json.loads(resp.decode()).get('ok') is True
except Exception:
    exit(1)
"

# Default: run the full Bantu-OS boot sequence
ENTRYPOINT ["./start.sh"]
