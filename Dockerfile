FROM python:3.8-slim

WORKDIR /app

COPY requirements.txt .
COPY src/ ./src/

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "src/ollama_review.py"]
