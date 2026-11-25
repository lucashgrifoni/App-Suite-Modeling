# bookworm = Debian 12 (suporte de segurança previsível); evita trixie/sid com CVEs ainda sem backport.
#
# Fixada por digest, não por tag: `python:3.12-slim-bookworm` é uma etiqueta móvel, por isso dois
# `docker build` em dias diferentes produziam imagens com conjuntos de pacotes do SO diferentes e
# sem registo de qual foi entregue — e um repontamento a montante entrava sem ser visto. É a mesma
# disciplina que os workflows já aplicam a 100% dos `uses:` de terceiros (todos com SHA de 40
# caracteres) e que parava na fronteira do contentor. A etiqueta fica no próprio `FROM` para
# continuar legível; o digest é o que o Docker resolve.
#
# Digest do índice OCI multi-arquitectura, confirmado por duas vias independentes em 2026-08-17:
# o cabeçalho `docker-content-digest` da API do registry e `docker buildx imagetools inspect`.
# Actualizá-lo é trabalho de manutenção: acrescentar o ecossistema `docker` a .github/dependabot.yml
# põe-no na mesma janela de arrefecimento de 7 dias do resto (esse ficheiro fica fora deste lote).
FROM python:3.12-slim-bookworm@sha256:a116514e19457bcb7af7efe9c3dd0b9b71e85b317694e7882a1c52aa15a78134
# Atualizações de segurança do SO antes de instalar dependências da aplicação.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md requirements.txt requirements-build-backend.txt ./
COPY packages ./packages
COPY apps ./apps
RUN python -m pip install --no-cache-dir --require-hashes --only-binary :all: -r requirements-build-backend.txt \
    && python -m pip install --no-cache-dir --require-hashes --only-binary :all: -r requirements.txt \
    && python -m pip install --no-cache-dir --no-index --no-build-isolation --no-deps -e ".[api]" \
    && python -m pip check \
    && addgroup --system app \
    && adduser --system --ingroup app --home /app app \
    && chown -R app:app /app
EXPOSE 8000
USER app
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status==200 else 1)" || exit 1
CMD ["uvicorn", "otm_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
