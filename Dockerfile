FROM python:3.11-slim

LABEL maintainer="Bantu-OS Team"
LABEL description="Bantu-OS: AI-native Linux OS"

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    gcc \
    make \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy project
COPY pyproject.toml ./
COPY pytest.ini ./
COPY bantu_os/ ./bantu_os/
COPY tests/ ./tests/

# Install deps
RUN poetry install --with dev --no-interaction

# Entry point
ENTRYPOINT ["poetry", "run", "bantu"]
CMD ["--help"]