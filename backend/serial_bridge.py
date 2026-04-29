"""
Serial Bridge — manages bidirectional serial communication with the ESP32.
"""

import threading
import time
import re
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
        self._scan_building: list[dict] = []
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

    @property
    def is_connected(self) -> bool: return self._connected
    @property
    def motor_state(self) -> str: return self._motor_state
    @property
    def state(self) -> str: return self._motor_state
    @property
    def is_scanning(self) -> bool: return self._scanning

    def get_scan_data(self) -> list[dict]:
        with self._scan_lock: return list(self._scan_data)
    def get_imu(self) -> dict:
        with self._imu_lock: return dict(self._imu)
    def get_encoders(self) -> dict:
        with self._encoders_lock: return dict(self._encoders)

    def connect(self) -> bool:
        """Open serial port and start reader thread."""
        try:
            self._ser = serial.Serial(port=self._port, baudrate=self._baud, timeout=self._timeout)
            time.sleep(2)
            self._connected = True
            self._running = True
            self._thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._thread.start()
            logger.info("Serial connected on %s @ %d", self._port, self._baud)
            return True
        except Exception as e:
            logger.error("Serial connect failed: %s", e)
            return False

    def disconnect(self):
        self._running = False
        if self._ser: self._ser.close()

    def send(self, command: str):
        if self._connected and self._ser:
            try:
                with self._lock:
                    self._ser.write(f"{command}\n".encode())
                logger.debug("TX: %s", command)
                return True
            except Exception as e:
                logger.error("Serial send error: %s", e)
                self._connected = False
        return False

    # Movement shorthands
    def move_forward(self): return self.send("CMD:FORWARD")
    def move_backward(self): return self.send("CMD:BACKWARD")
    def turn_left(self): return self.send("CMD:LEFT")
    def turn_right(self): return self.send("CMD:RIGHT")
    def stop(self): return self.send("CMD:STOP")

    def _reader_loop(self):
        buffer = ""
        while self._running:
            try:
                if self._ser and self._ser.in_available:
                    raw = self._ser.read(self._ser.in_available)
                    buffer += raw.decode("utf-8", errors="replace")
                    
                    # Robust splitting by newline OR by message start tags
                    parts = re.split(r'(\n|IMU:|SCAN:|ENC:|ACK:|ERR:|SCAN_DONE)', buffer)
                    current_msg = ""
                    for p in parts:
                        if p in ["\n", "IMU:", "SCAN:", "ENC:", "ACK:", "ERR:", "SCAN_DONE"]:
                            if current_msg: self._parse_line(current_msg)
                            current_msg = "" if p == "\n" else p
                        else:
                            current_msg += p
                    buffer = current_msg
                else:
                    time.sleep(0.01)
            except Exception as e:
                logger.error("Serial reader error: %s", e)
                time.sleep(2.0) # wait before retry

    def _parse_line(self, line: str):
        line = line.strip()
        if not line: return

        if line.startswith("SCAN:"):
            try:
                parts = line[5:].split(",")
                if len(parts) == 2:
                    with self._scan_lock:
                        self._scan_building.append({"angle": float(parts[0]), "dist": float(parts[1])})
            except: pass
        elif line == "SCAN_DONE":
            with self._scan_lock:
                self._scan_data = list(self._scan_building)
                self._scan_building = []
            self._scanning = False
            logger.info("Scan complete (%d points)", len(self._scan_data))
        elif line.startswith("IMU:"):
            try:
                p = line[4:].split(",")
                if len(p) == 7:
                    with self._imu_lock:
                        self._imu = {"ax":float(p[0]),"ay":float(p[1]),"az":float(p[2]),"gx":float(p[3]),"gy":float(p[4]),"gz":float(p[5]),"yaw":float(p[6])}
            except: pass
        elif line.startswith("ENC:"):
            try:
                p = line[4:].split(",")
                if len(p) == 2:
                    with self._encoders_lock: self._encoders = {"l": int(p[0]), "r": int(p[1])}
            except: pass
        elif line.startswith("ACK:"):
            ack = line[4:]
            if ack in ["FORWARD", "BACKWARD", "LEFT", "RIGHT"]: self._motor_state = ack.lower()
            elif ack == "STOP": self._motor_state = "stopped"
            elif ack == "SCAN_START": self._scanning = True
            elif ack == "SCAN_STOP": self._scanning = False
