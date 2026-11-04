FROM python:3.13-slim

RUN pip install --no-cache-dir aiohttp==3.12.13

COPY server.py /app/server.py

EXPOSE 80
HEALTHCHECK --interval=2s --timeout=2s --retries=15 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost/_control/health')"

CMD ["python", "/app/server.py"]
