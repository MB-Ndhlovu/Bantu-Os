FROM python:3.11-slim

LABEL maintainer="Malibongwe Ndhlovu <malibongwendhlovu05@gmail.com>"
LABEL description="Bantu-OS: AI-native Linux OS"
HOMEPAGE="https://github.com/MB-Ndhlovu/Bantu-Os"

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
        gcc \
        make \
        curl \
        git \
        clang-format \
        libasound2-dev \
        libusb-1.0-0-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (for shell build)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy dependency files first (for caching)
COPY requirements.txt ./

# Install Python runtime dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY bantu_os/ ./bantu_os/
COPY tests/ ./tests/
COPY shell/ ./shell/
COPY init/ ./init/
COPY Makefile ./
COPY start.sh ./
COPY README.md ./

# Build the Rust shell
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable && \
    cd shell && cargo build --release

# Default command — run the full system
CMD ["./start.sh"]
