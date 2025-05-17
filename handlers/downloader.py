# Any changes to this file may negatively impact performance.

import os
import subprocess
from typing import Literal
import logging  # Добавлен logging
import shutil  # Добавлен shutil для удаления папок

import bs4
import requests
import youthon  # Убедитесь, что эта библиотека установлена, если нет - pip install youthon
import yt_dlp


class Downloader:
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    PLATFORM_PREFIXES = {
        "YouTube": ["https://www.youtube.com/watch?v=", 'https://youtube.com/watch?v', "https://youtu.be/",
                    "https://www.youtube.com/shorts/", "https://youtube.com/shorts/"],
        "X": ["https://x.com/", "https://twitter.com/"],
        "TikTok": ["https://www.tiktok.com/", "https://vt.tiktok.com/"],
        "Instagram": ["https://www.instagram.com/reel/", "https://instagram.com/reel/"],
        "Pinterest": ["https://pin.it/", "https://www.pinterest.com/pin/", "https://in.pinterest.com/pin/"],
        "Spotify": ["https://open.spotify.com/track/"],
    }

    def download(self, platform: str, url: str, base_filename: str) -> str:  # filename переименован в base_filename
        """Download content based on the detected platform."""
        if platform == "YouTube":
            time_limit = 6000  # 100 минут
            # Проверка длительности видео YouTube
            try:
                video_info = youthon.Video(url)
                if video_info.length_seconds > time_limit:
                    raise ValueError(
                        f"Скачивание доступно только для YouTube видео короче {time_limit / 60:.0f} минут.")
            except Exception as e:  # Обработка ошибок youthon, например, если видео недоступно
                logging.error(f"Ошибка при получении информации о YouTube видео {url}: {e}")
                raise ValueError(
                    f"Не удалось получить информацию о YouTube видео. Возможно, оно недоступно или ссылка некорректна. Ошибка: {e}")
            return self.download_video(url, f"{base_filename}.mp4")
        elif platform in ["Instagram", "TikTok", "X"]:
            return self.download_video(url, f"{base_filename}.mp4", True)
        elif platform == "Pinterest":
            return self.download_pinterest_image(url, f"{base_filename}.png")
        elif platform == "Spotify":
            # download_spotify_track теперь будет использовать base_filename и добавлять .mp3
            return self.download_spotify_track(url, base_filename)
        else:
            # Эта ветка не должна достигаться, если platform корректно определен и проверен в message_handler
            raise ValueError("Неизвестная платформа для скачивания.")

    @staticmethod
    def detect_platform(url: str) -> Literal[
        "YouTube", "Instagram", "X", "TikTok", "Spotify", "Pinterest", "unsupported"]:
        """Detects the platform from the URL using prefix matching."""
        for platform, prefixes in Downloader.PLATFORM_PREFIXES.items():
            if any(url.startswith(prefix) for prefix in prefixes):
                return platform
        return "unsupported"

    def download_video(self, url: str, output_filename: str, extra_args: bool = False) -> str:
        """Download a video from supported platforms."""
        ydl_options = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",  # Более надежный формат
            "outtmpl": output_filename,
            "quiet": True,
            "http_headers": Downloader.HEADERS,
            "noplaylist": True,  # Не скачивать плейлисты
            "retries": 3,  # Количество попыток
        }

        if extra_args:  # Для TikTok
            ydl_options["extractor_args"] = {"tiktok": {"webpage_download": True}}

        try:
            with yt_dlp.YoutubeDL(ydl_options) as ydl:
                ydl.download([url])
        except Exception as e:
            logging.error(f"yt-dlp ошибка при скачивании {url}: {e}")
            raise RuntimeError(f"Ошибка при скачивании видео: {e}")

        if not os.path.exists(output_filename) or os.path.getsize(output_filename) == 0:
            # Дополнительная проверка, что файл действительно скачался
            raise FileNotFoundError(f"Файл {output_filename} не был создан или пуст после попытки скачивания с {url}.")

        return output_filename

    def download_pinterest_image(self, url: str, output_filename: str) -> str:
        """Download an image from Pinterest."""
        try:
            response = requests.get(url, headers=Downloader.HEADERS, timeout=10)
            response.raise_for_status()
            soup = bs4.BeautifulSoup(response.content, "html.parser")

            # Ищем мета-тег og:image
            og_image_meta = soup.find("meta", property="og:image")
            if not og_image_meta or not og_image_meta.get("content"):
                # Попробуем найти основной тег img с высоким разрешением, если og:image нет
                # Это может потребовать более сложного парсинга в зависимости от структуры Pinterest
                # Для простоты, пока ограничимся og:image или специфичным селектором
                img_tag = soup.find("img",
                                    {"data-test-id": "pin-closeup-image"})  # Примерный селектор, может измениться
                if img_tag and img_tag.get("src"):
                    img_url = img_tag["src"]
                else:  # Если ничего не найдено
                    raise ValueError("Не удалось найти URL изображения на странице Pinterest.")
            else:
                img_url = og_image_meta["content"]

            self.download_file(img_url, output_filename)
            return output_filename
        except requests.RequestException as e:
            logging.error(f"Ошибка сети при скачивании с Pinterest {url}: {e}")
            raise RuntimeError(f"Ошибка сети при доступе к Pinterest: {e}")
        except Exception as e:
            logging.error(f"Ошибка при обработке Pinterest {url}: {e}")
            raise RuntimeError(f"Ошибка при обработке Pinterest: {e}")

    @staticmethod
    def download_spotify_track(url: str, output_filename_base: str) -> str:
        """Download a Spotify track and save it as output_filename_base.mp3."""
        final_filename = f"{output_filename_base}.mp3"

        # Создаем временную уникальную папку для скачивания spotdl
        # чтобы избежать конфликтов имен и легко найти скачанный файл
        temp_download_dir = f"temp_spotify_{output_filename_base}_{os.urandom(4).hex()}"
        os.makedirs(temp_download_dir, exist_ok=True)

        try:
            # Команда для spotdl: скачать трек в указанную папку
            # Используем шаблон имени файла, чтобы потом его легко найти.
            # {title} - {artists} это стандартный шаблон spotdl
            # Мы не можем напрямую указать имя файла в spotdl для версии 3.x без сложных манипуляций
            # Поэтому скачиваем во временную папку, находим mp3 и переименовываем.
            cmd = ["spotdl", "download", url, "--output", temp_download_dir]

            # Запускаем spotdl
            result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=120)  # Увеличим таймаут

            if result.returncode != 0:
                error_output = result.stderr or result.stdout or "No output from spotdl."
                logging.error(
                    f"spotdl execution failed for {url}. Return code: {result.returncode}\nOutput:\n{error_output}")
                raise RuntimeError(f"Ошибка при скачивании трека Spotify (spotdl). Пожалуйста, проверьте логи.")

            downloaded_mp3_files = [f for f in os.listdir(temp_download_dir) if f.endswith(".mp3")]

            if not downloaded_mp3_files:
                logging.error(f"Файл .mp3 не найден в {temp_download_dir} после выполнения spotdl для {url}.")
                raise FileNotFoundError("Трек Spotify был обработан, но .mp3 файл не найден.")

            original_spotify_filename = os.path.join(temp_download_dir, downloaded_mp3_files[0])

            # Перемещаем (переименовываем) скачанный файл в нужное место с нужным именем
            shutil.move(original_spotify_filename, final_filename)  # Используем shutil.move

            return final_filename

        except subprocess.TimeoutExpired:
            logging.error(f"spotdl timed out while downloading {url}")
            raise RuntimeError("Скачивание трека Spotify заняло слишком много времени.")
        except Exception as e:  # Ловим другие возможные ошибки
            logging.error(f"Общая ошибка при скачивании Spotify трека {url}: {e}")
            raise RuntimeError(f"Произошла ошибка при скачивании трека Spotify: {e}")
        finally:
            # Удаляем временную папку со всем ее содержимым
            if os.path.exists(temp_download_dir):
                try:
                    shutil.rmtree(temp_download_dir)
                except Exception as e_rmtree:
                    logging.error(f"Не удалось удалить временную папку {temp_download_dir}: {e_rmtree}")

    @staticmethod
    def download_file(url: str, output_filename: str) -> None:
        """Generic file download helper."""
        try:
            with requests.get(url, stream=True, headers=Downloader.HEADERS, timeout=20) as r:  # Добавлен таймаут
                r.raise_for_status()
                with open(output_filename, "wb") as file:
                    for chunk in r.iter_content(chunk_size=8192):  # chunk_size=1024 довольно мал
                        file.write(chunk)
            if not os.path.exists(output_filename) or os.path.getsize(output_filename) == 0:
                raise FileNotFoundError(f"Файл {output_filename} не был создан или пуст после скачивания с {url}.")
        except requests.RequestException as e:
            logging.error(f"Ошибка сети при скачивании файла {url}: {e}")
            raise RuntimeError(f"Ошибка сети при скачивании файла: {e}")
        except Exception as e:
            logging.error(f"Общая ошибка при скачивании файла {url}: {e}")
            raise RuntimeError(f"Общая ошибка при скачивании файла: {e}")