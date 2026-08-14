FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Static files don't need the persistent volume, so this is safe at build time
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# migrate runs at container START (not build time), because the persistent
# volume holding db.sqlite3 is only attached once the container is running
CMD ["sh", "-c", "python manage.py migrate && gunicorn root.wsgi:application --bind 0.0.0.0:8000"]
