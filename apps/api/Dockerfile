# bookworm = Debian 12 (suporte de segurança previsível); evita trixie/sid com CVEs ainda sem backport.
FROM python:3.12-slim-bookworm
# Atualizações de segurança do SO antes de instalar dependências da aplicação.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY apps ./apps
RUN pip install --no-cache-dir -e ".[api]" \
    && addgroup --system app \
    && adduser --system --ingroup app --home /app app \
    && chown -R app:app /app
EXPOSE 8000
USER app
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status==200 else 1)" || exit 1
CMD ["uvicorn", "otm_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
