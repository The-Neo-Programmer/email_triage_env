FROM python:3.11-slim

WORKDIR /app

# Install server dependencies only (for a leaner server-only build)
COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt \
    && pip install --no-cache-dir openenv-core openenv \
    && python -c "import importlib.util as u; assert u.find_spec('openenv'), 'openenv namespace missing'; print('openenv import OK')"

# Copy only the server and project source files
COPY models.py ./models.py
COPY data/ ./data/
COPY server/ ./server/

# Ensure project root modules are importable
ENV PYTHONPATH=/app

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

ENV ENABLE_WEB_INTERFACE=false

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
