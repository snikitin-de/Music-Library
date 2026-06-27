FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Europe/Moscow \
    MUSIC_LIBRARY_PATH=/music

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
        libchromaprint-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-shazam.txt ./
RUN pip install -r requirements.txt \
    && pip install -r requirements-shazam.txt

COPY beets-config.yaml ./
COPY scripts ./scripts

RUN mkdir -p /app/reports /config/beets /music

EXPOSE 8765

CMD ["python", "scripts/report_server.py", "--host", "0.0.0.0", "--port", "8765"]
