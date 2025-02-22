FROM python:3.8-slim

WORKDIR /app

# Set environment variables
ENV API_URL=$OLLAMA_API_URL \
    MY_GITHUB_TOKEN=$MY_GITHUB_TOKEN \
    OWNER=$OWNER \
    REPO=$REPO \
    PR_NUMBER=$PR_NUMBER \
    CUSTOM_PROMPT=$CUSTOM_PROMPT \
    RESPONSE_LANGUAGE=$RESPONSE_LANGUAGE

COPY requirements.txt .
COPY src/ ./src/

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "src/ollama_review.py"]