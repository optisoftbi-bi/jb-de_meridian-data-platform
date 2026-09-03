# תחשוב על קובץ הזה כעל הוראות לבניית מחשב לינוקס קטן ומוכן מראש עבור ה־ג'בס שלך.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/





