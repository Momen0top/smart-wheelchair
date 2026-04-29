"""
SmartChair v3 — FastAPI + WebSocket Server.

Endpoints:
  GET  /status         — motor state, scanning, navigating
  GET  /map            — current occupancy grid
  GET  /scan           — latest LIDAR scan
  GET  /rooms          — list rooms
  POST /rooms          — create/update room
  DELETE /rooms/{name} — delete room
  POST /navigate       — start navigation to room
  POST /command        — NLP voice command
  POST /stop           — emergency stop
  GET  /pairing/qr     — QR code image
  GET  /pairing/info   — pairing JSON
  WS   /ws/map         — live map stream
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from config import SERVER_HOST, SERVER_PORT, MAP_GRID_SIZE, MAP_RESOLUTION
from models import (
    CommandRequest, CommandResponse, NavRequest,
    RoomCreateRequest, StatusResponse, ScanResponse,
)
from mapping_engine import MappingEngine
from room_manager import RoomManager
from navigator import Navigator
from command_interpreter import CommandInterpreter
from serial_bridge import SerialBridge
from pairing import generate_qr_bytes, get_pairing_payload
from utils import logger


# ── Globals ─────────────────────────────────────
motor: SerialBridge | None = None
scanner: SerialBridge | None = None
mapper: MappingEngine | None = None
rooms: RoomManager | None = None
nav: Navigator | None = None
interpreter: CommandInterpreter | None = None

# WebSocket clients
ws_clients: List[WebSocket] = []

MOVE_ACTIONS = {} # Will be populated in lifespan


# ── Background map updater ──────────────────────
async def map_update_loop():
    """Periodically integrates scans into the map and broadcasts."""
    while True:
        await asyncio.sleep(2.0) # Slow down updates to save bandwidth
        if scanner and mapper:
            scan = scanner.get_scan_data()
            if scan:
                logger.info("Integrating scan (%d points) into map...", len(scan))
                mapper.update_from_scan(scan)
                await broadcast_map()


async def broadcast_map():
    """Send current map to all WebSocket clients."""
    if not mapper or not ws_clients:
        return
    
    logger.debug("Broadcasting map to %d clients...", len(ws_clients))
    try:
        data = json.dumps({
            "type": "map",
            "width": MAP_GRID_SIZE,
            "height": MAP_GRID_SIZE,
            "resolution": MAP_RESOLUTION,
            "robot_x": mapper.robot_x,
            "robot_y": mapper.robot_y,
            "robot_yaw": mapper.robot_yaw,
            "cells": mapper.get_grid_list(),
        })
        
        dead = []
        for ws in ws_clients:
            try:
                await asyncio.wait_for(ws.send_text(data), timeout=1.0)
            except Exception:
                dead.append(ws)
        
        for d in dead:
            try:
                ws_clients.remove(d)
            except ValueError:
                pass
    except Exception as e:
        logger.warning("Broadcast error: %s", e)


# ── Lifespan ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global motor, scanner, mapper, rooms, nav, interpreter, MOVE_ACTIONS

    logger.info("🚀  SmartChair v3 starting (Serial/ESP32 Mode) …")

    bridge = SerialBridge()
    if not bridge.connect():
        logger.error("❌  Could not connect to ESP32! Check SERIAL_PORT in config.py")
    
    motor = bridge
    scanner = bridge
    mapper = MappingEngine()
    rooms = RoomManager()
    nav = Navigator(mapper, motor, scanner)
    interpreter = CommandInterpreter()

    MOVE_ACTIONS = {
        "forward":  lambda: motor.move_forward(),
        "backward": lambda: motor.move_backward(),
        "left":     lambda: motor.turn_left(),
        "right":    lambda: motor.turn_right(),
    }

    # Start background map updater
    task = asyncio.create_task(map_update_loop())

    yield

    task.cancel()
    logger.info("🛑  Shutting down …")
    if nav:
        nav.cancel()
    if motor:
        motor.disconnect()
    logger.info("Goodbye.")


# ── App ─────────────────────────────────────────
app = FastAPI(
    title="SmartChair API",
    version="3.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════
#  REST ENDPOINTS
# ═══════════════════════════════════════════════

@app.get("/status")
async def get_status():
    return StatusResponse(
        motors=motor.state if motor else "unknown",
        scanning=scanner.is_scanning if scanner else False,
        navigating=nav.is_navigating if nav else False,
        target_room=nav.target_room if nav else "",
    )

@app.get("/map")
async def get_map():
    if not mapper:
        raise HTTPException(503, "Mapper not ready")
    return {
        "width": MAP_GRID_SIZE,
        "height": MAP_GRID_SIZE,
        "resolution": MAP_RESOLUTION,
        "robot_x": mapper.robot_x,
        "robot_y": mapper.robot_y,
        "robot_yaw": mapper.robot_yaw,
        "cells": mapper.get_grid_list(),
    }

@app.get("/scan")
async def get_scan():
    if not scanner:
        raise HTTPException(503, "Scanner not ready")
    return ScanResponse(data=scanner.get_scan_data())

@app.get("/rooms")
async def list_rooms():
    if not rooms:
        raise HTTPException(503)
    return rooms.list_rooms()

@app.post("/rooms")
async def create_room(req: RoomCreateRequest):
    if not rooms:
        raise HTTPException(503)
    return rooms.set_room(req.name, req.x, req.y)

@app.delete("/rooms/{name}")
async def delete_room(name: str):
    if not rooms:
        raise HTTPException(503)
    if rooms.delete_room(name):
        return {"status": "deleted"}
    raise HTTPException(404)

@app.post("/navigate")
async def navigate(req: NavRequest):
    logger.info("📍  Navigate: %s", req.room_name)
    await process_incoming_command(f"go to {req.room_name}")
    return {"status": "accepted"}

@app.post("/command")
async def post_command(req: CommandRequest):
    logger.info("🎮  Command: %s", req.text)
    await process_incoming_command(req.text)
    return {"status": "accepted"}

@app.post("/stop")
async def post_stop():
    logger.info("🛑  STOP")
    await process_incoming_command("stop")
    return {"status": "stopped"}

@app.get("/pairing/qr")
async def get_qr():
    img_bytes = generate_qr_bytes()
    return Response(content=img_bytes, media_type="image/png")

@app.get("/pairing/info")
async def get_pairing_info():
    return get_pairing_payload()


# ═══════════════════════════════════════════════
#  WEBSOCKET & COMMAND LOGIC
# ═══════════════════════════════════════════════

async def process_incoming_command(text: str):
    """Unified command processor for HTTP and WebSocket."""
    if not interpreter or not motor:
        return
    
    result = interpreter.interpret(text)
    intent = result["intent"]
    param = result["parameter"]

    if intent == "navigate" and nav and rooms:
        room = rooms.get_room(param)
        if room:
            nav.navigate_to(room["name"], room["x"], room["y"])
    elif intent == "move":
        action = MOVE_ACTIONS.get(param)
        if action: action()
    elif intent == "stop":
        motor.stop()
        if nav and nav.is_navigating: nav.cancel()
    elif intent == "scan":
        if scanner: scanner.send("CMD:SCAN_START")

@app.websocket("/ws/map")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    logger.info("📡  WebSocket connected (%d total)", len(ws_clients))
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "command":
                    await process_incoming_command(msg.get("text", ""))
            except: pass
    except WebSocketDisconnect:
        if websocket in ws_clients: ws_clients.remove(websocket)
    except Exception:
        if websocket in ws_clients: ws_clients.remove(websocket)


if __name__ == "__main__":
    uvicorn.run("main:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)
