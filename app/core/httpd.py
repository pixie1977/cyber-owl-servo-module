#!/usr/bin/env python3
"""
HTTP-сервер на FastAPI для сервомодуля с поддержкой POST, GET.
"""

import os
from contextlib import asynccontextmanager

from aiohttp.web_fileresponse import FileResponse
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Импортируем роутеры
from app.core.routers.servo_router import router as servo_router
from app.core.routers.health_router import router as health_router

from app.config.config import settings
from app.core.logger import get_logger
from app.core.low_level_controllers.servo_controller_manager import (
    init_servo_controller,
    get_servo_controller,
)


log = get_logger(__name__)


# Управление жизненным циклом приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Функция управления жизненным циклом приложения.
    Выполняется при старте и завершении сервера.
    """
    log.info("Starting up SERVO server...")
    init_servo_controller(port=settings.SERVO_MODBUS_PORT)
    yield
    log.info("Shutting down SERVO server...")
    ctrl = get_servo_controller()
    if ctrl is not None:
        ctrl.stop()
        import time

        time.sleep(0.2)


app = FastAPI(title="SERVO API Server", lifespan=lifespan)

# Подключаем статические файлы
print(f"SERVO_DOC_ROOT={settings.SERVO_DOC_ROOT}")
app.mount("/static", StaticFiles(directory=settings.SERVO_DOC_ROOT), name="static")

# Подключаем роутеры
app.include_router(servo_router)
app.include_router(health_router)


# Модель для JSON-запроса
class TTSTextRequest(BaseModel):
    """
    Модель для валидации входных данных.
    Ожидает поле 'text' типа str.
    """

    text: str


@app.get("/")
async def read_root():
    """
    Корневой маршрут: отдаёт index.html или JSON-приветствие.
    """
    index_path = os.path.join(settings.SERVO_DOC_ROOT, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Cyber Owl TTS API"}