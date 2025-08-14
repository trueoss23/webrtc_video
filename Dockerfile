FROM python:3.13-slim

WORKDIR /app


ENV PYTHONPATH=/app

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

COPY app/ .

EXPOSE 8001
CMD ["uvicorn", "main:app", "--reload", "--host=0.0.0.0",  "--port=8000"]