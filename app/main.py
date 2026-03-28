"""
Запуск FastAPI-сервера для SERVO-модуля.
"""

from app.core.httpd import app
from app.config.config import SERVO_HOST, SERVO_PORT, SERVO_LOG_LEVEL


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=SERVO_HOST,
        port=SERVO_PORT,
        log_level=SERVO_LOG_LEVEL,
    )