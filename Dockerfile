FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY run.py ./
COPY main ./main
COPY docker ./docker

RUN chmod +x /app/docker/entrypoint_node.sh

ENV PYTHONUNBUFFERED=1
# HASHCOIN_GENESIS_SEED y HASHCOIN_SHARED_KEY deben inyectarse en runtime
# (ver .env.example). No usar valores por defecto en producción.

ENTRYPOINT ["python", "run.py"]
