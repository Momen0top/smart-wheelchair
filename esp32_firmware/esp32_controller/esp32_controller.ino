/*
 * ═══════════════════════════════════════════════════════════════════
 *  SMART WHEELCHAIR — ESP32 Controller Firmware
 * ═══════════════════════════════════════════════════════════════════
 *
 *  Hardware:
 *    - ESP32 38-pin DevKit
 *    - MPU6050 (I2C gyroscope/accelerometer)
 *    - 2x L298N motor drivers (left + right DC motors)
 *    - ULN2003A stepper driver (28BYJ-48 stepper motor)
 *    - VL53L1X ToF laser sensor (I2C)
 *
 *  Communication:
 *    USB Serial (115200 baud) to Raspberry Pi
 *
 *  Serial Protocol:
 *    ESP32 → Pi:
 *      SCAN:<angle>,<distance_mm>\n        (per measurement point)
 *      SCAN_DONE\n                         (full rotation complete)
 *      IMU:<ax>,<ay>,<az>,<gx>,<gy>,<gz>,<yaw>\n
 *      ACK:<command>\n                     (command acknowledged)
 *      ERR:<message>\n                     (error report)
 *
 *    Pi → ESP32:
 *      CMD:FORWARD\n
 *      CMD:BACKWARD\n
 *      CMD:LEFT\n
 *      CMD:RIGHT\n
 *      CMD:STOP\n
 *      CMD:SPEED:<0-100>\n
 *      CMD:SCAN_START\n
 *      CMD:SCAN_STOP\n
 */

#include <Wire.h>
#include <Adafruit_VL53L1X.h>
// Using manual I2C driver for MPU6050

// ═══════════════════════════════════════════════════════════════════
//  PIN DEFINITIONS — ESP32 38-pin DevKit
// ═══════════════════════════════════════════════════════════════════

// ── I2C (shared by MPU6050 + VL53L1X) ──
#define SDA_PIN   21
#define SCL_PIN   22

// ── Motor A (Left) — L298N #1 ──
#define MOTOR_A_EN   15   // PWM enable
#define MOTOR_A_IN1  5    // Direction 1
#define MOTOR_A_IN2  19   // Direction 2

// ── Motor B (Right) — L298N #2 ──
#define MOTOR_B_EN   2    // PWM enable
#define MOTOR_B_IN1  17   // Direction 1
#define MOTOR_B_IN2  18   // Direction 2

// ── Stepper Motor (28BYJ-48 via ULN2003A) ──
#define STEPPER_IN1  27
#define STEPPER_IN2  26
#define STEPPER_IN3  25
#define STEPPER_IN4  33

// ── Encoders ──
#define ENC_L_A 36
#define ENC_L_B 39
#define ENC_R_A 34
#define ENC_R_B 35

volatile long encL_count = 0;
volatile long encR_count = 0;

void IRAM_ATTR isr_encL() {
  if (digitalRead(ENC_L_A) == digitalRead(ENC_L_B)) encL_count--;
  else encL_count++;
}

void IRAM_ATTR isr_encR() {
  if (digitalRead(ENC_R_A) == digitalRead(ENC_R_B)) encR_count++;
  else encR_count--;
}

// ── PWM Config ──
#define PWM_FREQ     1000
#define PWM_RES      8       // 8-bit resolution (0–255)
#define PWM_CH_A     0       // LEDC channel for motor A
#define PWM_CH_B     1       // LEDC channel for motor B

// ═══════════════════════════════════════════════════════════════════
//  CONSTANTS
// ═══════════════════════════════════════════════════════════════════

// 28BYJ-48: 4096 half-steps = 360°
#define STEPS_PER_REV     4096
#define SCAN_POINTS       200     // measurements per full rotation
#define STEPS_PER_POINT   (STEPS_PER_REV / SCAN_POINTS)  // ~20
#define STEPPER_DELAY_US  1200    // µs between half-steps

#define SERIAL_BAUD       115200
#define IMU_SEND_INTERVAL 100     // ms between IMU updates

// ═══════════════════════════════════════════════════════════════════
//  GLOBALS
// ═══════════════════════════════════════════════════════════════════

Adafruit_VL53L1X vl53;

