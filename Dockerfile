FROM python:3.12-slim
ARG APP_VERSION=local
LABEL org.opencontainers.image.source="https://github.com/JonasPC18/Projeto_DevOps_Fase1" \
    org.opencontainers.image.title="API de tarefas - DevOps"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    DB_PATH=/data/tasks.db \
    APP_VERSION=${APP_VERSION}
WORKDIR /app
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall -y pip setuptools wheel \
    && useradd --uid 10001 --create-home appuser \
    && mkdir /data && chown appuser:appuser /data
COPY --chown=appuser:appuser app.py /app/app.py
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["python", "app.py"]
