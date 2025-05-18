import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from handlers import router # Убедитесь, что этот импорт корректен и указывает на ваш основной роутер

# Настраиваем базовое логирование как можно раньше
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def run_bot():
    logger.info("Загрузка переменных окружения...")
    load_dotenv() # Загружаем переменные из .env файла

    TOKEN = os.getenv("TOKEN")
    ADMIN_ID_STR = os.getenv("ADMIN_ID")

    if not TOKEN:
        logger.critical("Переменная окружения TOKEN не установлена! Бот не может быть запущен.")
        return

    logger.info("Инициализация бота и диспетчера...")
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router) # Подключаем роутеры из handlers

    # Отправка приветственного сообщения администратору
    if ADMIN_ID_STR:
        logger.info(f"Обнаружен ADMIN_ID_STR: '{ADMIN_ID_STR}'. Попытка отправить приветственное сообщение.")
        try:
            ADMIN_ID = int(ADMIN_ID_STR)
            await bot.send_message(ADMIN_ID, "✅ Бот успешно запущен и готов к работе!")
            logger.info(f"Приветственное сообщение успешно отправлено администратору {ADMIN_ID}")
        except ValueError:
            logger.error(
                f"ADMIN_ID '{ADMIN_ID_STR}' в переменных окружения указан некорректно (не является целым числом). "
                "Приветственное сообщение администратору не отправлено."
            )
        except Exception as e:
            logger.error(f"Не удалось отправить приветственное сообщение администратору {ADMIN_ID_STR}: {e}", exc_info=True)
    else:
        logger.warning(
            "Переменная окружения ADMIN_ID не установлена. "
            "Приветственное сообщение администратору не будет отправлено."
        )

    logger.info("Запуск поллинга бота...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критическая ошибка во время поллинга: {e}", exc_info=True)
    finally:
        logger.info("Остановка бота. Закрытие сессии...")
        await bot.session.close()
        logger.info("Сессия бота успешно закрыта.")


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную (Ctrl+C).")
    except Exception as e:
        logger.critical(f"Непредвиденная ошибка на верхнем уровне приложения: {e}", exc_info=True)