// --- MPU6050 Manual Driver State ---
const float G_TO_MS2 = 9.80665;
float off_ax = 0, off_ay = 0, off_az = 0;
float off_gx = 0, off_gy = 0, off_gz = 0;
float heading = 0;

bool initMPU() {
  Wire.beginTransmission(0x68);
  Wire.write(0x6B); Wire.write(0); // Wake up
  if (Wire.endTransmission(true) != 0) return false;

  Wire.beginTransmission(0x68);
  Wire.write(0x1C); Wire.write(0x10); // Accel +-8G
  Wire.endTransmission(true);

  Wire.beginTransmission(0x68);
  Wire.write(0x1B); Wire.write(0x08); // Gyro +-500 deg/s
  Wire.endTransmission(true);
  return true;
}

void readMPU(float &ax, float &ay, float &az, float &gx, float &gy, float &gz) {
  Wire.beginTransmission(0x68);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom((uint16_t)0x68, (uint8_t)14, true);

  int16_t r_ax = Wire.read() << 8 | Wire.read();
  int16_t r_ay = Wire.read() << 8 | Wire.read();
  int16_t r_az = Wire.read() << 8 | Wire.read();
  Wire.read(); Wire.read(); // Skip Temp
  int16_t r_gx = Wire.read() << 8 | Wire.read();
  int16_t r_gy = Wire.read() << 8 | Wire.read();
  int16_t r_gz = Wire.read() << 8 | Wire.read();

  ax = (r_ax / 4096.0) * G_TO_MS2;
  ay = (r_ay / 4096.0) * G_TO_MS2;
  az = (r_az / 4096.0) * G_TO_MS2;
  gx = (r_gx / 65.5) * (PI / 180.0);
  gy = (r_gy / 65.5) * (PI / 180.0);
  gz = (r_gz / 65.5) * (PI / 180.0);
}

void calibrateMPU() {
  float sax=0, say=0, saz=0, sgx=0, sgy=0, sgz=0;
  for (int i = 0; i < 500; i++) {
    float ax, ay, az, gx, gy, gz;
    readMPU(ax, ay, az, gx, gy, gz);
    sax += ax; say += ay; saz += az;
    sgx += gx; sgy += gy; sgz += gz;
    delay(2);
  }
  off_ax = sax/500.0; off_ay = say/500.0; off_az = (saz/500.0) - G_TO_MS2;
  off_gx = sgx/500.0; off_gy = sgy/500.0; off_gz = sgz/500.0;
}

// Motor state
int  motorSpeed   = 70;    // 0–100%
bool motorsActive = false;

// Stepper state
const int stepperPins[4] = { STEPPER_IN1, STEPPER_IN2, STEPPER_IN3, STEPPER_IN4 };
int  stepPhase    = 0;
int  stepDir      = 1;     // +1 = CW, -1 = CCW
bool scanning     = false;

// Half-step sequence (8 phases)
const uint8_t HALF_STEP[8][4] = {
  {1, 0, 0, 0},
  {1, 1, 0, 0},
  {0, 1, 0, 0},
  {0, 1, 1, 0},
  {0, 0, 1, 0},
  {0, 0, 1, 1},
  {0, 0, 0, 1},
  {1, 0, 0, 1},
};

// Timing
unsigned long lastIMU = 0;

// Serial input buffer
String serialBuffer = "";

// ═══════════════════════════════════════════════════════════════════
//  SETUP
// ═══════════════════════════════════════════════════════════════════

