"""
Virtual Test Server for SmartChair v3 (V3 - Size/Type Fix).
Simulates a square room and allows the app to connect and see a map.
"""
import asyncio
import json
import math
import random
from typing import List
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Configurations: Smaller size to ensure no transmission/timeout issues
MAP_GRID_SIZE = 100
MAP_RESOLUTION = 10.0  # 10cm per cell -> 10m x 10m
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

# Cell values from config.py
CELL_UNKNOWN = -1
CELL_FREE = 0
CELL_OCCUPIED = 1

class MockMapper:
    def __init__(self):
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_yaw = 0.0
        # Initialize grid with -1 (unknown)
        self.grid = [[int(CELL_UNKNOWN) for _ in range(MAP_GRID_SIZE)] for _ in range(MAP_GRID_SIZE)]
        self._generate_static_room()

    def _generate_static_room(self):
        # Create a 6m x 6m room (60x60 cells)
        center = MAP_GRID_SIZE // 2
        half_room = 30
        start = center - half_room
        end = center + half_room
        
        for y in range(start, end + 1):
            for x in range(start, end + 1):
                if x == start or x == end or y == start or y == end:
                    self.grid[y][x] = int(CELL_OCCUPIED)
                else:
                    self.grid[y][x] = int(CELL_FREE)
        
        # Add some random obstacles
        for _ in range(15):
            ox = random.randint(start + 5, end - 5)
            oy = random.randint(start + 5, end - 5)
            self.grid[oy][ox] = int(CELL_OCCUPIED)

    def get_grid_list(self):
        return self.grid

mapper = MockMapper()
ws_clients: List[WebSocket] = []

app = FastAPI(title="SmartChair Virtual Test")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status")
async def get_status():
    return {
        "motors": "idle",
        "scanning": True,
        "navigating": False,
        "target_room": "",
        "is_mock": True
    }

@app.get("/map")
async def get_map():
    return {
        "type": "map", # Adding type here too just in case MapData.fromJson needs it if used directly
        "width": MAP_GRID_SIZE,
        "height": MAP_GRID_SIZE,
        "resolution": MAP_RESOLUTION,
        "robot_x": mapper.robot_x,
        "robot_y": mapper.robot_y,
        "robot_yaw": mapper.robot_yaw,
        "cells": mapper.get_grid_list(),
    }

@app.get("/rooms")
async def list_rooms():
    return [
        {"name": "Kitchen", "x": -200.0, "y": -200.0},
        {"name": "Living Room", "x": 200.0, "y": 200.0}
    ]

@app.post("/stop")
async def post_stop():
    return {"status": "stopped"}

@app.websocket("/ws/map")
async def ws_map(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    print(f"DEBUG: WebSocket client connected. Total: {len(ws_clients)}")
    try:
        while True:
            # Broadcast map
            payload = {
                "type": "map",
                "width": MAP_GRID_SIZE,
                "height": MAP_GRID_SIZE,
                "resolution": float(MAP_RESOLUTION),
                "robot_x": float(mapper.robot_x),
                "robot_y": float(mapper.robot_y),
                "robot_yaw": float(mapper.robot_yaw),
                "cells": mapper.get_grid_list(),
            }
            await websocket.send_text(json.dumps(payload))
            
            try:
                # Wait for 1 second or a message
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                if msg == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        ws_clients.remove(websocket)
        print("DEBUG: WebSocket client disconnected.")
    except Exception as e:
        print(f"DEBUG: WebSocket Error: {e}")

if __name__ == "__main__":
    print(f"🚀 Virtual Test Server V3 starting on {SERVER_HOST}:{SERVER_PORT}")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
