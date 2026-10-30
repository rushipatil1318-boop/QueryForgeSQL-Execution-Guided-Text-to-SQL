FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY queryforgesql ./queryforgesql
COPY scripts ./scripts
COPY configs ./configs
RUN mkdir -p /app/data /app/runs && chown -R 10001:10001 /app
USER 10001:10001
CMD ["python", "-m", "scripts.run_demo"]