void setup() {
  Serial.begin(SERIAL_BAUD);
  while (!Serial) { delay(10); }

  // ── I2C ──
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);  // 400kHz fast mode

  // ── Motors ──
  pinMode(MOTOR_A_IN1, OUTPUT);
  pinMode(MOTOR_A_IN2, OUTPUT);
  pinMode(MOTOR_B_IN1, OUTPUT);
  pinMode(MOTOR_B_IN2, OUTPUT);

  // PWM outputs (ESP32 Core 3.x uses analogWrite directly)
  pinMode(MOTOR_A_EN, OUTPUT);
  pinMode(MOTOR_B_EN, OUTPUT);
  stopMotors();

  // ── Stepper ──
  for (int i = 0; i < 4; i++) {
    pinMode(stepperPins[i], OUTPUT);
    digitalWrite(stepperPins[i], LOW);
  }

  // ── Encoders ──
  pinMode(ENC_L_A, INPUT);
  pinMode(ENC_L_B, INPUT);
  pinMode(ENC_R_A, INPUT);
  pinMode(ENC_R_B, INPUT);
  attachInterrupt(digitalPinToInterrupt(ENC_L_A), isr_encL, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_R_A), isr_encR, CHANGE);

  // ── VL53L1X ──
  if (!vl53.begin(0x29, &Wire)) {
    Serial.println("ERR:VL53L1X_INIT_FAILED");
  } else {
    vl53.setTimingBudget(33);
    vl53.startRanging();
    Serial.println("ACK:VL53L1X_READY");
  }

  // ── MPU6050 ──
  if (!initMPU()) {
    Serial.println("ERR:MPU6050_INIT_FAILED");
  } else {
    Serial.println("ACK:MPU6050_CALIBRATING");
    calibrateMPU();
    Serial.println("ACK:MPU6050_READY");
  }

  Serial.println("ACK:ESP32_READY");
}

// ═══════════════════════════════════════════════════════════════════
//  MAIN LOOP
// ═══════════════════════════════════════════════════════════════════

void loop() {
  // 1. Process serial commands from Pi
  processSerial();

  // 2. Run lidar scan if active
  if (scanning) {
    performScanStep();
  }

  // 3. Send IMU data periodically
  unsigned long now = millis();
  if (now - lastIMU >= IMU_SEND_INTERVAL) {
    lastIMU = now;
    sendIMUData();
  }
}

// ═══════════════════════════════════════════════════════════════════
//  SERIAL COMMAND PROCESSING
// ═══════════════════════════════════════════════════════════════════

void processSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      serialBuffer.trim();
      if (serialBuffer.length() > 0) {
        handleCommand(serialBuffer);
        serialBuffer = "";
      }
    } else {
      serialBuffer += c;
    }
  }
}

void handleCommand(String cmd) {
  if (cmd == "CMD:FORWARD") {
    moveForward();
    Serial.println("ACK:FORWARD");
  }
  else if (cmd == "CMD:BACKWARD") {
    moveBackward();
    Serial.println("ACK:BACKWARD");
  }
  else if (cmd == "CMD:LEFT") {
    turnLeft();
    Serial.println("ACK:LEFT");
  }
  else if (cmd == "CMD:RIGHT") {
    turnRight();
    Serial.println("ACK:RIGHT");
  }
  else if (cmd == "CMD:STOP") {
    stopMotors();
    Serial.println("ACK:STOP");
  }
  else if (cmd.startsWith("CMD:SPEED:")) {
    int spd = cmd.substring(10).toInt();
    motorSpeed = constrain(spd, 0, 100);
    Serial.print("ACK:SPEED:");
    Serial.println(motorSpeed);
  }
  else if (cmd == "CMD:SCAN_START") {
    scanning = true;
    stepDir = 1;
    Serial.println("ACK:SCAN_START");
  }
  else if (cmd == "CMD:SCAN_STOP") {
    scanning = false;
    stepperOff();
    Serial.println("ACK:SCAN_STOP");
  }
  else if (cmd == "CMD:PING") {
    Serial.println("ACK:PONG");
  }
  else {
    Serial.print("ERR:UNKNOWN_CMD:");
    Serial.println(cmd);
  }
}

// ═══════════════════════════════════════════════════════════════════
//  MOTOR CONTROL
// ═══════════════════════════════════════════════════════════════════

uint8_t speedToPWM(int pct) {
  return (uint8_t)map(constrain(pct, 0, 100), 0, 100, 0, 255);
}

void setMotorA(bool in1, bool in2) {
  digitalWrite(MOTOR_A_IN1, in1);
  digitalWrite(MOTOR_A_IN2, in2);
}

void setMotorB(bool in1, bool in2) {
  digitalWrite(MOTOR_B_IN1, in1);
  digitalWrite(MOTOR_B_IN2, in2);
}

void engageMotors() {
  uint8_t pwm = speedToPWM(motorSpeed);
  analogWrite(MOTOR_A_EN, pwm);
  analogWrite(MOTOR_B_EN, pwm);
  motorsActive = true;
}

void moveForward() {
  setMotorA(LOW, HIGH);
  setMotorB(LOW, HIGH);
  engageMotors();
}

