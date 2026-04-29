<style>
  body {
    font-size: 13.5px !important;
    line-height: 1.6 !important;
  }
  .team-header {
    text-align: center;
    font-size: 32px !important;
    font-weight: 900;
    color: #222;
    padding-top: 15px;
    padding-bottom: 15px;
    margin-bottom: 30px;
    border-bottom: 4px solid #444;
    text-transform: uppercase;
    letter-spacing: 2px;
  }
  h1 { font-size: 22px !important; margin-bottom: 15px !important; }
  h2 { font-size: 18px !important; margin-top: 30px !important; margin-bottom: 15px !important; border-bottom: 2px solid #ccc; padding-bottom: 8px; }
  h3 { font-size: 15.5px !important; margin-top: 20px !important; }
  p, li { margin-bottom: 10px !important; }
</style>

<div class="team-header">TEAM STORM</div>

# SmartChair Complete System Documentation

This document explains the overarching architecture of the SmartChair prototype. It details the separation of responsibilities across the hardware (ESP32), the "brain" (Raspberry Pi), and the user interface (Mobile Application).

---

## 1. System Overview & The Three Tiers

The SmartChair relies on a three-tier modular architecture:
1. **ESP32 Microcontroller (Hardware Layer):** Interacts natively with the physical world (motors, sensors).
2. **Raspberry Pi 3B (Computation Layer):** The "Brain" of the operation. Parses data, draws maps, calculates safe paths, hosts the network, and makes AI decisions.
3. **Flutter Mobile App (User Layer):** The visual interface. Streams the map, captures voice commands, and gives the user remote control via Wi-Fi.

Because of this separation, **the Raspberry Pi requires absolutely zero physical wires attached to it other than its power cable and one USB cable going to the ESP32.**

---

## 2. Hardware Connectivity

### ESP32 ↔ Raspberry Pi
* **Physical Connect:** A standard USB cable links the ESP32's micro-USB port to one of the Raspberry Pi's USB-A ports.
* **Protocol:** USB Serial Communication (UART).
* **Power:** The Raspberry Pi powers the ESP32 board over this USB connection. 

### Raspberry Pi ↔ Mobile App
* **Physical Connect:** Wireless (Wi-Fi). Both the user's phone and the Raspberry Pi connect to a common local Wi-Fi router.
* **Protocol:** Real-time HTTP REST API and WebSockets.
* **Pairing Mechanism:** The Raspberry Pi hosts a generated QR code (visible in testing or easily scannable from a monitor) that embeds its internal IP address (e.g., `192.168.1.55`). The phone scans this to establish the Wi-Fi connection instantly.

---

## 3. The ESP32 Peripheral Controller

The ESP32 runs C++ (Arduino) firmware and acts strictly as a "Real-Time Hardware Manager." It does not know what a "room" or a "map" is. 

**What it does:**
* **Continuous Scanning:** It rotates a ULN2003 stepper motor 360 degrees. Mounted on this motor is a VL53L1X Time-of-Flight laser sensor. 
* **Real-time IMU:** Reads a mounted MPU6050 gyroscope/accelerometer to calculate the chair's orientation (Yaw).
* **Motor Control:** Directly sends PWM signals to two L298N motor drivers to physically spin the left and right wheels (Forward, Backward, Turning).

**Data Formats:**
It constantly yells its raw data up the USB cable to the Pi as simple strings:
* `SCAN:45.0,1200` *(At 45 degrees, something is 1200mm away)*
* `IMU:ax,ay,az,gx,gy,gz,yaw`

It listens for strict commands coming down from the Pi:
* `CMD:FORWARD` or `CMD:STOP`

---

## 4. The Raspberry Pi Brain

The Raspberry Pi runs the backend server, hosted silently as a background service (`systemd`) that auto-boots without requiring a screen. It receives the "dumb" data from the ESP32 over the USB cable and applies heavy computations to it.

### What it does to the data (The Pipeline):

1. **Serial Bridging:**
   A background thread (`serial_bridge.py`) continuously listens to the USB port. It intercepts the incoming `SCAN:` and `IMU:` strings sent by the ESP32 and categorizes them.

2. **Occupancy Grid Mapping (SLAM-lite):** 
   The `mapping_engine.py` takes the raw polar coordinates (Degrees + Distance in mm). 
   * It applies trigonometry to convert these to **Cartesian X/Y coordinates**.
   * It uses *Bresenham’s Ray-Casting algorithm* on a 2D matrix array. The space between the wheelchair and the laser hit is flagged as `0` (Safe/Floor). The point where the laser stopped is flagged as `1` (Wall/Obstacle).
   * It "inflates" the walls virtually by a few centimeters to ensure the wheelchair's width doesn't clip a corner.

3. **Autonomous Navigation (A* Pathfinding):**
   When asked to move autonomously, the `navigator.py` calculates the shortest mathematical path through the 2D matrix array of 0s, strictly avoiding the 1s. It then translates that path into physical driving commands (`CMD:FORWARD`, `CMD:TURN_LEFT`) mapped back down the USB cable to the ESP32.

4. **AI Command Parsing:**
   A Natural Language Processing rule-engine (`command_interpreter.py`) takes plain English strings like *"take me to the kitchen"* and extracts the vital intent: `navigate`, target: `kitchen`.

5. **Room Management:**
   Translates custom "named targets" into X/Y coordinates on the map. This is saved permanently to the Pi's SD card inside a `rooms.json` file.

---

## 5. The Mobile App (Flutter)

The smartphone app provides the ultimate user experience, communicating wholly over local Wi-Fi to the Raspberry Pi.

### What it shows and how it interacts:
* **The WebSocket Live Map:** The app opens a persistent WebSocket connection to the Pi. Every one second, the Pi broadcasts its updated 2D matrix array over Wi-Fi. The phone uses a `CustomPainter` canvas to draw this matrix graphically.
   * *Visuals:* Black space is unknown, Dark Grey is explored floor, Red dots are obstacles, Purple arrow is the wheelchair, and Orange pins are saved rooms.
* **Saving Rooms:** The user can physically tap anywhere on the rendered map on their phone. A dialog pops up asking for a name (e.g., "Bathroom"). The phone issues a `POST /rooms` HTTP request to the Pi, saving that coordinate.
* **Voice Control Integration:** 
   * The user taps the purple microphone button.
   * The phone's native OS translates the audio stream to text (e.g. *"go back"*).
   * The phone sends a `POST /command` request to the Pi with the JSON payload: `{"text": "go back"}`.
   * The Pi calculates it, answers `{"status": "executed"}`, and sends the `CMD:BACKWARD` protocol to the ESP32!
* **Emergency Stop & Manual Overrides:** The app features a permanent D-pad and a large red Emergency Stop button. Pressing any of these sends instantaneous overriding HTTP requests to the Pi to halt the A* pathfinding and bypass straight to the USB-connected ESP motors.
