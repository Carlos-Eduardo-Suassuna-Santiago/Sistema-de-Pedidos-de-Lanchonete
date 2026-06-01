FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copia e instala dependências primeiro para aproveitar cache de camadas
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copia o código da aplicação
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
