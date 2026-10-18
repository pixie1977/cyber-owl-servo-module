#!/usr/bin/env python3
"""
Контроллер сервоприводов через I2C (PCA9685) с многопоточной обработкой команд.

Формат порта: I2C:<bus>:<address>
  I2C:7:0x40  — шина 7, PCA9685 по адресу 0x40
  I2C:5:0x41  — шина 5, PCA9685 по адресу 0x41

Дефолты: bus=7, address=0x40
"""

import re
import queue
from threading import Thread, Event
from time import sleep
from typing import Optional, Dict, Any, Callable, Tuple

from app.core.logger import get_logger

# Сервоприводы: ID (совместимо с Modbus-архитектурой)
HV = 0  # Head Vertical
HH = 1  # Head Horizontal
LW = 2  # Left Wing
RW = 4  # Right Wing

# Каналы PCA9685 для каждого сервопривода
_SERVO_CHANNEL_MAP = {
    HV: 3,  # голова вертикально
    HH: 2,  # голова горизонтально
    LW: 0,  # левое крыло
    RW: 1,  # правое крыло
}

# Дефолтные значения по умолчанию
_DEFAULT_I2C_BUS = 7
_DEFAULT_I2C_ADDRESS = 0x40


def parse_i2c_port(port: str) -> Tuple[int, int]:
    """
    Парсит порт в формате I2C:<bus>:<address>.

    :param port: Строка вида "I2C:7:0x40"
    :return: Кортеж (bus_number, i2c_address)
    """
    if not port or not port.upper().startswith("I2C"):
        return _DEFAULT_I2C_BUS, _DEFAULT_I2C_ADDRESS

    pattern = r"^I2C(?::(\d+))?(?::(0x[0-9a-fA-F]+))?$"
    match = re.match(pattern, port, re.IGNORECASE)

    if not match:
        return _DEFAULT_I2C_BUS, _DEFAULT_I2C_ADDRESS

    bus = int(match.group(1)) if match.group(1) else _DEFAULT_I2C_BUS
    address = int(match.group(2), 16) if match.group(2) else _DEFAULT_I2C_ADDRESS

    return bus, address


