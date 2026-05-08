# servo_controller.py
import queue
from threading import Thread, Event
from time import sleep
from typing import Optional, Dict, Any, Callable

from pymodbus.client import ModbusSerialClient

from app.core.logger import get_logger

# Сервоприводы: ID по протоколу Modbus
HV = 0  # Head Vertical
HH = 1  # Head Horizontal
LW = 2  # Left Wing
RW = 4  # Right Wing


class ServoControllerThread(Thread):
    """Контроллер сервоприводов через Modbus в отдельном потоке."""

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
        self._client: Optional[ModbusSerialClient] = None
        self._stop_event = Event()
        self.is_running_process = True

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

        if self._port is not None:
            self._connect_with_retry()

    def __enter__(self) -> "ServoControllerThread":
        """Поддержка контекстного менеджера."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Завершение работы при выходе из контекста."""
        self.stop()

    def _connect_with_retry(self) -> bool:
        """Подключение к устройству с экспоненциальной задержкой."""
        for attempt in range(1, self._reconnect_attempts + 1):
            self._connection_stats["attempts"] += 1
            delay = self._initial_retry_delay * (2 ** (attempt - 1))  # Экспоненциальная задержка

            try:
                self.log.info(
                    f"Connecting to Modbus device on port {self._port} "
                    f"(attempt {attempt}/{self._reconnect_attempts})"
                )
                self._client = ModbusSerialClient(port=self._port, timeout=0.1)
                if self._client.connect():
                    self.log.info(f"Successfully connected to Modbus device on port {self._port}")
                    self._connection_stats["successes"] += 1
                    self._connection_stats["current_status"] = "connected"
                    if self._on_connection_restored:
                        try:
                            self._on_connection_restored()
                        except Exception as e:
                            self.log.error(f"Error in on_connection_restored callback: {e}")
                    return True
                else:
                    self.log.warning(f"Connection attempt {attempt} failed: connect() returned False")
            except Exception as e:
                self.log.error(f"Connection attempt {attempt} failed with exception: {e}")

            # Обновляем статус при неудаче
            if attempt == 1 and self._connection_stats["current_status"] == "connected":
                self._connection_stats["current_status"] = "disconnected"
                if self._on_connection_lost:
                    try:
                        self._on_connection_lost()
                    except Exception as e:
                        self.log.error(f"Error in on_connection_lost callback: {e}")

            self._connection_stats["failures"] += 1

            if attempt < self._reconnect_attempts:
                self.log.info(f"Retrying in {delay:.1f} seconds...")
                sleep(delay)
            else:
                self.log.critical(f"Failed to connect after {self._reconnect_attempts} attempts")
                self._client = None
        return False

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику подключений (для мониторинга).

        :return: словарь с метриками
        """
        return self._connection_stats.copy()

    def reset_connection_stats(self) -> None:
        """Сброс статистики подключений."""
        current_status = (
            "connected"
            if self._client is not None and getattr(self._client, "connected", False)
            else "disconnected"
        )
        self._connection_stats = {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "current_status": current_status,
        }

    def run(self) -> None:
        """Основной цикл потока."""
        try:
            if self._client is not None:
                self.process()
            else:
                self.log.warning("Modbus client not initialized, thread exiting.")
        finally:
            self.log.info("Servo controller thread stopped.")

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

        # Приведение command_id к строке для сравнения
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
        if self._client is not None and getattr(self._client, "connected", False):
            return True

        self.log.warning("Modbus connection lost or not established. Attempting to reconnect...")
        self.on_quit()
        return self._connect_with_retry()

    def on_quit(self) -> None:
        """Закрытие клиента с проверкой."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception as e:
                self.log.error(f"Error closing Modbus client: {e}")
            finally:
                self._client = None
        self._connection_stats["current_status"] = "disconnected"

    def set_head_vertical(self, value: int = 55) -> None:
        """Установка вертикального положения головы (0–100)."""
        value = max(0, min(100, value))
        if self._ensure_connection():
            self._client.write_register(address=HV, value=value)

    def set_head_horizontal(self, value: int = 55) -> None:
        """Установка горизонтального положения головы (0–100)."""
        value = max(0, min(100, value))
        if self._ensure_connection():
            self._client.write_register(address=HH, value=value)

    def set_right_wing(self, value: int = 55) -> None:
        """Установка правого крыла (0–100)."""
        value = max(0, min(100, value))
        if self._ensure_connection():
            self._client.write_register(address=RW, value=value)

    def set_left_wing(self, value: int = 55) -> None:
        """Установка левого крыла (0–100)."""
        value = max(0, min(100, value))
        if self._ensure_connection():
            self._client.write_register(address=LW, value=value)

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
            {"id": LW, "value": 0},
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
            {"id": LW, "value": 100},
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