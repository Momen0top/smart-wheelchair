"""
Mapping Engine — converts LIDAR scans into a 2D occupancy grid.

Uses polar→Cartesian conversion and Bresenham ray-casting to mark
free space along each beam and occupied cells at the endpoint.
"""
import math
import threading
import numpy as np

from config import (
    MAP_GRID_SIZE, MAP_RESOLUTION, MAP_ORIGIN,
    CELL_UNKNOWN, CELL_FREE, CELL_OCCUPIED,
    OBSTACLE_INFLATE,
)
from utils import logger


class MappingEngine:

    def __init__(self):
        self._lock = threading.Lock()
        # Occupancy grid: -1 unknown, 0 free, 1 occupied
        self._grid = np.full((MAP_GRID_SIZE, MAP_GRID_SIZE), CELL_UNKNOWN, dtype=np.int8)

        # Robot pose in world coordinates (cm)
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_yaw = 0.0  # radians

        logger.info("MappingEngine ready (%d×%d grid, %dcm/cell)",
                     MAP_GRID_SIZE, MAP_GRID_SIZE, MAP_RESOLUTION)

    # ── Coordinate conversion ────────────────

    def _world_to_grid(self, wx: float, wy: float) -> tuple[int, int]:
        """World cm → grid cell."""
        gx = int(wx / MAP_RESOLUTION) + MAP_ORIGIN
        gy = int(wy / MAP_RESOLUTION) + MAP_ORIGIN
        return gx, gy

    def _grid_to_world(self, gx: int, gy: int) -> tuple[float, float]:
        """Grid cell → world cm."""
        wx = (gx - MAP_ORIGIN) * MAP_RESOLUTION
        wy = (gy - MAP_ORIGIN) * MAP_RESOLUTION
        return wx, wy

    def _in_bounds(self, gx: int, gy: int) -> bool:
        return 0 <= gx < MAP_GRID_SIZE and 0 <= gy < MAP_GRID_SIZE

    # ── Bresenham ray-cast ───────────────────

    def _bresenham(self, x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
        """Generate all grid cells along a line from (x0,y0) to (x1,y1)."""
        cells = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            cells.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
        return cells

    # ── Update from scan ─────────────────────

    def update_from_scan(self, scan_data: list[dict]):
        """Integrate a full LIDAR scan into the occupancy grid.

        Each scan point: {angle: degrees, distance: mm}
        Polar→Cartesian, then Bresenham ray-cast to mark free/occupied.
        """
        rx, ry = self._world_to_grid(self.robot_x, self.robot_y)

        with self._lock:
            for pt in scan_data:
                angle_deg = pt.get("angle", 0)
                dist_mm = pt.get("distance", -1)
                if dist_mm <= 0:
                    continue

                # Polar → Cartesian (world cm)
                angle_rad = math.radians(angle_deg) + self.robot_yaw
                dist_cm = dist_mm / 10.0
                wx = self.robot_x + dist_cm * math.cos(angle_rad)
                wy = self.robot_y + dist_cm * math.sin(angle_rad)

                ex, ey = self._world_to_grid(wx, wy)

                # Ray-cast: mark free cells along the beam
                ray = self._bresenham(rx, ry, ex, ey)
                for cx, cy in ray[:-1]:  # all except endpoint = free
                    if self._in_bounds(cx, cy):
                        self._grid[cy, cx] = CELL_FREE

                # Endpoint = occupied
                if self._in_bounds(ex, ey):
                    self._grid[ey, ex] = CELL_OCCUPIED

        logger.debug("Map updated from %d scan points", len(scan_data))

    # ── Grid accessors ───────────────────────

    def get_grid(self) -> np.ndarray:
        """Return a copy of the occupancy grid."""
        with self._lock:
            return self._grid.copy()

    def get_grid_list(self) -> list[list[int]]:
        """Return the grid as a 2D list (for JSON serialisation)."""
        with self._lock:
            return self._grid.tolist()

    def get_inflated_grid(self) -> np.ndarray:
        """Return grid with obstacles inflated for navigation."""
        with self._lock:
            grid = self._grid.copy()

        # Inflate obstacles
        occupied = np.argwhere(grid == CELL_OCCUPIED)
        for oy, ox in occupied:
            for dy in range(-OBSTACLE_INFLATE, OBSTACLE_INFLATE + 1):
                for dx in range(-OBSTACLE_INFLATE, OBSTACLE_INFLATE + 1):
                    ny, nx = oy + dy, ox + dx
                    if 0 <= ny < MAP_GRID_SIZE and 0 <= nx < MAP_GRID_SIZE:
                        if grid[ny, nx] != CELL_OCCUPIED:
                            grid[ny, nx] = CELL_OCCUPIED
        return grid

    def is_cell_free(self, gx: int, gy: int) -> bool:
        if not self._in_bounds(gx, gy):
            return False
        with self._lock:
            return self._grid[gy, gx] == CELL_FREE

    def world_to_grid(self, wx: float, wy: float) -> tuple[int, int]:
        """Public wrapper."""
        return self._world_to_grid(wx, wy)

    def grid_to_world(self, gx: int, gy: int) -> tuple[float, float]:
        """Public wrapper."""
        return self._grid_to_world(gx, gy)
