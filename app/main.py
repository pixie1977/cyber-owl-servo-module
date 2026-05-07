"""
Точка входа для запуска Uvicorn сервера.
Использует строку-импорт для поддержки hot-reload.
"""

from app.config.config import settings


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.core.httpd:app",
        host=settings.SERVO_HOST,
        port=settings.SERVO_PORT,
        log_level=settings.uvicorn_log_level,
        reload=True,
    )