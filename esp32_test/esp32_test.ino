#include <BluetoothSerial.h>
#include <Adafruit_VL53L1X.h>
#include <Wire.h>

// --- PIN DEFINITIONS ---
#define in1 5
#define in2 19
#define in3 17
#define in4 18
#define en1 15
#define en2 2

#define IN1 27
#define IN2 26
#define IN3 25
#define IN4 33

// --- ENCODER PINS ---
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

// --- CONSTANTS ---
#define STEPS_PER_REV 4096 
#define STEP_DELAY_US 1200 
const float G_TO_MS2 = 9.80665;

const bool SEQ[8][4] = {
  {1,0,0,0},{1,1,0,0},{0,1,0,0},{0,1,1,0},
  {0,0,1,0},{0,0,1,1},{0,0,0,1},{1,0,0,1}
};

// --- STATE VARIABLES ---
float state[4] = {0, 0, 0, 0}; // x, y, vx, vy
float heading = 0;
unsigned long lastTime = 0;
bool mpuEnabled = false;
int16_t latest_distance = -1;

// Calibration Offsets
float off_ax = 0, off_ay = 0, off_az = 0;
float off_gx = 0, off_gy = 0, off_gz = 0;

// Stepper State
int stepIdx = 0;
int stepperDir = 1;
int stepsTaken = 0;
unsigned long lastStepTime = 0;

Adafruit_VL53L1X vl53;
BluetoothSerial serialBt;

// --- MOTOR CONTROL ---
void setMotors(int p1, int p2, int p3, int p4) {
  digitalWrite(in1, p1); digitalWrite(in2, p2);
  digitalWrite(in3, p3); digitalWrite(in4, p4);
}

// --- STEPPER LOGIC (Non-blocking) ---
void updateStepper() {
  if (micros() - lastStepTime >= STEP_DELAY_US) {
    lastStepTime = micros();
    stepIdx = (stepIdx + stepperDir + 8) % 8;
    digitalWrite(IN1, SEQ[stepIdx][0]);
    digitalWrite(IN2, SEQ[stepIdx][1]);
    digitalWrite(IN3, SEQ[stepIdx][2]);
    digitalWrite(IN4, SEQ[stepIdx][3]);
    stepsTaken++;
    if (stepsTaken >= STEPS_PER_REV) {
      stepsTaken = 0;
      stepperDir = -stepperDir; 
    }
  }
}

// --- MPU6050 MANUAL DRIVER ---
bool initMPU() {
  Wire.beginTransmission(0x68);
  Wire.write(0x6B); Wire.write(0); // Wake up
  if (Wire.endTransmission(true) != 0) return false;

  Wire.beginTransmission(0x68);
  Wire.write(0x1C); Wire.write(0x10); // Accel +-8G (4096 LSB/g)
  Wire.endTransmission(true);

  Wire.beginTransmission(0x68);
  Wire.write(0x1B); Wire.write(0x08); // Gyro +-500 deg/s (65.5 LSB/deg/s)
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
  Serial.println(F("Calibrating... DO NOT MOVE"));
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
  Serial.println(F("Calibration Done."));
}

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  Wire.setClock(400000);

  int p[] = {in1, in2, in3, in4, en1, en2, IN1, IN2, IN3, IN4};
  for(int i=0; i<10; i++) pinMode(p[i], OUTPUT);
  digitalWrite(en1, HIGH); digitalWrite(en2, HIGH); // 100% Max speed

  // Setup encoder pins as inputs (34, 35, 36, 39 are input-only on ESP32, no internal pullups)
  pinMode(ENC_L_A, INPUT);
  pinMode(ENC_L_B, INPUT);
  pinMode(ENC_R_A, INPUT);
  pinMode(ENC_R_B, INPUT);
  
  // Attach interrupts for magnetic encoders
  attachInterrupt(digitalPinToInterrupt(ENC_L_A), isr_encL, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_R_A), isr_encR, CHANGE);

  // Set motors to spin continuously forward (polarity reversed)
  setMotors(0, 1, 0, 1);

  if (vl53.begin(0x29, &Wire)) {
    vl53.setTimingBudget(33);
    vl53.startRanging();
  }

  if (initMPU()) {
    mpuEnabled = true;
    calibrateMPU();
  }

  serialBt.begin("wheelchair_esp32");
  lastTime = micros();
}

void loop() {
  updateStepper();

  if (vl53.dataReady()) {
    latest_distance = vl53.distance();
    vl53.clearInterrupt();
  }

  if (mpuEnabled) {
    float raw_ax, raw_ay, raw_az, raw_gx, raw_gy, raw_gz;
    readMPU(raw_ax, raw_ay, raw_az, raw_gx, raw_gy, raw_gz);

    unsigned long now = micros();
    float dt = (now - lastTime) / 1000000.0;
    lastTime = now;
    if (dt <= 0 || dt > 0.1) dt = 0.01;

    // 1. Apply Calibration and threshold
    float ax = raw_ax - off_ax;
    float ay = raw_ay - off_ay;
    float gz = raw_gz - off_gz;

    if (abs(ax) < 0.12) ax = 0; 
    if (abs(ay) < 0.12) ay = 0;
    if (abs(gz) < 0.01) gz = 0;

    // 2. Update Orientation
    heading += gz * dt;

    // 3. Transform to World Frame
    float world_ax = ax * cos(heading) - ay * sin(heading);
    float world_ay = ax * sin(heading) + ay * cos(heading);

    // 4. Integrated Velocity & Position
    // Increased ZUPT sensitivity to avoid freezing at non-zero
    if (abs(ax) < 0.05 && abs(ay) < 0.05 && abs(gz) < 0.01) {
      state[2] = 0; state[3] = 0; // Stationary reset
    } else {
      state[2] += world_ax * dt;
      state[3] += world_ay * dt;
      state[2] *= 0.97; // Slightly stronger damping
      state[3] *= 0.97;
    }

    state[0] += state[2] * dt;
    state[1] += state[3] * dt;
  }

  // Motors spin continuously. Ignore BT commands that stop it.
  if (serialBt.available()) {
    char cmd = serialBt.read();
    // Do nothing with cmd
  }

  static unsigned long lastPrint = 0;
  if (millis() - lastPrint > 200) {
    // Read encoder counts safely and reset them to get speed/delta
    long currentEncL = encL_count;
    long currentEncR = encR_count;
    encL_count = 0;
    encR_count = 0;
    
    Serial.print("X:"); Serial.print(state[0], 3);
    Serial.print(" Y:"); Serial.print(state[1], 3);
    Serial.print(" VX:"); Serial.print(state[2], 3);
    Serial.print(" H:"); Serial.print(degrees(heading), 1);
    Serial.print(" EncL:"); Serial.print(currentEncL);
    Serial.print(" EncR:"); Serial.print(currentEncR);
    Serial.print(" Dist:"); Serial.println(latest_distance);
    lastPrint = millis();
  }
}
