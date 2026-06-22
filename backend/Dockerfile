FROM python:3.12-slim

WORKDIR /app

COPY requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt

COPY main.py scorer_llm.py scorer_tribe.py typographic.py index.py roi.py cache.py models.py ./
COPY calibration/ calibration/

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
