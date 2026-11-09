FROM python:3.13-slim
WORKDIR /app
COPY requirements-runtime.lock ./
RUN python -m pip install --no-cache-dir -r requirements-runtime.lock
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir --no-deps . \
    && useradd --create-home --uid 10001 appuser
COPY data ./data
COPY scripts ./scripts
USER appuser
CMD ["python", "scripts/demo.py"]
