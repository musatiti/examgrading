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

RUN pip install flask
RUN pip install --upgrade google-generativeai==0.4.1
RUN pip install pypdf
RUN pip install pdf2image
RUN pip install pytesseract

EXPOSE 5000
CMD ["python", "app.py"]
