
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_SECRET_KEY="VisionaryGradersSuperSecretKey2026!"

WORKDIR /app


RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    curl \
    gnupg \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*


RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc -o /etc/apt/trusted.gpg.d/microsoft.asc \
    && curl -fsSL https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY . .

EXPOSE 5000


CMD ["gunicorn", "-w", "4", "--threads", "4", "-b", "0.0.0.0:5000", "--timeout", "300", "app:app"]