FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl supervisor nodejs npm && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY week3/assignment-1/nexus/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY week3/assignment-1/nexus/ .
COPY week3/assignment-1/nexus/supervisord.conf /etc/supervisor/conf.d/nexus.conf
EXPOSE 8003
HEALTHCHECK --interval=30s --timeout=10s --retries=5 --start-period=60s CMD curl -f http://localhost:8003/health || exit 1
CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/nexus.conf"]
