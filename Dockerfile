# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 系統套件：psycopg2、weasyprint、Pillow、locale 都需要
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        cmake \
        libpq-dev \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libcairo2-dev \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
        shared-mime-info \
        fonts-noto-cjk \
        fonts-arphic-uming \
        fonts-arphic-ukai \
        libreoffice-writer \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt /app/
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ] ; then \
        pip install -r requirements-dev.txt ; \
    else \
        pip install -r requirements.txt ; \
    fi

COPY . /app/

EXPOSE 8000

# 預設啟動命令：本機 docker-compose 用 8000；Railway/Heroku 走 $PORT。
# 各服務（web / celery worker / celery beat）會在 docker-compose.yml 或 Railway service 設定
# 用自己的 startCommand override 這行。
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --worker-class gthread --workers 3 --threads 4 --timeout 60 --max-requests 1000 --max-requests-jitter 100"]
