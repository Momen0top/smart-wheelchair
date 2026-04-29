"""
Configuration for the SmartChair v3 system.
GPIO pin mappings, server settings, map grid parameters, safety limits.
"""

# ──────────────────────────────────────────────
# Server
# ──────────────────────────────────────────────
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

# ──────────────────────────────────────────────
# Motor A (Left) — L298N #1
# ──────────────────────────────────────────────
MOTOR_A_EN  = 25     # PWM enable
MOTOR_A_IN1 = 24     # Direction
MOTOR_A_IN2 = 23

# ──────────────────────────────────────────────
# Motor B (Right) — L298N #2
# ──────────────────────────────────────────────
MOTOR_B_EN  = 12     # PWM enable
MOTOR_B_IN1 = 16     # Direction
MOTOR_B_IN2 = 20

PWM_FREQUENCY   = 1000
DEFAULT_SPEED   = 60   # 0-100 %

# ──────────────────────────────────────────────
# Stepper Motor (28BYJ-48 via ULN2003)
# ──────────────────────────────────────────────
STEPPER_PINS = [6, 13, 19, 26]
STEPS_PER_REV = 4096          # half-step
STEPPER_DELAY = 0.001         # seconds between half-steps

# ──────────────────────────────────────────────
# VL53L0X (I2C)
# ──────────────────────────────────────────────
VL53L0X_I2C_ADDR = 0x29

# ──────────────────────────────────────────────
# Scan
# ──────────────────────────────────────────────
SCAN_RESOLUTION  = 200        # points per 360°
STEPS_PER_POINT  = STEPS_PER_REV // SCAN_RESOLUTION
ANGLE_PER_POINT  = 360.0 / SCAN_RESOLUTION

# ──────────────────────────────────────────────
# Occupancy Grid Map
# ──────────────────────────────────────────────
MAP_SIZE_CM      = 1000       # 10 m × 10 m world
MAP_RESOLUTION   = 5          # cm per cell
MAP_GRID_SIZE    = MAP_SIZE_CM // MAP_RESOLUTION   # 200×200
MAP_ORIGIN       = MAP_GRID_SIZE // 2              # robot starts at center

# Cell values
CELL_UNKNOWN = -1
CELL_FREE    =  0
CELL_OCCUPIED =  1

# ──────────────────────────────────────────────
# Safety
# ──────────────────────────────────────────────
SAFETY_DISTANCE_MM = 200      # emergency stop threshold
OBSTACLE_INFLATE   = 2        # grid cells to inflate obstacles for nav

# ──────────────────────────────────────────────
# Navigation
# ──────────────────────────────────────────────
NAV_GOAL_TOLERANCE = 3        # grid cells — close enough to target

# ──────────────────────────────────────────────
# Pairing
# ──────────────────────────────────────────────
ROBOT_ID = "smartchair-001"

# ──────────────────────────────────────────────
# Data files
# ──────────────────────────────────────────────
ROOMS_FILE = "rooms.json"
