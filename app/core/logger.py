"""
Модуль настройки логгера приложения.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from app.config.config import settings


# Создание директории для логов
os.makedirs(settings.SERVO_LOGS_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(settings.SERVO_LOGS_DIR, "stt.log")


# Форматтер логов
formatter = logging.Formatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# Обработчик записи в файл с ротацией
file_handler = RotatingFileHandler(
    LOG_FILE_PATH,
    maxBytes=10 * 1024 * 1024,  # 10 МБ
    backupCount=5,
)
file_handler.setFormatter(formatter)


# Обработчик вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)


# Настройка корневого логгера
logger = logging.getLogger("MBB_logger")
logger.setLevel(settings.SERVO_LOG_LEVEL)
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.propagate = False  # Отключение передачи логов выше по иерархии


def get_logger(name: str) -> logging.Logger:
    """
    Возвращает дочерний логгер с указанным именем.

    :param name: имя модуля или компонента
    :return: экземпляр логгера
    """
    return logger.getChild(name)