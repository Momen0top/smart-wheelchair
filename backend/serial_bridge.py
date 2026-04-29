"""
Serial Bridge — manages bidirectional serial communication with the ESP32.

ESP32 → Pi: SCAN data, IMU data, ACK/ERR messages
Pi → ESP32: Motor commands, scan control

Runs a background reader thread that parses incoming lines and updates
shared state (scan data, IMU, motor status).
"""

import threading
import time
from typing import Optional

import serial

from config import SERIAL_PORT, SERIAL_BAUD, SERIAL_TIMEOUT
from utils import logger


class SerialBridge:
    """Thread-safe serial connection to the ESP32 controller."""

    def __init__(
        self,
        port: str = SERIAL_PORT,
        baud: int = SERIAL_BAUD,
        timeout: float = SERIAL_TIMEOUT,
    ):
        self._port = port
        self._baud = baud
        self._timeout = timeout
        self._ser: Optional[serial.Serial] = None
        self._lock = threading.Lock()

        # ── Shared state ─────────────────────────
        self._scan_data: list[dict] = []
        self._scan_building: list[dict] = []  # partial scan in progress
        self._scan_lock = threading.Lock()

        self._imu: dict = {}
        self._imu_lock = threading.Lock()

        self._encoders: dict = {"l": 0, "r": 0}
        self._encoders_lock = threading.Lock()

        self._motor_state: str = "stopped"
        self._scanning: bool = False
        self._connected: bool = False
        self._last_ack: str = ""

        # ── Reader thread ────────────────────────
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ── Properties ──────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def motor_state(self) -> str:
        return self._motor_state

    @property
    def state(self) -> str:
        """Compatibility property for MotorController.state"""
        return self._motor_state

    @property
    def is_scanning(self) -> bool:
        return self._scanning

    def get_scan_data(self) -> list[dict]:
        with self._scan_lock:
            return list(self._scan_data)

    def get_imu(self) -> dict:
        with self._imu_lock:
            return dict(self._imu)

    def get_encoders(self) -> dict:
        with self._encoders_lock:
            return dict(self._encoders)

    # ── Connection ──────────────────────────────

    def connect(self) -> bool:
        """Open serial port and start reader thread."""
        try:
            self._ser = serial.Serial(
                port=self._port,
                baudrate=self._baud,
                timeout=self._timeout,
            )
            time.sleep(2)  # wait for ESP32 to reset after serial open
            self._connected = True
            self._running = True
            self._thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._thread.start()
            logger.info("Serial connected on %s @ %d", self._port, self._baud)

            # Ask ESP32 to start scanning
            self.send("CMD:SCAN_START")
            return True

        except serial.SerialException as e:
            logger.error("Serial connect failed: %s", e)
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Stop reader thread and close serial."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        if self._ser and self._ser.is_open:
            try:
                self.send("CMD:STOP")
                self.send("CMD:SCAN_STOP")
            except Exception:
                pass
            self._ser.close()
        self._connected = False
        logger.info("Serial disconnected")

    # ── Send command ────────────────────────────

    def send(self, command: str) -> bool:
        """Send a command string to the ESP32."""
        if not self._ser or not self._ser.is_open:
            logger.warning("Cannot send — serial not open")
            return False
        try:
            with self._lock:
                self._ser.write(f"{command}\n".encode("utf-8"))
                self._ser.flush()
            logger.debug("TX: %s", command)
            return True
        except serial.SerialException as e:
            logger.error("Serial write error: %s", e)
            self._connected = False
            return False

    # ── Motor commands (convenience) ────────────

    def move_forward(self) -> bool:
        self._motor_state = "forward"
        return self.send("CMD:FORWARD")

    def move_backward(self) -> bool:
        self._motor_state = "backward"
        return self.send("CMD:BACKWARD")

    def turn_left(self) -> bool:
        self._motor_state = "turning_left"
        return self.send("CMD:LEFT")

    def turn_right(self) -> bool:
        self._motor_state = "turning_right"
        return self.send("CMD:RIGHT")

    def stop(self) -> bool:
        self._motor_state = "stopped"
        return self.send("CMD:STOP")

    def set_speed(self, speed: int) -> bool:
        return self.send(f"CMD:SPEED:{max(0, min(100, speed))}")

    def start(self):
        """Compatibility method for LidarScanner. Already handled in connect()."""
        pass

    # ── Reader thread ───────────────────────────

    def _reader_loop(self) -> None:
        """Background thread: continuously reads lines from ESP32."""
        logger.info("Serial reader started")
        buffer = ""

        while self._running:
            if not self._ser or not self._ser.is_open:
                time.sleep(0.5)
                continue

            try:
                if self._ser.in_waiting > 0:
                    raw = self._ser.read(self._ser.in_waiting)
                    if not raw:
                        continue
                    
                    # Add to buffer and split by newlines
                    buffer += raw.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            self._parse_line(line)
                else:
                    time.sleep(0.01)

            except serial.SerialException as e:
                logger.error("Serial error (will retry): %s", e)
                self._connected = False
                if self._ser:
                    try: self._ser.close()
                    except: pass
                time.sleep(2)
                self.connect()
            except Exception as e:
                logger.warning("Reader loop error: %s", e)
                time.sleep(0.5)

        logger.info("Serial reader stopped")

    def _parse_line(self, line: str) -> None:
        """Parse a single line from ESP32."""

        if line.startswith("SCAN:"):
            # SCAN:<angle>,<distance>
            try:
                parts = line[5:].split(",")
                angle = float(parts[0])
                distance = float(parts[1])
                self._scan_building.append({
                    "angle": angle,
                    "distance": distance,
                })
            except (IndexError, ValueError) as e:
                logger.warning("Bad scan line: %s (%s)", line, e)

        elif line == "SCAN_DONE":
            # Full rotation complete — publish scan
            with self._scan_lock:
                self._scan_data = list(self._scan_building)
            self._scan_building = []
            self._scanning = True
            logger.info("Scan complete (%d points)", len(self._scan_data))

        elif line.startswith("IMU:"):
            # IMU:<ax>,<ay>,<az>,<gx>,<gy>,<gz>,<yaw>
            try:
                parts = line[4:].split(",")
                with self._imu_lock:
                    self._imu = {
                        "ax": float(parts[0]),
                        "ay": float(parts[1]),
                        "az": float(parts[2]),
                        "gx": float(parts[3]),
                        "gy": float(parts[4]),
                        "gz": float(parts[5]),
                        "yaw": float(parts[6]),
                    }
            except (IndexError, ValueError) as e:
                logger.warning("Bad IMU line: %s (%s)", line, e)

        elif line.startswith("ENC:"):
            # ENC:<encL>,<encR>
            try:
                parts = line[4:].split(",")
                with self._encoders_lock:
                    self._encoders = {
                        "l": int(parts[0]),
                        "r": int(parts[1])
                    }
            except (IndexError, ValueError) as e:
                logger.warning("Bad ENC line: %s (%s)", line, e)

        elif line.startswith("ACK:"):
            cmd = line[4:]
            self._last_ack = cmd
            logger.debug("ACK: %s", cmd)

            # Update motor state from ACK
            ack_to_state = {
                "FORWARD": "forward",
                "BACKWARD": "backward",
                "LEFT": "turning_left",
                "RIGHT": "turning_right",
                "STOP": "stopped",
                "SCAN_START": None,
                "SCAN_STOP": None,
            }
            if cmd in ack_to_state and ack_to_state[cmd] is not None:
                self._motor_state = ack_to_state[cmd]
            if cmd == "SCAN_START":
                self._scanning = True
            elif cmd == "SCAN_STOP":
                self._scanning = False

        elif line.startswith("ERR:"):
            logger.error("ESP32 error: %s", line[4:])

        else:
            logger.debug("ESP32: %s", line)
