FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY compliance_engine/ compliance_engine/
COPY batch_process.py .
COPY backend.py .
COPY sample_output/ sample_output/

EXPOSE 8080

CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8080"]
