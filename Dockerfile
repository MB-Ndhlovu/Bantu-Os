FROM python:3.11-slim

LABEL maintainer="Bantu-OS Team"
LABEL description="Bantu-OS: AI-native Linux OS"

WORKDIR /app

# Install system deps (gcc for C init, make, curl, git, rust, clang-format)
RUN apt-get update && apt-get install -y \
        gcc \
        make \
        curl \
        git \
        clang-format \
        wget \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy project files
COPY pyproject.toml ./
COPY pytest.ini ./
COPY bantu_os/ ./bantu_os/
COPY tests/ ./tests/
COPY shell/ ./shell/
COPY init/ ./init/
COPY Makefile ./

# Install Python deps
RUN poetry install --with dev --no-interaction

# Default command
ENTRYPOINT ["poetry", "run", "bantu"]