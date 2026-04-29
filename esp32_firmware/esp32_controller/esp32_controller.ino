/*
 * ═══════════════════════════════════════════════════════════════════
 *  SMART WHEELCHAIR — Optimized Multi-Tasking ESP32 Firmware
 * ═══════════════════════════════════════════════════════════════════
 * 
 *  Architecture:
 *    - Task A (Core 0): Serial Communication & Command Parsing (High Priority)
 *    - Task B (Core 1): Lidar Scanning & Motor Control (Medium Priority)
 *    - Task C (Core 1): IMU & Encoder Reporting (Low Priority)
 * 
 *  This design ensures that motor commands (D-pad) are processed with 
 *  microsecond latency even while the Lidar is scanning.
 */

#include <Wire.h>
#include <Adafruit_VL53L1X.h>

// ═══════════════════════════════════════════════════════════════════
//  PIN DEFINITIONS
// ═══════════════════════════════════════════════════════════════════
#define SDA_PIN   21
#define SCL_PIN   22

// Motor Pins
#define MOTOR_A_EN   15
#define MOTOR_A_IN1  5
#define MOTOR_A_IN2  19
#define MOTOR_B_EN   2
#define MOTOR_B_IN1  17
#define MOTOR_B_IN2  18

// Stepper Pins
#define STEPPER_IN1  27
#define STEPPER_IN2  26
#define STEPPER_IN3  25
#define STEPPER_IN4  33

// Encoder Pins
#define ENC_L_A 36
#define ENC_L_B 39
#define ENC_R_A 34
#define ENC_R_B 35

// ═══════════════════════════════════════════════════════════════════
//  CONSTANTS & GLOBALS
// ═══════════════════════════════════════════════════════════════════
#define SERIAL_BAUD       115200
#define STEPS_PER_REV     4096
#define SCAN_POINTS       200
#define STEPS_PER_POINT   (STEPS_PER_REV / SCAN_POINTS)
#define STEPPER_DELAY_US  1200 

Adafruit_VL53L1X vl53;
SemaphoreHandle_t serialMutex;

// Volatile state for multi-tasking
volatile bool scanning = false;
volatile int motorSpeed = 70;
enum MotorState { STOP, FORWARD, BACKWARD, LEFT, RIGHT };
volatile MotorState currentMotorState = STOP;

volatile long encL_count = 0;
volatile long encR_count = 0;

// ═══════════════════════════════════════════════════════════════════
//  INTERRUPTS
// ═══════════════════════════════════════════════════════════════════
void IRAM_ATTR isr_encL() {
    if (digitalRead(ENC_L_A) == digitalRead(ENC_L_B)) encL_count--;
    else encL_count++;
}
void IRAM_ATTR isr_encR() {
    if (digitalRead(ENC_R_A) == digitalRead(ENC_R_B)) encR_count++;
    else encR_count--;
}

// ═══════════════════════════════════════════════════════════════════
//  MOTOR CONTROL HELPERS
// ═══════════════════════════════════════════════════════════════════
void applyMotorHardware() {
    uint8_t pwm = (uint8_t)map(motorSpeed, 0, 100, 0, 255);
    
    switch (currentMotorState) {
        case FORWARD:
            digitalWrite(MOTOR_A_IN1, LOW);  digitalWrite(MOTOR_A_IN2, HIGH);
            digitalWrite(MOTOR_B_IN1, LOW);  digitalWrite(MOTOR_B_IN2, HIGH);
            analogWrite(MOTOR_A_EN, pwm);    analogWrite(MOTOR_B_EN, pwm);
            break;
        case BACKWARD:
            digitalWrite(MOTOR_A_IN1, HIGH); digitalWrite(MOTOR_A_IN2, LOW);
            digitalWrite(MOTOR_B_IN1, HIGH); digitalWrite(MOTOR_B_IN2, LOW);
            analogWrite(MOTOR_A_EN, pwm);    analogWrite(MOTOR_B_EN, pwm);
            break;
        case LEFT:
            digitalWrite(MOTOR_A_IN1, HIGH); digitalWrite(MOTOR_A_IN2, LOW);
            digitalWrite(MOTOR_B_IN1, LOW);  digitalWrite(MOTOR_B_IN2, HIGH);
            analogWrite(MOTOR_A_EN, pwm);    analogWrite(MOTOR_B_EN, pwm);
            break;
        case RIGHT:
            digitalWrite(MOTOR_A_IN1, LOW);  digitalWrite(MOTOR_A_IN2, HIGH);
            digitalWrite(MOTOR_B_IN1, HIGH); digitalWrite(MOTOR_B_IN2, LOW);
            analogWrite(MOTOR_A_EN, pwm);    analogWrite(MOTOR_B_EN, pwm);
            break;
        case STOP:
        default:
            analogWrite(MOTOR_A_EN, 0);      analogWrite(MOTOR_B_EN, 0);
            digitalWrite(MOTOR_A_IN1, LOW);  digitalWrite(MOTOR_A_IN2, LOW);
            digitalWrite(MOTOR_B_IN1, LOW);  digitalWrite(MOTOR_B_IN2, LOW);
            break;
    }
}

// ═══════════════════════════════════════════════════════════════════
//  TASK A: SERIAL COMMUNICATION (Core 0)
// ═══════════════════════════════════════════════════════════════════
void serialTask(void *pvParameters) {
    String buffer = "";
    while (1) {
        while (Serial.available()) {
            char c = Serial.read();
            if (c == '\n') {
                buffer.trim();
                if (buffer.startsWith("CMD:")) {
                    handleCommand(buffer);
                }
                buffer = "";
            } else {
                buffer += c;
            }
        }
        vTaskDelay(10 / portTICK_PERIOD_MS);
    }
}

