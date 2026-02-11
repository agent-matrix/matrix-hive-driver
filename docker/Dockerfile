FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -e .

EXPOSE 7000

CMD ["python", "-m", "matrix_hive_driver.api.app"]
