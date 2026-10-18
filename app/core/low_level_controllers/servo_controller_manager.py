from typing import Optional, Union

from app.config.config import settings
from app.core.logger import get_logger
from app.core.low_level_controllers.servo_controller import ModbusServoControllerThread
from app.core.low_level_controllers.i2c_servo_controller import I2CServoControllerThread

logger = get_logger(__name__)

# Глобальный экземпляр контроллера сервоприводов
servo_controller: Optional[Union[ModbusServoControllerThread, I2CServoControllerThread]] = None


def init_servo_controller(port: str = None) -> Union[ModbusServoControllerThread, I2CServoControllerThread]:
    """
    Инициализирует и запускает контроллер сервоприводов.
    Выбор типа контроллера зависит от префикса порта:
      - 'I2C' -> I2CServoControllerThread (PCA9685)
      - иначе -> ModbusServoControllerThread (serial)

    Формат I2C-порта: I2C:<bus>:<address>
      I2C:7:0x40  — шина 7, PCA9685 по адресу 0x40
      I2C:5:0x41  — шина 5, PCA9685 по адресу 0x41
      I2C         — шина 7, адрес 0x40 (по умолчанию)

    :param port: Порт (по умолчанию берётся из настроек)
    :return: Экземпляр ServoController
    """
    global servo_controller

    if servo_controller is not None:
        logger.warning("ServoController already initialized. Reusing existing instance.")
        return servo_controller

    # Используем порт по умолчанию из настроек, если не передан
    port = port or settings.SERVO_SERIAL_PORT

    # Определение типа контроллера по префиксу порта
    if port.upper().startswith("I2C"):
        servo_controller = I2CServoControllerThread(
            port=port,
            reconnect_attempts=5,
            initial_retry_delay=1.0,
            on_connection_lost=lambda: logger.warning("Servo: Connection lost"),
            on_connection_restored=lambda: logger.info("Servo: Connection restored")
        )
        logger.info(f"I2CServoController initialized and started on port {port}")
    else:
        servo_controller = ModbusServoControllerThread(
            port=port,
            reconnect_attempts=5,
            initial_retry_delay=1.0,
            on_connection_lost=lambda: logger.warning("Servo: Connection lost"),
            on_connection_restored=lambda: logger.info("Servo: Connection restored")
        )
        logger.info(f"ModbusServoController initialized and started on port {port}")

    servo_controller.start()
    return servo_controller


def get_servo_controller() -> Union[ModbusServoControllerThread, I2CServoControllerThread]:
    """
    Возвращает инициализированный экземпляр контроллера.

    :raises RuntimeError: Если контроллер не был инициализирован
    :return: Экземпляр ServoController
    """
    if servo_controller is None:
        raise RuntimeError("ServoController not initialized. Call init_servo_controller first.")
    return servo_controller
