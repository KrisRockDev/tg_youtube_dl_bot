import os
import logging
import time

from aiogram import Bot, F, Router, types
from aiogram.filters import Command
from dotenv import load_dotenv # load_dotenv здесь может быть избыточен, если main.py его уже вызвал,
                               # но не повредит (переменные не перезапишутся, если уже установлены)

from handlers import downloader

router = Router()
# Загружаем переменные окружения. Лучше делать это один раз при старте приложения,
# но для модульности оставим здесь, load_dotenv безопасен при повторном вызове.
load_dotenv()

# Настройка логгера для этого модуля
logger = logging.getLogger(__name__)

# Загружаем ADMIN_ID и проверяем его наличие и тип
ADMIN_ID_STR = os.getenv("ADMIN_ID")
ADMIN_ID = None  # Инициализируем как None

if not ADMIN_ID_STR:
    logger.warning("Переменная окружения ADMIN_ID не установлена! Функции администрирования будут ограничены.")
else:
    try:
        ADMIN_ID = int(ADMIN_ID_STR)
        logger.info(f"ADMIN_ID успешно загружен и установлен: {ADMIN_ID}")
    except ValueError:
        logger.critical(
            f"ADMIN_ID ('{ADMIN_ID_STR}') должен быть целым числом (ID пользователя Telegram)! Функции администрирования будут ограничены.")
        ADMIN_ID = None  # Оставляем None, если значение некорректно


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
async def message_handler(message: types.Message, bot: Bot) -> None:
    msg_text_template = """
<b>Platform: {}</b>

Downloading {}
Sending {}
    """
    user_status_msg = await message.answer(msg_text_template.format("🟨", "❌", "❌"))

    downloaded_filename = None
    file_type = None
    platform_name = "не определена"

    try:
        dl = downloader.Downloader()
        platform_name = dl.detect_platform(message.text)

        if platform_name == "unsupported":
            raise ValueError("Ссылка не поддерживается. Поддерживаемые ссылки - /supported_links")

        await user_status_msg.edit_text(msg_text_template.format(platform_name, "🟨", "❌"))

        base_filename_for_dl = str(f"{time.time()}-{message.from_user.id}")
        downloaded_filename = dl.download(platform_name, message.text, base_filename_for_dl)
        logger.info(f"Файл скачан: {downloaded_filename} для пользователя {message.from_user.id}")

        file_ext = os.path.splitext(downloaded_filename)[1].lower()
        file_type_map = {
            ".mp4": "video",
            ".png": "photo",
            ".mp3": "audio"
        }
        file_type = file_type_map.get(file_ext)

        if not file_type:
            logger.error(
                f"Не удалось определить тип файла для '{downloaded_filename}' (расширение '{file_ext}' неизвестно).")
            raise ValueError(
                f"Не удалось определить тип файла для скачанного контента (расширение '{file_ext}' неизвестно).")
        logger.info(f"Тип файла определен как: {file_type}")

        await user_status_msg.edit_text(msg_text_template.format(platform_name, "✅", "🟨"))

        # Отправка файла пользователю
        logger.info(f"Отправка файла {downloaded_filename} пользователю {message.from_user.id}")
        await getattr(
            message,
            f"answer_{file_type}")(
            types.FSInputFile(downloaded_filename),
        )
        logger.info(f"Файл {downloaded_filename} успешно отправлен пользователю {message.from_user.id}")

        time.sleep(0.5) # Небольшая пауза для обновления статуса, если необходимо
        await user_status_msg.edit_text(msg_text_template.format(platform_name, "✅", "✅"))

        # Отправка отчетов и копии файла администратору
        if ADMIN_ID and message.from_user.id != ADMIN_ID:
            logger.info(f"Пользователь {message.from_user.id} не является админом ({ADMIN_ID}). Подготовка отчета для админа.")
            # 1. Отправляем текстовый отчет об успехе админу
            admin_text_report_success = (
                f"✅ <b>Успех! Файл отправлен пользователю.</b>\n"
                f"Пользователь: {message.from_user.full_name} (@{message.from_user.username or 'N/A'}, ID: {message.from_user.id})\n"
                f"Платформа: {platform_name}\n"
                f"Ссылка (первые 200 симв.): {message.text[:200]}{'...' if len(message.text) > 200 else ''}\n"
                f"Имя файла: {os.path.basename(downloaded_filename)}"
            )
            try:
                await bot.send_message(ADMIN_ID, admin_text_report_success, parse_mode="HTML",
                                       disable_web_page_preview=True)
                logger.info(f"Текстовый отчет об успехе отправлен админу {ADMIN_ID}")
            except Exception as e_admin_text_send:
                logger.error(f"Не удалось отправить текстовый отчет админу {ADMIN_ID}: {e_admin_text_send}", exc_info=True)

            # 2. Пытаемся отправить файл админу (если он есть и тип определен)
            if downloaded_filename and file_type:
                logger.info(f"Попытка отправить копию файла '{downloaded_filename}' (тип: {file_type}) админу {ADMIN_ID}")
                admin_file_caption = (
                    f"Копия файла для пользователя: {message.from_user.full_name} (@{message.from_user.username or 'N/A'})\n"
                    f"ID: {message.from_user.id}\n"
                    f"Оригинальная ссылка (первые 100 симв.): {message.text[:100]}{'...' if len(message.text) > 100 else ''}"
                )
                try:
                    await getattr(bot, f"send_{file_type}")(
                        ADMIN_ID,
                        types.FSInputFile(downloaded_filename),
                        caption=admin_file_caption,
                        parse_mode="HTML"
                    )
                    logger.info(f"Копия файла {downloaded_filename} успешно отправлена админу {ADMIN_ID}.")
                except Exception as e_admin_send_file:
                    logger.error(f"Не удалось отправить копию файла '{downloaded_filename}' админу {ADMIN_ID}: {e_admin_send_file}", exc_info=True)
                    try:
                        await bot.send_message(
                            ADMIN_ID,
                            f"⚠️ Файл для пользователя {message.from_user.full_name} (ID: {message.from_user.id}) "
                            f"был успешно обработан и отправлен ему.\n"
                            f"Однако, мне не удалось отправить копию файла вам (администратору).\n"
                            f"Причина: {e_admin_send_file}",
                            parse_mode="HTML",
                            disable_web_page_preview=True
                        )
                    except Exception as e_notify_fail_send_file:
                        logger.error(
                            f"Не удалось уведомить админа об ошибке отправки ему файла: {e_notify_fail_send_file}", exc_info=True)
            else:
                logger.warning(f"Копия файла не будет отправлена админу. "
                               f"downloaded_filename: '{downloaded_filename}', file_type: '{file_type}'")
        elif ADMIN_ID and message.from_user.id == ADMIN_ID:
             logger.info(f"Пользователь {message.from_user.id} является админом. Копия файла и отчет не дублируются.")
        elif not ADMIN_ID:
            logger.info("ADMIN_ID не установлен, отчеты и копия файла админу не отправляются.")


        # Удаляем исходное сообщение пользователя и статусное сообщение бота ПОСЛЕ успешной отправки и отчетов
        try:
            await message.delete()
            logger.info(f"Сообщение пользователя {message.from_user.id} (ID: {message.message_id}) удалено.")
        except Exception as e_del_msg:
            logger.warning(f"Не удалось удалить сообщение пользователя {message.from_user.id}: {e_del_msg}", exc_info=True)

        try:
            await user_status_msg.delete()
            logger.info(f"Статусное сообщение бота (ID: {user_status_msg.message_id}) удалено.")
        except Exception as e_del_status:
            logger.warning(f"Не удалось удалить статусное сообщение бота: {e_del_status}", exc_info=True)


    except Exception as e:
        error_message = str(e)
        logger.error(f"Ошибка при обработке ссылки {message.text} от пользователя {message.from_user.id}: {e}",
                      exc_info=True)
        try:
            await user_status_msg.edit_text(f"⚠️ Произошла ошибка: {error_message}")
        except Exception as e_edit:
            logger.warning(f"Не удалось отредактировать статусное сообщение об ошибке: {e_edit}", exc_info=True)
            try:
                await message.answer(f"⚠️ Произошла ошибка: {error_message}")
            except Exception as e_answer_err:
                 logger.error(f"Не удалось отправить пользователю сообщение об ошибке: {e_answer_err}", exc_info=True)


        # Отправляем отчет об ошибке админу, если это не сам админ и ADMIN_ID установлен
        if ADMIN_ID and message.from_user.id != ADMIN_ID:
            admin_text_report_error = (
                f"❌ <b>Ошибка при обработке запроса!</b>\n"
                f"Пользователь: {message.from_user.full_name} (@{message.from_user.username or 'N/A'}, ID: {message.from_user.id})\n"
                f"Платформа: {platform_name}\n"
                f"Ссылка (первые 200 симв.): {message.text[:200]}{'...' if len(message.text) > 200 else ''}\n"
                f"Ошибка: {error_message}"
            )
            try:
                await bot.send_message(ADMIN_ID, admin_text_report_error, parse_mode="HTML",
                                       disable_web_page_preview=True)
                logger.info(f"Отчет об ошибке отправлен администратору {ADMIN_ID}")
            except Exception as e_admin_err_send:
                logger.error(
                    f"Не удалось отправить отчет об ошибке администратору (ID: {ADMIN_ID}): {e_admin_err_send}", exc_info=True)

    finally:
        # Удаление временного файла
        if downloaded_filename and os.path.exists(downloaded_filename):
            try:
                os.remove(downloaded_filename)
                logger.info(f"Временный файл {downloaded_filename} удален.")
            except Exception as e_remove:
                logger.error(f"Ошибка удаления файла {downloaded_filename}: {e_remove}", exc_info=True)
                # Дополнительно уведомить админа о проблеме с удалением файла
                if ADMIN_ID and message.from_user.id != ADMIN_ID: # Проверяем, что пользователь не админ
                    try:
                        await bot.send_message(
                            ADMIN_ID,
                            f"‼️ <b>КРИТИЧЕСКАЯ ОШИБКА ФАЙЛОВОЙ СИСТЕМЫ (common.py):</b>\n"
                            f"Не удалось удалить временный файл: <code>{os.path.basename(downloaded_filename)}</code>\n"
                            f"Полный путь: <code>{downloaded_filename}</code>\n"
                            f"Ошибка: <code>{e_remove}</code>\n"
                            f"Запрос от пользователя: @{message.from_user.username or 'N/A'} (ID: {message.from_user.id})",
                            parse_mode="HTML"
                        )
                    except Exception as e_admin_file_remove_notify:
                        logger.error(
                            f"Не удалось отправить админу сообщение об ошибке удаления файла: {e_admin_file_remove_notify}", exc_info=True)
        elif downloaded_filename: # Файл должен был быть, но его нет
             logger.warning(f"Временный файл {downloaded_filename} не найден для удаления в блоке finally.")