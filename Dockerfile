# Используем официальный образ Python
FROM python:3.13-slim
# Устанавливаем необходимые пакеты
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Обновляем pip до последней версии
RUN pip install --upgrade pip

# Устанавливаем переменную окружения для корректной работы Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Устанавливаем зависимости, обновляя их до последних версий.
# Добавляем spotdl, так как он используется в downloader.py.
RUN pip install --no-cache-dir --upgrade \
    aiogram \
    python-dotenv \
    requests \
    beautifulsoup4 \
    youthon \
    yt-dlp \
    spotdl

# Копируем код бота в контейнер
COPY . /app/

# Указываем команду для запуска приложения
CMD ["python", "main.py"]