import os
import logging
import time

from aiogram import Bot, F, Router, types
from aiogram.filters import Command
from dotenv import load_dotenv

from handlers import downloader

router = Router()
load_dotenv()

# Загружаем ADMIN_ID и проверяем его наличие и тип
ADMIN_ID_STR = os.getenv("ADMIN_ID")
if not ADMIN_ID_STR:
    logging.critical("Переменная окружения ADMIN_ID не установлена!")
    raise ValueError("Переменная окружения ADMIN_ID не установлена! Пожалуйста, добавьте ADMIN_ID в ваш .env файл.")
try:
    ADMIN_ID = int(ADMIN_ID_STR)
except ValueError:
    logging.critical("ADMIN_ID должен быть целым числом (ID пользователя Telegram)!")
    raise ValueError("ADMIN_ID должен быть целым числом (ID пользователя Telegram)!")


@router.message(F.text, Command("start"))
async def start(message: types.Message) -> None:
    await message.answer(
        text="Отправь боту ссылку на видео.\nПоддерживаемые ссылки - /supported_links\n\n<b>Мы не собираем никаких данных о Вас!</b>")


@router.message(F.text, Command("supported_links"))
async def usage(message: types.Message) -> None:
    await message.answer(
        """
<b>YouTube shorts</b>
https://www.youtube.com/watch?v=
https://youtu.be/
https://www.youtube.com/shorts/
https://youtube.com/shorts/

<b>Instagram</b>
https://www.instagram.com/reel/
https://instagram.com/reel/

<b>TikTok</b>
https://www.tiktok.com/
https://vt.tiktok.com/

<b>X (Twitter)</b>
https://x.com/
https://twitter.com/

<b>Spotify</b>
https://open.spotify.com/track/

<b>Pinterest</b>
https://www.pinterest.com/pin/
https://in.pinterest.com/pin/
https://pin.it/
"""
    )


@router.message(F.text)
async def message_handler(message: types.Message, bot: Bot) -> None:  # Добавляем bot: Bot для доступа к экземпляру бота
    msg_text_template = """
<b>Platform: {}</b>

Downloading {}
Sending {}
    """
    user_status_msg = await message.answer(msg_text_template.format("🟨", "❌", "❌"))

    downloaded_filename = None
    admin_report_message = ""
    platform_name = "не определена"  # Инициализация платформы

    try:
        dl = downloader.Downloader()
        platform_name = dl.detect_platform(message.text)

        if platform_name == "unsupported":
            raise ValueError("Ссылка не поддерживается. Поддерживаемые ссылки - /supported_links")

        await user_status_msg.edit_text(msg_text_template.format(platform_name, "🟨", "❌"))

        # Используем message.from_user.id для уникальности имени файла
        base_filename_for_dl = str(f"{time.time()}-{message.from_user.id}")
        downloaded_filename = dl.download(platform_name, message.text, base_filename_for_dl)

        file_ext = os.path.splitext(downloaded_filename)[1].lower()
        file_type_map = {
            ".mp4": "video",
            ".png": "photo",
            ".mp3": "audio"
        }
        file_type = file_type_map.get(file_ext)

        if not file_type:
            # Это может произойти, если downloader.py вернет файл с неизвестным расширением
            logging.error(
                f"Не удалось определить тип файла для '{downloaded_filename}' (расширение '{file_ext}' неизвестно).")
            raise ValueError(
                f"Не удалось определить тип файла для скачанного контента (расширение '{file_ext}' неизвестно).")

        await user_status_msg.edit_text(msg_text_template.format(platform_name, "✅", "🟨"))

        # Отправка файла пользователю
        await getattr(
            message,
            f"answer_{file_type}")(
            types.FSInputFile(downloaded_filename),
            # caption="<b>@free_yt_dl_bot</b>" # Раскомментируйте, если нужен caption
        )

        time.sleep(0.5)  # Небольшая задержка, как и было
        await user_status_msg.edit_text(msg_text_template.format(platform_name, "✅", "✅"))

        # Формируем сообщение для админа об успехе
        admin_report_message = (
            f"✅ <b>Успех!</b>\n"
            f"Пользователь: {message.from_user.full_name} (@{message.from_user.username or 'N/A'}, ID: {message.from_user.id})\n"
            f"Платформа: {platform_name}\n"
            f"Ссылка: {message.text}\n"
            f"Файл: {os.path.basename(downloaded_filename)}\n"
            f"Результат: Успешно отправлено пользователю."
        )

        # Удаляем исходное сообщение пользователя и статусное сообщение бота ПОСЛЕ успешной отправки
        await message.delete()
        await user_status_msg.delete()

    except Exception as e:
        error_message = str(e)
        logging.error(f"Ошибка при обработке ссылки {message.text} от пользователя {message.from_user.id}: {e}",
                      exc_info=True)
        try:
            await user_status_msg.edit_text(f"⚠️ Произошла ошибка: {error_message}")
        except Exception as e_edit:  # Если статусное сообщение уже удалено или другая ошибка
            logging.warning(f"Не удалось отредактировать статусное сообщение об ошибке: {e_edit}")
            # Отправляем новое сообщение пользователю об ошибке
            await message.answer(f"⚠️ Произошла ошибка: {error_message}")

        # Формируем сообщение для админа об ошибке
        admin_report_message = (
            f"❌ <b>Ошибка!</b>\n"
            f"Пользователь: {message.from_user.full_name} (@{message.from_user.username or 'N/A'}, ID: {message.from_user.id})\n"
            f"Платформа: {platform_name}\n"  # platform_name будет "не определена" или реальное значение
            f"Ссылка: {message.text}\n"
            f"Ошибка: {error_message}"
        )
    finally:
        # Отправка отчета админу (если сообщение сформировано и пользователь не является админом)
        if admin_report_message and message.from_user.id != ADMIN_ID:
            try:
                await bot.send_message(ADMIN_ID, admin_report_message, parse_mode="HTML", disable_web_page_preview=True)
            except Exception as e_admin_send:
                logging.error(f"Не удалось отправить сообщение администратору (ID: {ADMIN_ID}): {e_admin_send}")

        # Удаление временного файла
        if downloaded_filename and os.path.exists(downloaded_filename):
            try:
                os.remove(downloaded_filename)
            except Exception as e_remove:
                logging.error(f"Ошибка удаления файла {downloaded_filename}: {e_remove}")
                # Дополнительно уведомить админа о проблеме с удалением файла, если это не он сам
                if message.from_user.id != ADMIN_ID:
                    try:
                        await bot.send_message(
                            ADMIN_ID,
                            f"‼️ <b>КРИТИЧЕСКАЯ ОШИБКА ФАЙЛОВОЙ СИСТЕМЫ:</b>\n"
                            f"Не удалось удалить временный файл: <code>{os.path.basename(downloaded_filename)}</code>\n"
                            f"Ошибка: <code>{e_remove}</code>\n"
                            f"Запрос от пользователя: @{message.from_user.username or 'N/A'} (ID: {message.from_user.id})",
                            parse_mode="HTML"
                        )
                    except Exception as e_admin_file_remove_notify:
                        logging.error(
                            f"Не удалось отправить админу сообщение об ошибке удаления файла: {e_admin_file_remove_notify}")