void moveBackward() {
  setMotorA(HIGH, LOW);
  setMotorB(HIGH, LOW);
  engageMotors();
}

void turnLeft() {
  setMotorA(HIGH, LOW);    // left backward
  setMotorB(LOW, HIGH);    // right forward
  engageMotors();
}

void turnRight() {
  setMotorA(LOW, HIGH);    // left forward
  setMotorB(HIGH, LOW);    // right backward
  engageMotors();
}

void stopMotors() {
  analogWrite(MOTOR_A_EN, 0);
  analogWrite(MOTOR_B_EN, 0);
  setMotorA(LOW, LOW);
  setMotorB(LOW, LOW);
  motorsActive = false;
}

// ═══════════════════════════════════════════════════════════════════
//  STEPPER MOTOR (28BYJ-48 via ULN2003A)
// ═══════════════════════════════════════════════════════════════════

void stepMotor() {
  stepPhase = (stepPhase + stepDir + 8) % 8;
  for (int i = 0; i < 4; i++) {
    digitalWrite(stepperPins[i], HALF_STEP[stepPhase][i]);
  }
  delayMicroseconds(STEPPER_DELAY_US);
}

void stepperOff() {
  for (int i = 0; i < 4; i++) {
    digitalWrite(stepperPins[i], LOW);
  }
}

// ═══════════════════════════════════════════════════════════════════
//  LIDAR SCANNING
// ═══════════════════════════════════════════════════════════════════

// Scan state
static int scanPointIndex = 0;

void performScanStep() {
  // Move stepper to next measurement position
  for (int s = 0; s < STEPS_PER_POINT; s++) {
    stepMotor();
  }

  // Read distance
  uint16_t dist = 0;
  while (!vl53.dataReady()) {
    delay(1);
  }
  dist = vl53.distance();
  vl53.clearInterrupt();

  // Calculate angle
  float angle = scanPointIndex * (360.0 / SCAN_POINTS);

  // Send scan point to Pi
  Serial.print("SCAN:");
  Serial.print(angle, 1);
  Serial.print(",");
  Serial.println(dist);

  scanPointIndex++;

  // Full rotation complete
  if (scanPointIndex >= SCAN_POINTS) {
    scanPointIndex = 0;
    stepDir *= -1;  // reverse direction
    Serial.println("SCAN_DONE");
  }
}

// ═══════════════════════════════════════════════════════════════════
//  IMU (MPU6050)
// ═══════════════════════════════════════════════════════════════════

void sendIMUData() {
  float raw_ax, raw_ay, raw_az, raw_gx, raw_gy, raw_gz;
  readMPU(raw_ax, raw_ay, raw_az, raw_gx, raw_gy, raw_gz);

  float ax = raw_ax - off_ax;
  float ay = raw_ay - off_ay;
  float az = raw_az - off_az;
  float gx = raw_gx - off_gx;
  float gy = raw_gy - off_gy;
  float gz = raw_gz - off_gz;

  // Thresholds to kill static noise
  if (abs(ax) < 0.12) ax = 0; 
  if (abs(ay) < 0.12) ay = 0;
  if (abs(gz) < 0.01) gz = 0;

  static unsigned long last_mpu_time = 0;
  unsigned long now = micros();
  if (last_mpu_time == 0) last_mpu_time = now;
  float dt = (now - last_mpu_time) / 1000000.0;
  last_mpu_time = now;
  if (dt <= 0 || dt > 0.5) dt = 0.1;

  heading += gz * dt; // integrate Z rotation to get yaw

  // Format: IMU:<ax>,<ay>,<az>,<gx>,<gy>,<gz>,<yaw>
  Serial.print("IMU:");
  Serial.print(ax, 2);  Serial.print(",");
  Serial.print(ay, 2);  Serial.print(",");
  Serial.print(az, 2);  Serial.print(",");
  Serial.print(gx, 1);  Serial.print(",");
  Serial.print(gy, 1);  Serial.print(",");
  Serial.print(gz, 1);  Serial.print(",");
  Serial.println(degrees(heading), 1);  // yaw

  // Send Encoders
  long currentEncL = encL_count;
  long currentEncR = encR_count;
  encL_count = 0;
  encR_count = 0;
  Serial.print("ENC:");
  Serial.print(currentEncL); Serial.print(",");
  Serial.println(currentEncR);
}
