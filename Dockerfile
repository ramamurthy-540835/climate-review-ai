FROM python:3.12-slim
WORKDIR /app
COPY requirements.api.txt .
RUN pip install --no-cache-dir -r requirements.api.txt
COPY . .
ENV PORT=8080 PYTHONUNBUFFERED=1
CMD exec uvicorn api:app --host 0.0.0.0 --port ${PORT}
