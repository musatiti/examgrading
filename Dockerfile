FROM python:3.10-slim

ARG GEMINI_API_KEY
ENV GEMINI_API_KEY=$GEMINI_API_KEY

WORKDIR /app
COPY . .

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    flask \
    google-generativeai \
    pdf2image \
    pytesseract


EXPOSE 5000
CMD ["python", "app.py"]
