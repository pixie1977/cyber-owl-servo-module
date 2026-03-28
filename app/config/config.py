import os
from pathlib import Path
from typing import Optional
import logging
from dotenv import load_dotenv


# Загрузка переменных окружения
load_dotenv()

# Определяем базовую директорию проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# Логгер для конфигурации
logger = logging.getLogger(__name__)


class Settings:
    """
    Класс настроек приложения с валидацией и дефолтными значениями.
    """

    def __init__(self):
        # Обязательные переменные
        self.SERVO_PORT: int = self._get_int("SERVO_PORT")
        self.SERVO_HOST: str = self._get_str("SERVO_HOST")
        self.SERVO_LOG_LEVEL: str = self._get_str("SERVO_LOG_LEVEL")

        # Необязательные переменные с дефолтами
        self.SERVO_DOC_ROOT: Path = self._get_path(
            "SERVO_DOC_ROOT",
            default=BASE_DIR / "content"
        )
        self.SERVO_MODBUS_PORT: str = self._get_str(
            "SERVO_MODBUS_PORT",
            default="/dev/ttyUSB0"
        )
        self.SERVO_LOGS_DIR: Optional[Path] = self._get_path(
            "SERVO_LOGS_DIR",
            default=None
        )

        # Валидация уровня логирования
        self._validate_log_level()

    def _get_str(self, key: str, default: str = None) -> str:
        """Получить строковую переменную из .env"""
        value = os.getenv(key, default)
        if value is None:
            raise ValueError(f"Переменная окружения '{key}' не задана и нет значения по умолчанию")
        return value.strip()

    def _get_int(self, key: str, default: int = None) -> int:
        """Получить целочисленную переменную из .env"""
        value = os.getenv(key)
        if value is None:
            if default is not None:
                return default
            raise ValueError(f"Переменная окружения '{key}' обязательна и не задана")
        try:
            return int(value.strip())
        except (ValueError, TypeError):
            raise ValueError(f"Переменная '{key}' должна быть целым числом, получено: {value}")

    def _get_path(self, key: str, default: Path = None) -> Optional[Path]:
        """Получить путь из .env или вернуть Path-объект по умолчанию"""
        value = os.getenv(key)
        if value is None:
            return default
        return Path(value).expanduser().resolve()

    def _validate_log_level(self):
        """Проверяет корректность уровня логирования"""
        valid_levels = {
            "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
        }
        if self.SERVO_LOG_LEVEL.upper() not in valid_levels:
            raise ValueError(
                f"Неверный уровень логирования: {self.SERVO_LOG_LEVEL}. "
                f"Допустимые значения: {', '.join(valid_levels)}"
            )

    @property
    def log_level(self) -> int:
        """Возвращает числовой уровень логирования"""
        return getattr(logging, self.SERVO_LOG_LEVEL.upper())

    def ensure_directories(self):
        """Создаёт необходимые директории, если их нет"""
        if self.SERVO_DOC_ROOT and not self.SERVO_DOC_ROOT.exists():
            self.SERVO_DOC_ROOT.mkdir(parents=True, exist_ok=True)
            logger.info(f"Создана директория: {self.SERVO_DOC_ROOT}")

        if self.SERVO_LOGS_DIR:
            self.SERVO_LOGS_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"Создана директория логов: {self.SERVO_LOGS_DIR}")


# Единый экземпляр настроек
settings = Settings()