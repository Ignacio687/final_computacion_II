FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY run.py ./
COPY main ./main
COPY docker ./docker

RUN chmod +x /app/docker/entrypoint_node.sh

ENV PYTHONUNBUFFERED=1
ENV HASHCOIN_GENESIS_SEED=hashcoin-docker-seed
ENV HASHCOIN_SHARED_KEY=AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE=

ENTRYPOINT ["python", "run.py"]
