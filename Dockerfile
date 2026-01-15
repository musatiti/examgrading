FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    flask \
    pdf2image \
    pillow \
    torch --index-url https://download.pytorch.org/whl/cpu \
    transformers \
    sentencepiece

EXPOSE 5000
CMD ["python", "app.py"]



