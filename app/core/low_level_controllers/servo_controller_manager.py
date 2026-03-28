from typing import Optional

from app.config.config import settings
from app.core.logger import get_logger
from app.core.low_level_controllers.servo_controller import ServoControllerThread

logger = get_logger(__name__)

# Глобальный экземпляр контроллера сервоприводов
servo_controller: Optional[ServoControllerThread] = None


def init_servo_controller(port: str = None) -> ServoControllerThread:
    """
    Инициализирует и запускает контроллер сервоприводов.

    :param port: Порт Modbus (по умолчанию берётся из настроек)
    :return: Экземпляр ServoControllerThread
    """
    global servo_controller

    if servo_controller is not None:
        logger.warning("ServoController already initialized. Reusing existing instance.")
        return servo_controller

    # Используем порт по умолчанию из настроек, если не передан
    port = port or settings.SERVO_MODBUS_PORT

    servo_controller = ServoControllerThread(
        port=port,
        reconnect_attempts=5,
        initial_retry_delay=1.0,
        on_connection_lost=lambda: logger.warning("Servo: Connection lost"),
        on_connection_restored=lambda: logger.info("Servo: Connection restored")
    )
    servo_controller.start()
    logger.info(f"ServoController initialized and started on port {port}")
    return servo_controller


def get_servo_controller() -> ServoControllerThread:
    """
    Возвращает инициализированный экземпляр контроллера.

    :raises RuntimeError: Если контроллер не был инициализирован
    :return: Экземпляр ServoControllerThread
    """
    if servo_controller is None:
        raise RuntimeError("ServoController not initialized. Call init_servo_controller first.")
    return servo_controller