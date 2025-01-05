# Используем официальный образ Python
FROM python:3.13-slim
# Устанавливаем необходимые пакеты
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

# Устанавливаем переменную окружения для корректной работы Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Копируем файл requirements.txt, если он существует
COPY requirements.txt /app/

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота в контейнер
COPY . /app/

# Указываем команду для запуска приложения
CMD ["python", "main.py"]
