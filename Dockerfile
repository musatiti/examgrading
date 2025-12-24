FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install flask
RUN pip install streamlit
RUN pip install openai
RUN pip install pypdf

EXPOSE 8080
CMD ["streamlit", "run", "app.py"]

