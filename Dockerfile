FROM python:3.12-slim

WORKDIR /app

COPY "AI Engineering Bootcamp & Certificate/Week 1/Assignment 1/Build & Deploy FastAPI LLM API/" .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
