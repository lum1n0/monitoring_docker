FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта (включая management/commands)
COPY monitor/ .

# Создание статических файлов
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# CMD: запуск с миграциями, синхронизацией и созданием суперпользователя
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py setup_docker --sync && python manage.py ensure_superuser --noinput && gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 monitor.wsgi:application"]
