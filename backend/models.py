"""
Pydantic models for SmartChair v3.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class ScanPoint(BaseModel):
    angle: float
    distance: float


class ScanResponse(BaseModel):
    data: List[ScanPoint] = Field(default_factory=list)


class MapCell(BaseModel):
    """Single map cell for JSON serialisation."""
    x: int
    y: int
    value: int     # -1=unknown, 0=free, 1=occupied


class MapData(BaseModel):
    width: int
    height: int
    resolution: float        # cm per cell
    cells: List[List[int]]   # 2D grid
    robot_x: float = 0.0
    robot_y: float = 0.0
    robot_yaw: float = 0.0


class Room(BaseModel):
    name: str
    x: float          # world cm
    y: float


class RoomCreateRequest(BaseModel):
    name: str
    x: float
    y: float


class NavRequest(BaseModel):
    room_name: str


class CommandRequest(BaseModel):
    text: str


class CommandResponse(BaseModel):
    intent: str
    parameter: str = ""
    status: str = "ok"


class StatusResponse(BaseModel):
    motors: str = "stopped"
    scanning: bool = False
    navigating: bool = False
    target_room: str = ""


class PairingInfo(BaseModel):
    robot_id: str
    ip: str
    port: int


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