class I2CServoControllerThread(Thread):
    """Контроллер сервоприводов через I2C (PCA9685) в отдельном потоке."""

    log = get_logger(__name__)

    def __init__(
        self,
        port: str = None,
        reconnect_attempts: int = 3,
        initial_retry_delay: float = 1.0,
        on_connection_lost: Optional[Callable[[], None]] = None,
        on_connection_restored: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self.daemon = True
        self._command_queue = queue.Queue()
        self._port = port
        self._stop_event = Event()
        self.is_running_process = True

        # Параметры I2C (bus, address)
        self._i2c_bus, self._i2c_address = parse_i2c_port(port) if port else (_DEFAULT_I2C_BUS, _DEFAULT_I2C_ADDRESS)

        # Параметры переподключения
        self._reconnect_attempts = reconnect_attempts
        self._initial_retry_delay = initial_retry_delay

        # Callback-функции
        self._on_connection_lost = on_connection_lost
        self._on_connection_restored = on_connection_restored

        # Статистика подключений
        self._connection_stats: Dict[str, Any] = {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "current_status": "disconnected",
        }

        # PCA9685 и сервоприводы (инициализируются в run())
        self._pca = None
        self._servos: Dict[int, Any] = {}

        if self._port is not None:
            self._connect_with_retry()

    def __enter__(self) -> "I2CServoControllerThread":
        """Поддержка контекстного менеджера."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Завершение работы при выходе из контекста."""
        self.stop()

    def _connect_with_retry(self) -> bool:
        """Подключение к I2C-устройству с экспоненциальной задержкой."""
        try:
            import board
            import busio
            from adafruit_pca9685 import PCA9685
            from adafruit_motor import servo
        except ImportError as e:
            self.log.error(f"Необходимые библиотеки не установлены: {e}")
            self.log.error("Установите: pip install adafruit-circuitpython-pca9685 adafruit-circuitpython-motor")
            return False

        for attempt in range(1, self._reconnect_attempts + 1):
            self._connection_stats["attempts"] += 1
            delay = self._initial_retry_delay * (2 ** (attempt - 1))

            try:
                self.log.info(
                    f"Connecting to I2C PCA9685 on bus {self._i2c_bus} "
                    f"(address=0x{self._i2c_address:02x}) "
                    f"(attempt {attempt}/{self._reconnect_attempts})"
                )

                # Инициализация I2C шины через Blinka (board.SCL/SDA привязаны к нужной шине)
                i2c = busio.I2C(board.SCL, board.SDA)

                # Инициализация PCA9685
                self._pca = PCA9685(i2c, address=self._i2c_address)
                self._pca.frequency = 50  # 50 Гц для аналоговых серв

                # Создание сервоприводов на соответствующих каналах PCA9685
                for servo_id, channel in _SERVO_CHANNEL_MAP.items():
                    self._servos[servo_id] = servo.Servo(
                        self._pca.channels[channel],
                        min_pulse=500,
                        max_pulse=2400,
                    )

                self.log.info(
                    f"Successfully connected to I2C PCA9685 on bus {self._i2c_bus} "
                    f"(address=0x{self._i2c_address:02x})"
                )
                self._connection_stats["successes"] += 1
                self._connection_stats["current_status"] = "connected"

                if self._on_connection_restored:
                    try:
                        self._on_connection_restored()
                    except Exception as e:
                        self.log.error(f"Error in on_connection_restored callback: {e}")

                return True

            except Exception as e:
                self.log.error(f"Connection attempt {attempt} failed with exception: {e}")
                self._connection_stats["failures"] += 1

                if attempt < self._reconnect_attempts:
                    self.log.info(f"Retrying in {delay:.1f} seconds...")
                    sleep(delay)
                else:
                    self.log.critical(f"Failed to connect after {self._reconnect_attempts} attempts")
                    self._pca = None
                    self._servos.clear()

        return False

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику подключений (для мониторинга).

        :return: словарь с метриками
        """
        return self._connection_stats.copy()

    def reset_connection_stats(self) -> None:
        """Сброс статистики подключений."""
        current_status = "connected" if self._pca is not None else "disconnected"
        self._connection_stats = {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "current_status": current_status,
        }

    def run(self) -> None:
        """Основной цикл потока."""
        try:
            if self._pca is not None:
                self.process()
            else:
                self.log.warning("I2C controller not initialized, thread exiting.")
        finally:
            self.log.info("I2C servo controller thread stopped.")

    def process(self) -> None:
        """Цикл обработки команд из очереди."""
        while self.is_running_process and not self._stop_event.is_set():
            try:
                command: Dict[str, Any] = self._command_queue.get(timeout=0.01)
            except queue.Empty:
                continue

            self._execute_command(command)
            self._command_queue.task_done()

    def _execute_command(self, command: Dict[str, Any]) -> None:
        """Выполнение одной команды."""
        command_id = command.get("id")
        value_str = command.get("value")

        if command_id is None or value_str is None:
            self.log.debug("Invalid command: missing 'id' or 'value'")
            return

        str_command_id = str(command_id).lower()

        try:
            val = int(value_str)
        except (ValueError, TypeError):
            self.log.error(f"Invalid value for command {command_id}: {value_str}")
            return

        # Обработка команд
        if str_command_id == "rw" or command_id == RW:
            self.set_right_wing(val)
        elif str_command_id == "lw" or command_id == LW:
            self.set_left_wing(val)
        elif str_command_id == "hh" or command_id == HH:
            self.set_head_horizontal(val)
        elif str_command_id == "hv" or command_id == HV:
            self.set_head_vertical(val)
        elif str_command_id == "wait":
            delay_ms = float(val)
            if delay_ms < 0:
                delay_ms = 0
            sleep(delay_ms / 1000.0)
        else:
            self.log.warning(f"Unknown command ID: {command_id}")

    def _ensure_connection(self) -> bool:
        """
        Проверяет соединение и пытается восстановить его.

        :return: True, если соединение активно или восстановлено
        """
        if self._pca is not None:
            return True

        self.log.warning("I2C connection lost. Attempting to reconnect...")
        self.on_quit()
        return self._connect_with_retry()

    def on_quit(self) -> None:
        """Очистка ресурсов."""
        # Деактивируем сервоприводы
        for servo_obj in self._servos.values():
            try:
                servo_obj.deinit()
            except Exception as e:
                self.log.error(f"Error deinitializing servo: {e}")

        self._servos.clear()
        self._pca = None
        self._connection_stats["current_status"] = "disconnected"

    def _angle_to_value(self, value: int) -> int:
        """
        Преобразует значение из внутреннего диапазона 0-100 в углы сервопривода (0-180).

        :param value: Значение в диапазоне 0-100
        :return: Угол в диапазоне 0-180
        """
        return max(0, min(180, int(value * 180 / 100)))

    def set_head_vertical(self, value: int = 55) -> None:
        """Установка вертикального положения головы (0–100)."""
        value = max(0, min(100, value))
        if self._ensure_connection():
            angle = self._angle_to_value(value)
            try:
                self._servos[HV].angle = angle
            except Exception as e:
                self.log.error(f"Error setting head vertical to {value}: {e}")

    def set_head_horizontal(self, value: int = 55) -> None:
        """Установка горизонтального положения головы (0–100)."""
        value = max(0, min(100, value))
        if self._ensure_connection():
            angle = self._angle_to_value(value)
            try:
                self._servos[HH].angle = angle
            except Exception as e:
                self.log.error(f"Error setting head horizontal to {value}: {e}")

    def set_right_wing(self, value: int = 55) -> None:
        """Установка правого крыла (0–100)."""
        value = max(0, min(100, value))
        if self._ensure_connection():
            angle = self._angle_to_value(value)
            try:
                self._servos[RW].angle = angle
            except Exception as e:
                self.log.error(f"Error setting right wing to {value}: {e}")

    def set_left_wing(self, value: int = 55) -> None:
        """Установка левого крыла (0–100)."""
        value = max(0, min(100, value))
        if self._ensure_connection():
            angle = self._angle_to_value(value)
            try:
                self._servos[LW].angle = angle
            except Exception as e:
                self.log.error(f"Error setting left wing to {value}: {e}")

    def add_command(self, command: dict) -> None:
        """Добавление команды в очередь."""
        if not isinstance(command, dict):
            self.log.error(f"Invalid command type: {type(command)}, expected dict")
            return
        self._command_queue.put(command)

    def sowa_sleep(self) -> None:
        """Поза сна — все сервы в нейтральное/отключённое состояние."""
        self.log.debug("DO SOWA SLEEP")
        commands = [
            {"id": HH, "value": 55},
            {"id": HV, "value": 0},
            {"id": LW, "value": 100},
            {"id": RW, "value": 0},
        ]
        for cmd in commands:
            self.add_command(cmd)

    def sowa_happy(self) -> None:
        """Радостная поза — крылья подняты, голова приподнята."""
        self.log.debug("DO SOWA HAPPY")
        commands = [
            {"id": HH, "value": 55},
            {"id": HV, "value": 30},
            {"id": LW, "value": 0},
            {"id": RW, "value": 95},
        ]
        for cmd in commands:
            self.add_command(cmd)

    def sowa_ready(self) -> None:
        """Готовность — голова приподнята, левое крыло опущено, правое — приподнято."""
        self.log.debug("DO SOWA READY")
        commands = [
            {"id": HH, "value": 55},
            {"id": HV, "value": 30},
            {"id": LW, "value": 0},
            {"id": RW, "value": 95},
        ]
        for cmd in commands:
            self.add_command(cmd)

    def sowa_lw_sign(self, count: int = 3) -> None:
        """Махание левым крылом N раз."""
        self.log.debug(f"DO SOWA LW SIGN (count={count})")
        commands = []
        for _ in range(count):
            commands.append({"id": LW, "value": 100})
            commands.append({"id": LW, "value": 0})
        for cmd in commands:
            self.add_command(cmd)

    def sowa_rw_sign(self, count: int = 3) -> None:
        """Махание правым крылом N раз."""
        self.log.debug(f"DO SOWA RW SIGN (count={count})")
        commands = []
        for _ in range(count):
            commands.append({"id": RW, "value": 95})
            commands.append({"id": RW, "value": 0})
        for cmd in commands:
            self.add_command(cmd)

    def stop(self) -> None:
        """Остановка потока и корректное завершение."""
        self.is_running_process = False
        self._stop_event.set()
        self.on_quit()
