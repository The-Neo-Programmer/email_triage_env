FROM python:3.11-slim

WORKDIR /app

# Install server and inference dependencies in one layer
COPY server/requirements.txt ./server/requirements.txt
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt -r requirements.txt \
    && (pip install --no-cache-dir openenv-core || pip install --no-cache-dir openenv) \
    && python -c "import importlib.util as u; assert (u.find_spec('openenv') or u.find_spec('openenv_core')), 'OpenEnv module missing'; print('openenv namespace import OK')"

# Copy the entire project into the container
COPY . /app/

# Ensure all modules at project root are importable
ENV PYTHONPATH=/app

# Hugging Face Spaces requires port 7860
EXPOSE 7860

# Keep custom UI route deterministic for Spaces
ENV ENABLE_WEB_INTERFACE=false

# Use python urllib for healthcheck — no curl needed on slim image
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

# Start the FastAPI environment server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