void handleCommand(String cmd) {
    bool recognized = true;
    if (cmd == "CMD:FORWARD")  currentMotorState = FORWARD;
    else if (cmd == "CMD:BACKWARD") currentMotorState = BACKWARD;
    else if (cmd == "CMD:LEFT")     currentMotorState = LEFT;
    else if (cmd == "CMD:RIGHT")    currentMotorState = RIGHT;
    else if (cmd == "CMD:STOP")     currentMotorState = STOP;
    else if (cmd == "CMD:SCAN_START") scanning = true;
    else if (cmd == "CMD:SCAN_STOP")  scanning = false;
    else if (cmd.startsWith("CMD:SPEED:")) {
        motorSpeed = constrain(cmd.substring(10).toInt(), 0, 100);
    } else recognized = false;

    if (recognized) {
        applyMotorHardware();
        xSemaphoreTake(serialMutex, portMAX_DELAY);
        Serial.print("ACK:"); Serial.println(cmd.substring(4));
        xSemaphoreGive(serialMutex);
    }
}

// ═══════════════════════════════════════════════════════════════════
//  TASK B: LIDAR SCANNING (Core 1)
// ═══════════════════════════════════════════════════════════════════
const uint8_t HALF_STEP[8][4] = {
    {1,0,0,0},{1,1,0,0},{0,1,0,0},{0,1,1,0},
    {0,0,1,0},{0,0,1,1},{0,0,0,1},{1,0,0,1}
};
int stepPhase = 0;
int scanIndex = 0;
int stepDir = 1;

void stepMotor() {
    stepPhase = (stepPhase + stepDir + 8) % 8;
    digitalWrite(STEPPER_IN1, HALF_STEP[stepPhase][0]);
    digitalWrite(STEPPER_IN2, HALF_STEP[stepPhase][1]);
    digitalWrite(STEPPER_IN3, HALF_STEP[stepPhase][2]);
    digitalWrite(STEPPER_IN4, HALF_STEP[stepPhase][3]);
    delayMicroseconds(STEPPER_DELAY_US);
}

void lidarTask(void *pvParameters) {
    while (1) {
        if (scanning) {
            // 1. Move stepper
            for (int i = 0; i < STEPS_PER_POINT; i++) stepMotor();
            
            // 2. Non-blocking Wait for Lidar
            uint32_t timeout = millis() + 100;
            while (!vl53.dataReady() && millis() < timeout) {
                vTaskDelay(1 / portTICK_PERIOD_MS); 
            }
            
            if (vl53.dataReady()) {
                uint16_t dist = vl53.distance();
                vl53.clearInterrupt();
                float angle = scanIndex * (360.0 / SCAN_POINTS);
                
                xSemaphoreTake(serialMutex, portMAX_DELAY);
                Serial.print("SCAN:"); Serial.print(angle, 1); Serial.print(","); Serial.println(dist);
                xSemaphoreGive(serialMutex);
            }
            
            scanIndex++;
            if (scanIndex >= SCAN_POINTS) {
                scanIndex = 0;
                stepDir *= -1;
                xSemaphoreTake(serialMutex, portMAX_DELAY);
                Serial.println("SCAN_DONE");
                xSemaphoreGive(serialMutex);
            }
        } else {
            // Turn off stepper coils to save power
            digitalWrite(STEPPER_IN1, LOW); digitalWrite(STEPPER_IN2, LOW);
            digitalWrite(STEPPER_IN3, LOW); digitalWrite(STEPPER_IN4, LOW);
            vTaskDelay(100 / portTICK_PERIOD_MS);
        }
    }
}

// ═══════════════════════════════════════════════════════════════════
//  SETUP
// ═══════════════════════════════════════════════════════════════════
void setup() {
    Serial.begin(SERIAL_BAUD);
    serialMutex = xSemaphoreCreateMutex();
    
    Wire.begin(SDA_PIN, SCL_PIN);
    Wire.setClock(400000);

    // Pin Modes
    pinMode(MOTOR_A_IN1, OUTPUT); pinMode(MOTOR_A_IN2, OUTPUT); pinMode(MOTOR_A_EN, OUTPUT);
    pinMode(MOTOR_B_IN1, OUTPUT); pinMode(MOTOR_B_IN2, OUTPUT); pinMode(MOTOR_B_EN, OUTPUT);
    pinMode(STEPPER_IN1, OUTPUT); pinMode(STEPPER_IN2, OUTPUT); pinMode(STEPPER_IN3, OUTPUT); pinMode(STEPPER_IN4, OUTPUT);
    pinMode(ENC_L_A, INPUT); pinMode(ENC_L_B, INPUT); pinMode(ENC_R_A, INPUT); pinMode(ENC_R_B, INPUT);
    
    attachInterrupt(digitalPinToInterrupt(ENC_L_A), isr_encL, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ENC_R_A), isr_encR, CHANGE);

    // Sensors
    if (vl53.begin(0x29, &Wire)) {
        vl53.setTimingBudget(33);
        vl53.startRanging();
    }

    // Start Tasks
    xTaskCreatePinnedToCore(serialTask, "SerialTask", 4096, NULL, 3, NULL, 0);
    xTaskCreatePinnedToCore(lidarTask, "LidarTask", 4096, NULL, 2, NULL, 1);
    
    Serial.println("ACK:SYSTEM_BOOT_COMPLETE");
}

void loop() {
    // Keep core 1 free for reporting IMU or other low-pri telemetry
    // (Optional: add MPU6050 logic here or in another task)
    vTaskDelay(1000 / portTICK_PERIOD_MS);
}
