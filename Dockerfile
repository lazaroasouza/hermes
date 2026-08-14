FROM python:3.11-slim

WORKDIR /app

# Instalar dependências de sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
