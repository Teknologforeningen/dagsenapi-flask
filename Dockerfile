FROM python:3.12.0-alpine3.18

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD gunicorn -w 3 'app:app' --bind 0.0.0.0:5000