# Dockerfile

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY hello.py .
COPY .env .

# CHANGED: instead of "python hello.py" (runs once and exits)
# now we run uvicorn (a web server that keeps running and listens for requests)
CMD ["uvicorn", "hello:app", "--host", "0.0.0.0", "--port", "8080"]
