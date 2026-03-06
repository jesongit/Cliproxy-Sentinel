FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt pyproject.toml README.md /app/
COPY src /app/src
COPY config.example.yaml /app/config.example.yaml

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip install --no-cache-dir -e .

CMD ["python", "-m", "cliproxyapi.app", "--config", "/app/config.yaml"]

