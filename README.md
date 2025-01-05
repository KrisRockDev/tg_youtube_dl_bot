# YouTube, Instagram, TikTok, X (Twitter), Spotify, Pinterest downloader bot
![version](https://img.shields.io/badge/Project_version-1.0-blue)
![licence](https://img.shields.io/badge/License-MIT-green)
![made with love](https://img.shields.io/badge/Made_with-Love-red)

Telegram bot для скачивания видео с YouTube, Instagram, TikTok, X (Twitter), Spotify and Pinterest

<<<<<<< HEAD
Fork from `https://github.com/anekobtw/youtube-dl-bot.git`

#### Для запуска локально:
1. Клонирование репозитория:  
    ```sh
    git clone https://github.com/KrisRockDev/tg_youtube_dl_bot.git
    ```
2. Перейдите в директорию tg_youtube_dl_bot:
   ```sh
   cd tg_youtube_dl_bot
   ```
3. Устанавливаем зависимости:
   ```sh
   pip install -r requirements.txt
   ```
4. Запускаем бот:
   ```sh
   python main.py
   ```

#### Для запуска в Docker-контейнера на собственном сервере:

=======
1. Клонирование репозитория:  
    ```sh
    git clone https://github.com/KrisRockDev/tg_youtube_dl_bot.git
    ```
2. Перейдите в директорию tg_youtube_dl_bot:
   ```sh
   cd tg_youtube_dl_bot
   ```
   
3. Сборка Docker-образа:
   ```bash
   sudo docker build -t krisrockdev/tg_youtube_dl_bot:1.0 .
   ```

4. Запуск Docker-контейнера:
>>>>>>> origin/master
   ```bash
   sudo docker run \
   --restart on-failure \
   -e TOKEN='TELEGRAM-TOKEN' \
   --name tg_youtube_dl_bot_container \
   krisrockdev/tg_youtube_dl_bot:1.0
<<<<<<< HEAD
   ```
=======
   ```
>>>>>>> origin/master
