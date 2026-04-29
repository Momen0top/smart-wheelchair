import serial
import time

try:
    ser = serial.Serial('COM4', 115200, timeout=1)
    print("--- STARTING RECORDING ---")
    start_time = time.time()
    while time.time() - start_time < 3:
        if ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='replace').strip()
            if line:
                print(line)
    print("--- RECORDING FINISHED ---")
    ser.close()
except Exception as e:
    print(f"ERROR: {e}")
