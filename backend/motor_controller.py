"""
Motor Controller — 2× L298N H-bridge drivers via RPi.GPIO.

Differential drive:
  Forward  → both forward
  Backward → both backward
  Left     → left back, right fwd
  Right    → left fwd,  right back
"""
import RPi.GPIO as GPIO
from config import (
    MOTOR_A_EN, MOTOR_A_IN1, MOTOR_A_IN2,
    MOTOR_B_EN, MOTOR_B_IN1, MOTOR_B_IN2,
    PWM_FREQUENCY, DEFAULT_SPEED,
)
from utils import clamp, logger


class MotorController:

    def __init__(self, speed: int = DEFAULT_SPEED):
        self._speed = clamp(speed)
        self._state = "stopped"

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for p in (MOTOR_A_EN, MOTOR_A_IN1, MOTOR_A_IN2,
                  MOTOR_B_EN, MOTOR_B_IN1, MOTOR_B_IN2):
            GPIO.setup(p, GPIO.OUT)

        self._pwm_a = GPIO.PWM(MOTOR_A_EN, PWM_FREQUENCY)
        self._pwm_b = GPIO.PWM(MOTOR_B_EN, PWM_FREQUENCY)
        self._pwm_a.start(0)
        self._pwm_b.start(0)
        logger.info("MotorController ready (speed=%d%%)", self._speed)

    # ── properties ───────────────────────────
    @property
    def state(self) -> str:
        return self._state

    def set_speed(self, v: int):
        self._speed = clamp(v)
        if self._state != "stopped":
            self._pwm_a.ChangeDutyCycle(self._speed)
            self._pwm_b.ChangeDutyCycle(self._speed)

    # ── private ──────────────────────────────
    def _a(self, in1, in2):
        GPIO.output(MOTOR_A_IN1, in1)
        GPIO.output(MOTOR_A_IN2, in2)

    def _b(self, in1, in2):
        GPIO.output(MOTOR_B_IN1, in1)
        GPIO.output(MOTOR_B_IN2, in2)

    def _go(self):
        self._pwm_a.ChangeDutyCycle(self._speed)
        self._pwm_b.ChangeDutyCycle(self._speed)

    # ── commands ─────────────────────────────
    def move_forward(self):
        self._a(True, False); self._b(True, False); self._go()
        self._state = "forward"

    def move_backward(self):
        self._a(False, True); self._b(False, True); self._go()
        self._state = "backward"

    def turn_left(self):
        self._a(False, True); self._b(True, False); self._go()
        self._state = "turning_left"

    def turn_right(self):
        self._a(True, False); self._b(False, True); self._go()
        self._state = "turning_right"

    def stop(self):
        self._pwm_a.ChangeDutyCycle(0)
        self._pwm_b.ChangeDutyCycle(0)
        self._a(False, False); self._b(False, False)
        self._state = "stopped"

    def cleanup(self):
        self.stop()
        self._pwm_a.stop(); self._pwm_b.stop()
        GPIO.cleanup()
        logger.info("MotorController cleaned up")
