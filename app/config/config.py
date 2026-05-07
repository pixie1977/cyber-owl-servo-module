import logging
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


# Загрузка переменных окружения
load_dotenv()

# Определяем базовую директорию проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("config")

# Допустимые уровни логирования для Python и Uvicorn
LOG_LEVELS_PYTHON = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
LOG_LEVELS_UVICORN = {level.lower() for level in LOG_LEVELS_PYTHON}


class Settings:
    """
    Класс настроек приложения. Централизованная конфигурация с валидацией.
    """

    def __init__(self) -> None:
        # Обязательные переменные
        self.SERVO_HOST: str = self._get_str("SERVO_HOST")
        self.SERVO_PORT: int = self._get_int("SERVO_PORT")

        # Уровень логирования
        raw_log_level = self._get_str("SERVO_LOG_LEVEL", default="INFO")
        self.SERVO_LOG_LEVEL: str = raw_log_level.upper()
        self._validate_log_level()

        # Необязательные переменные с дефолтами
        self.SERVO_DOC_ROOT: Path = self._get_path(
            "SERVO_DOC_ROOT",
            default=BASE_DIR / "content",
        )
        self.SERVO_MODBUS_PORT: str = self._get_str(
            "SERVO_MODBUS_PORT",
            default="/dev/ttyUSB0",
        )
        self.SERVO_LOGS_DIR: Optional[Path] = self._get_path(
            "SERVO_LOGS_DIR",
            default=None,
        )

        logger.info("Конфигурация успешно загружена.")
        self._log_settings()

    def _get_str(self, key: str, default: str = None) -> str:
        """Получить строковую переменную из .env."""
        value = os.getenv(key)
        if value is not None:
            return value.strip()
        if default is not None:
            logger.debug(f"Переменная '{key}' не задана. Используется значение по умолчанию: {default}")
            return default
        raise ValueError(
            f"Обязательная переменная окружения '{key}' не задана и нет значения по умолчанию."
        )

    def _get_int(self, key: str, default: int = None) -> int:
        """Получить целочисленную переменную из .env."""
        value = os.getenv(key)
        if value is not None:
            try:
                parsed = int(value.strip())
                logger.debug(f"Загружено целое: {key}={parsed}")
                return parsed
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Переменная '{key}' должна быть целым числом. Получено: {value!r}"
                ) from e
        if default is not None:
            logger.debug(f"Переменная '{key}' не задана. Используется значение по умолчанию: {default}")
            return default
        raise ValueError(
            f"Обязательная переменная окружения '{key}' не задана и нет значения по умолчанию."
        )

    def _get_path(self, key: str, default: Path = None) -> Path:
        """Получить путь из .env или вернуть Path-объект по умолчанию."""
        value = os.getenv(key)
        if value is not None:
            path = Path(value).expanduser().resolve()
            logger.debug(f"Загружен путь из переменной {key}: {path}")
            return path
        logger.debug(f"Используется путь по умолчанию для {key}: {default}")
        return default

    def _validate_log_level(self) -> None:
        """Проверяет корректность уровня логирования для Python и Uvicorn."""
        if self.SERVO_LOG_LEVEL not in LOG_LEVELS_PYTHON:
            raise ValueError(
                f"Неверный уровень логирования: {self.SERVO_LOG_LEVEL}. "
                f"Допустимые значения: {', '.join(sorted(LOG_LEVELS_PYTHON))}"
            )
        logger.debug(f"Уровень логирования валиден: {self.SERVO_LOG_LEVEL}")

    @property
    def log_level(self) -> int:
        """Возвращает числовой уровень логирования для Python logging."""
        return getattr(logging, self.SERVO_LOG_LEVEL)

    @property
    def uvicorn_log_level(self) -> str:
        """Возвращает уровень логирования в нижнем регистре для совместимости с Uvicorn."""
        return self.SERVO_LOG_LEVEL.lower()

    def ensure_directories(self) -> None:
        """Создаёт необходимые директории, если их нет."""
        directories = []
        if self.SERVO_DOC_ROOT:
            directories.append(("Корневая директория контента", self.SERVO_DOC_ROOT))
        if self.SERVO_LOGS_DIR:
            directories.append(("Директория логов", self.SERVO_LOGS_DIR))

        for name, path in directories:
            path.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                logger.error(f"Не удалось создать директорию: {path}")
                raise RuntimeError(f"Не удалось создать директорию: {path}")
            logger.info(f"{name} создана или уже существует: {path}")

    def _log_settings(self) -> None:
        """Логирует основные настройки (без чувствительных данных)."""
        logger.info("Загруженные настройки:")
        logger.info(f"  SERVO_HOST: {self.SERVO_HOST}")
        logger.info(f"  SERVO_PORT: {self.SERVO_PORT}")
        logger.info(f"  SERVO_LOG_LEVEL: {self.SERVO_LOG_LEVEL}")
        logger.info(f"  SERVO_DOC_ROOT: {self.SERVO_DOC_ROOT}")
        logger.info(f"  SERVO_MODBUS_PORT: {self.SERVO_MODBUS_PORT}")
        logger.info(f"  SERVO_LOGS_DIR: {self.SERVO_LOGS_DIR or 'не задана'}")


# Единый экземпляр настроек
settings = Settings()