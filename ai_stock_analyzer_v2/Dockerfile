FROM python:3.13-slim

WORKDIR /app

# Install a pinned uv binary, then install only the locked runtime dependencies.
COPY pyproject.toml uv.lock ./
RUN python -m pip install --no-cache-dir --only-binary=:all: "uv==0.12.1" \
    && uv sync --locked --no-dev --no-install-project --no-build \
    && rm -rf /root/.cache/uv

ENV PATH="/app/.venv/bin:${PATH}"

# The integrated app (app.py plus pages/, modules/, components/, services/, engine/ ...)
# imports first-party packages from across the repository, so the whole source tree is
# copied. .dockerignore keeps tests, secrets, local databases and archives out of the image.
COPY . .

# Run the application as an unprivileged user.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app /home/appuser
USER appuser

EXPOSE 8501

# Container-level liveness check for the Streamlit HTTP endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).read()" || exit 1

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
