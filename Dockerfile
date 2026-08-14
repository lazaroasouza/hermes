FROM python:3.11-slim

# Instala ferramentas de sistema essenciais para o Hermes rodar comandos e MCPs
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia arquivos de dependências
COPY requirements.txt .

# Instala pacotes do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código da aplicação, agentes, skills e MCPs
COPY . .

# Expõe a porta do servidor Web
EXPOSE 8000

# Variáveis de ambiente padrão para evitar travamentos em comandos interativos
ENV PYTHONUNBUFFERED=1
ENV CI=true
ENV DEBIAN_FRONTEND=noninteractive

# Inicia a API e o Loop Autônomo em segundo plano
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
