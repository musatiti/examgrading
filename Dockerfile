FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install flask
RUN pip install streamlit

EXPOSE 8080
CMD ["python", "app.py"]
