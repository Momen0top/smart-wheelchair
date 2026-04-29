"""
Navigator — A* pathfinding + autonomous drive controller.

Takes a target (world coordinates), runs A* on the inflated occupancy grid,
then drives the robot along the path. Continuously re-checks the LIDAR for
obstacles and recalculates the path if blocked.
"""
import heapq
import math
import threading
import time

from config import (
    MAP_GRID_SIZE, CELL_FREE, CELL_OCCUPIED,
    NAV_GOAL_TOLERANCE, SAFETY_DISTANCE_MM,
)
from utils import logger


class Navigator:
    """A* pathfinding and autonomous drive loop."""

    def __init__(self, mapping_engine, motor_controller, lidar_scanner):
        self._map = mapping_engine
        self._motor = motor_controller
        self._lidar = lidar_scanner

        self._running = False
        self._thread = None
        self._target_room = ""
        self._target_gx = 0
        self._target_gy = 0
        self._path: list[tuple[int, int]] = []

    # ── properties ───────────────────────────
    @property
    def is_navigating(self) -> bool:
        return self._running

    @property
    def target_room(self) -> str:
        return self._target_room

    @property
    def current_path(self) -> list[tuple[int, int]]:
        return list(self._path)

    # ── A* pathfinding ───────────────────────

    @staticmethod
    def _heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    def find_path(self, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
        """A* search on the inflated occupancy grid.
        Returns list of (gx, gy) from start to goal, or empty list.
        """
        grid = self._map.get_inflated_grid()

        open_set: list[tuple[float, tuple[int, int]]] = []
        heapq.heappush(open_set, (0.0, start))

        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        g_score: dict[tuple[int, int], float] = {start: 0.0}

        # 8-connected neighbours
        neighbours = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1),
        ]

        while open_set:
            _, current = heapq.heappop(open_set)

            if self._heuristic(current, goal) <= NAV_GOAL_TOLERANCE:
                # Reconstruct path
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path

            for dx, dy in neighbours:
                nx, ny = current[0] + dx, current[1] + dy
                if not (0 <= nx < MAP_GRID_SIZE and 0 <= ny < MAP_GRID_SIZE):
                    continue
                if grid[ny, nx] == CELL_OCCUPIED:
                    continue

                move_cost = math.sqrt(dx * dx + dy * dy)
                tentative_g = g_score[current] + move_cost

                if tentative_g < g_score.get((nx, ny), float("inf")):
                    came_from[(nx, ny)] = current
                    g_score[(nx, ny)] = tentative_g
                    f = tentative_g + self._heuristic((nx, ny), goal)
                    heapq.heappush(open_set, (f, (nx, ny)))

        return []  # no path found

    # ── Steering ─────────────────────────────

    def _steer_toward(self, target_gx: int, target_gy: int):
        """Simple differential-drive steering toward a grid cell."""
        rx, ry = self._map.world_to_grid(self._map.robot_x, self._map.robot_y)
        dx = target_gx - rx
        dy = target_gy - ry
        target_angle = math.atan2(dy, dx)

        # Angle difference
        diff = target_angle - self._map.robot_yaw
        # Normalise to [-pi, pi]
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi

        threshold = math.radians(20)

        if abs(diff) > threshold:
            if diff > 0:
                self._motor.turn_left()
            else:
                self._motor.turn_right()
            time.sleep(0.15)
            self._motor.stop()
        else:
            self._motor.move_forward()
            time.sleep(0.2)
            self._motor.stop()

    # ── Autonomous drive loop ────────────────

    def _nav_loop(self):
        """Background thread: follow path, re-plan on obstacles."""
        logger.info("Navigation started → '%s'", self._target_room)

        while self._running:
            rx, ry = self._map.world_to_grid(self._map.robot_x, self._map.robot_y)
            dist = self._heuristic((rx, ry), (self._target_gx, self._target_gy))

            # Arrived?
            if dist <= NAV_GOAL_TOLERANCE:
                logger.info("Arrived at '%s'!", self._target_room)
                self._motor.stop()
                self._running = False
                break

            # Safety check
            if self._lidar.obstacle_alert:
                logger.warning("Obstacle detected — stopping and replanning")
                self._motor.stop()
                time.sleep(0.5)

                # Recalculate path
                start = (rx, ry)
                goal = (self._target_gx, self._target_gy)
                self._path = self.find_path(start, goal)
                if not self._path:
                    logger.error("No path found — aborting navigation")
                    self._running = False
                    break
                continue

            # Follow path
            if self._path:
                next_cell = self._path[0]
                cell_dist = self._heuristic((rx, ry), next_cell)
                if cell_dist <= 1.5:
                    self._path.pop(0)
                    if not self._path:
                        continue
                    next_cell = self._path[0]
                self._steer_toward(next_cell[0], next_cell[1])
            else:
                # Replan
                start = (rx, ry)
                goal = (self._target_gx, self._target_gy)
                self._path = self.find_path(start, goal)
                if not self._path:
                    logger.error("No path — aborting")
                    self._running = False
                    break

            time.sleep(0.1)

        self._motor.stop()
        self._running = False
        logger.info("Navigation ended")

    # ── Public API ───────────────────────────

    def navigate_to(self, room_name: str, world_x: float, world_y: float) -> bool:
        """Start autonomous navigation to a world coordinate."""
        if self._running:
            self.cancel()

        self._target_room = room_name
        gx, gy = self._map.world_to_grid(world_x, world_y)
        self._target_gx = gx
        self._target_gy = gy

        rx, ry = self._map.world_to_grid(self._map.robot_x, self._map.robot_y)
        self._path = self.find_path((rx, ry), (gx, gy))

        if not self._path:
            logger.error("No path to '%s'", room_name)
            return False

        self._running = True
        self._thread = threading.Thread(target=self._nav_loop, daemon=True)
        self._thread.start()
        return True

    def cancel(self):
        self._running = False
        self._motor.stop()
        if self._thread:
            self._thread.join(timeout=3)
        self._path = []
        logger.info("Navigation cancelled")
