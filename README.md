# SmartChair v3 — Complete System

A locally controlled smart robotic wheelchair with Raspberry Pi 3B, 2D LIDAR mapping, A* autonomous navigation, and a Flutter mobile app.

## Project Structure

```
chair/
├── backend/                        # Raspberry Pi (Python/FastAPI)
│   ├── main.py                     # FastAPI + WebSocket server
│   ├── config.py                   # GPIO pins, map grid, safety
│   ├── models.py                   # Pydantic models
│   ├── utils.py                    # Logging
│   ├── motor_controller.py         # 2× L298N DC motor control
│   ├── lidar_scanner.py            # Stepper + VL53L0X 360° scanner
│   ├── mapping_engine.py           # Occupancy grid + Bresenham ray-cast
│   ├── navigator.py                # A* pathfinding + autonomous drive
│   ├── room_manager.py             # rooms.json CRUD
│   ├── command_interpreter.py      # NLP intent extraction
│   ├── pairing.py                  # QR code generation
│   ├── requirements.txt
│   └── test_interpreter.py
│
├── wheelchair_app/                 # Flutter mobile app
│   ├── pubspec.yaml
│   ├── android/.../AndroidManifest.xml
│   └── lib/
│       ├── main.dart               # App shell + bottom nav
│       ├── models/models.dart      # Data classes
│       ├── services/
│       │   ├── api_service.dart    # REST client
│       │   ├── websocket_service.dart # Live map
│       │   └── speech_service.dart # Voice
│       ├── widgets/
│       │   ├── map_painter.dart    # Occupancy grid renderer
│       │   ├── room_dialog.dart    # Room naming
│       │   └── control_pad.dart    # D-pad
│       └── screens/
│           ├── map_screen.dart     # Main map view
│           ├── rooms_screen.dart   # Room list + Go
│           └── pairing_screen.dart # QR/NFC + manual
│
├── esp32_firmware/                 # (v2 ESP32 — optional)
│   └── esp32_controller/
│       └── esp32_controller.ino
│
└── README.md
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Raspberry Pi 3B                       │
│                                                         │
│  LIDAR Scanner ──► Mapping Engine ──► Navigator          │
│  (VL53L0X+stepper) (occupancy grid)  (A* pathfinding)  │
│                        │                  │             │
│  Motor Controller ◄────┴──────────────────┘             │
│  (2× L298N GPIO)                                        │
│                                                         │
│  FastAPI Server ──► WebSocket /ws/map                   │
│  Room Manager   ──► rooms.json                          │
│  Command Parser ──► NLP intent extraction               │
│  QR Generator   ──► PNG QR code                         │
└────────────────────┬────────────────────────────────────┘
                     │  Wi-Fi (HTTP + WebSocket)
┌────────────────────▼────────────────────────────────────┐
│                  Flutter App                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Map View │  │  Rooms   │  │ Connect  │              │
│  │          │  │          │  │          │              │
│  │ Live map │  │ Room list│  │ QR scan  │              │
│  │ Zoom/pan │  │ "Go" nav │  │ NFC tap  │              │
│  │ Tap→room │  │ Delete   │  │ Manual IP│              │
│  │ Voice    │  │          │  │          │              │
│  │ D-pad    │  │          │  │          │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
```

## Setup

### Raspberry Pi
```bash
cd backend/
pip install -r requirements.txt
python main.py        # starts on 0.0.0.0:8000
```

### Flutter App
```bash
cd wheelchair_app/
flutter create .      # generate platform scaffolding
flutter pub get
flutter run           # or: flutter build apk
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | Motor state, scanning, navigating |
| GET | `/map` | Current occupancy grid |
| GET | `/scan` | Latest LIDAR scan |
| GET | `/lidar` | Alias for /scan |
| GET | `/rooms` | List saved rooms |
| POST | `/rooms` | Create/update room |
| DELETE | `/rooms/{name}` | Delete room |
| POST | `/navigate` | Navigate to room |
| POST | `/command` | NLP voice command |
| POST | `/stop` | Emergency stop |
| GET | `/pairing/qr` | QR code PNG |
| GET | `/pairing/info` | Pairing JSON |
| WS | `/ws/map` | Live map stream |

## GPIO Wiring

| Component | BCM Pin | Function |
|-----------|---------|----------|
| Motor A EN | 25 | PWM speed |
| Motor A IN1 | 24 | Direction |
| Motor A IN2 | 23 | Direction |
| Motor B EN | 12 | PWM speed |
| Motor B IN1 | 16 | Direction |
| Motor B IN2 | 20 | Direction |
| Stepper IN1 | 6 | ULN2003 |
| Stepper IN2 | 13 | ULN2003 |
| Stepper IN3 | 19 | ULN2003 |
| Stepper IN4 | 26 | ULN2003 |
| VL53L0X SDA | GPIO 2 | I2C |
| VL53L0X SCL | GPIO 3 | I2C |
