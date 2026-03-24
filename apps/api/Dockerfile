FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY apps ./apps
RUN pip install --no-cache-dir -e ".[api]"
EXPOSE 8000
CMD ["uvicorn", "otm_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
