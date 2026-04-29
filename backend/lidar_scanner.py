"""
LIDAR Scanner — 28BYJ-48 stepper + VL53L0X Time-of-Flight sensor.

Runs in a background thread. Rotates 360° CW, then 360° CCW, repeating.
At each angular step, reads distance. Publishes complete scans thread-safely.
"""
import threading
import time
import math

import RPi.GPIO as GPIO
import board
import busio
import adafruit_vl53l0x

from config import (
    STEPPER_PINS, STEPS_PER_REV, STEPPER_DELAY,
    SCAN_RESOLUTION, STEPS_PER_POINT, ANGLE_PER_POINT,
    SAFETY_DISTANCE_MM,
)
from utils import logger

# Half-step sequence (8 phases)
HALF_STEP = [
    [1,0,0,0],[1,1,0,0],[0,1,0,0],[0,1,1,0],
    [0,0,1,0],[0,0,1,1],[0,0,0,1],[1,0,0,1],
]


class LidarScanner:

    def __init__(self):
        self._lock = threading.Lock()
        self._scan_data: list[dict] = []
        self._current_scan: list[dict] = []
        self._running = False
        self._thread = None
        self._step_idx = 0
        self._obstacle_alert = False     # True if something within safety distance

        # ── Stepper GPIO ──
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for p in STEPPER_PINS:
            GPIO.setup(p, GPIO.OUT)
            GPIO.output(p, 0)

        # ── VL53L0X ──
        i2c = busio.I2C(board.SCL, board.SDA)
        self._sensor = adafruit_vl53l0x.VL53L0X(i2c)
        self._sensor.measurement_timing_budget = 30_000

        logger.info("LidarScanner ready")

    # ── properties ───────────────────────────
    @property
    def is_scanning(self) -> bool:
        return self._running

    @property
    def obstacle_alert(self) -> bool:
        return self._obstacle_alert

    def get_scan_data(self) -> list[dict]:
        with self._lock:
            return list(self._scan_data)

    # ── stepper ──────────────────────────────
    def _step(self, direction: int = 1):
        self._step_idx = (self._step_idx + direction) % 8
        phase = HALF_STEP[self._step_idx]
        for pin, val in zip(STEPPER_PINS, phase):
            GPIO.output(pin, val)
        time.sleep(STEPPER_DELAY)

    def _read_distance(self) -> float:
        try:
            return float(self._sensor.range)
        except Exception:
            return -1.0

    # ── scan loop ────────────────────────────
    def _loop(self):
        direction = 1
        while self._running:
            scan = []
            alert = False
            for i in range(SCAN_RESOLUTION):
                if not self._running:
                    break
                for _ in range(STEPS_PER_POINT):
                    if not self._running:
                        break
                    self._step(direction)
                dist = self._read_distance()
                angle = round(i * ANGLE_PER_POINT, 1)
                scan.append({"angle": angle, "distance": dist})
                if 0 < dist < SAFETY_DISTANCE_MM:
                    alert = True

            if self._running:
                with self._lock:
                    self._scan_data = scan
                self._obstacle_alert = alert
                logger.info("Scan done (%d pts, dir=%s, alert=%s)",
                            len(scan), "CW" if direction == 1 else "CCW", alert)
            direction *= -1

        for p in STEPPER_PINS:
            GPIO.output(p, 0)

    # ── control ──────────────────────────────
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        for p in STEPPER_PINS:
            GPIO.output(p, 0)

    def cleanup(self):
        self.stop()
