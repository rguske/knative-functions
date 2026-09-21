FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py .

RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

ENV FLASK_APP=handler.py
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "flask run --host=0.0.0.0 --port=${PORT}"]
