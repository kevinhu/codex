FROM python:3.11.8-bullseye AS python-base

# Set environment variables for Python, Pip, Poetry and project directories
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PROJECT_DIR="/code"

ENV PATH="$POETRY_HOME/bin:$PROJECT_DIR/.venv/bin:$PATH"

FROM python-base AS production

# Set environment variables for FastAPI
ENV FASTAPI_ENV=production

# Install system dependencies
RUN buildDeps="build-essential" \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
    curl \
    vim \
    netcat \
    && apt-get install -y --no-install-recommends $buildDeps \
    && rm -rf /var/lib/apt/lists/*

# Set Poetry version
ARG POETRY_VERSION=""
ENV POETRY_VERSION=${POETRY_VERSION}

# Install Poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://install.python-poetry.org | python3 - && chmod a+x /opt/poetry/bin/poetry
RUN poetry self add poetry-plugin-export
RUN pip install uv==0.1.24

# Install package dependencies with uv
COPY poetry.lock pyproject.toml ./
RUN poetry export -f requirements.txt --output requirements.txt
RUN poetry run uv pip install -r requirements.txt

# Set working directory and copy package files
WORKDIR $PROJECT_DIR
RUN mkdir logs
COPY server ./server

EXPOSE 443

# Set default command to run the application
CMD [""]