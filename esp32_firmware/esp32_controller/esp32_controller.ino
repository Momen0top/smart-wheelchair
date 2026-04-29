/*
 * ═══════════════════════════════════════════════════════════════════
 *  SMART WHEELCHAIR — FINAL PRODUCTION FIRMWARE (v3.2)
 * ═══════════════════════════════════════════════════════════════════
 * 
 *  Changes:
 *    - Robust setup: tasks start immediately so D-pad works even if sensors fail.
 *    - Non-blocking I2C checks for IMU and Lidar.
 */

#include <Wire.h>
#include <Adafruit_VL53L1X.h>

#define SDA_PIN 21
#define SCL_PIN 22
#define MOTOR_A_EN 15, MOTOR_A_IN1 5, MOTOR_A_IN2 19
#define MOTOR_B_EN 2, MOTOR_B_IN1 17, MOTOR_B_IN2 18
#define STEPPER_IN1 27, STEPPER_IN2 26, STEPPER_IN3 25, STEPPER_IN4 33
#define ENC_L_A 36, ENC_L_B 39, ENC_R_A 34, ENC_R_B 35
#define IMU_ADDR 0x68

Adafruit_VL53L1X vl53;
SemaphoreHandle_t serialMutex;
volatile bool scanning = false;
volatile int motorSpeed = 70;
enum MotorState { STOP, FORWARD, BACKWARD, LEFT, RIGHT };
volatile MotorState currentMotorState = STOP;
volatile long encL = 0, encR = 0;
float off_ax=0, off_ay=0, off_az=0, off_gx=0, off_gy=0, off_gz=0, yaw=0;
bool imu_ready = false, lidar_ready = false;

void IRAM_ATTR isrL() { if (digitalRead(36) == digitalRead(39)) encL--; else encL++; }
void IRAM_ATTR isrR() { if (digitalRead(34) == digitalRead(35)) encR++; else encR--; }

void applyMotorHardware() {
    uint8_t pwm = (uint8_t)map(motorSpeed, 0, 100, 0, 255);
    int a1=5, a2=19, ae=15, b1=17, b2=18, be=2; // Pins
    if(currentMotorState==FORWARD){ digitalWrite(a1,0); digitalWrite(a2,1); digitalWrite(b1,0); digitalWrite(b2,1); }
    else if(currentMotorState==BACKWARD){ digitalWrite(a1,1); digitalWrite(a2,0); digitalWrite(b1,1); digitalWrite(b2,0); }
    else if(currentMotorState==LEFT){ digitalWrite(a1,1); digitalWrite(a2,0); digitalWrite(b1,0); digitalWrite(b2,1); }
    else if(currentMotorState==RIGHT){ digitalWrite(a1,0); digitalWrite(a2,1); digitalWrite(b1,1); digitalWrite(b2,0); }
    else { digitalWrite(a1,0); digitalWrite(a2,0); digitalWrite(b1,0); digitalWrite(b2,0); pwm=0; }
    analogWrite(ae, pwm); analogWrite(be, pwm);
}

void handleCommand(String cmd) {
    if(cmd=="CMD:FORWARD") currentMotorState=FORWARD; else if(cmd=="CMD:BACKWARD") currentMotorState=BACKWARD;
    else if(cmd=="CMD:LEFT") currentMotorState=LEFT; else if(cmd=="CMD:RIGHT") currentMotorState=RIGHT;
    else if(cmd=="CMD:STOP") currentMotorState=STOP; else if(cmd=="CMD:SCAN_START") scanning=true;
    else if(cmd=="CMD:SCAN_STOP") scanning=false; else if(cmd.startsWith("CMD:SPEED:")) motorSpeed=constrain(cmd.substring(10).toInt(),0,100);
    applyMotorHardware();
    xSemaphoreTake(serialMutex, portMAX_DELAY); Serial.print("ACK:"); Serial.println(cmd.substring(4)); xSemaphoreGive(serialMutex);
}

void readMPU(float &ax, float &ay, float &az, float &gx, float &gy, float &gz) {
    Wire.beginTransmission(IMU_ADDR); Wire.write(0x3B); if(Wire.endTransmission(false)!=0) return;
    Wire.requestFrom((uint16_t)IMU_ADDR, (uint8_t)14, true);
    if(Wire.available()<14) return;
    int16_t r_ax = Wire.read()<<8|Wire.read(); int16_t r_ay = Wire.read()<<8|Wire.read(); int16_t r_az = Wire.read()<<8|Wire.read();
    Wire.read(); Wire.read();
    int16_t r_gx = Wire.read()<<8|Wire.read(); int16_t r_gy = Wire.read()<<8|Wire.read(); int16_t r_gz = Wire.read()<<8|Wire.read();
    ax = r_ax/4096.0; ay = r_ay/4096.0; az = r_az/4096.0; gx = (r_gx/65.5)*(PI/180.0); gy = (r_gy/65.5)*(PI/180.0); gz = (r_gz/65.5)*(PI/180.0);
}

void serialTask(void *p) {
    String buf = "";
    while(1) {
        while(Serial.available()){ char c=Serial.read(); if(c=='\n'){ buf.trim(); handleCommand(buf); buf=""; } else buf+=c; }
        vTaskDelay(5/portTICK_PERIOD_MS);
    }
}

void hardwareTask(void *p) {
    const uint8_t HS[8][4] = {{1,0,0,0},{1,1,0,0},{0,1,0,0},{0,1,1,0},{0,0,1,0},{0,0,1,1},{0,0,0,1},{1,0,0,1}};
    int phase=0, idx=0, dir=1;
    while(1) {
        if(scanning && lidar_ready) {
            for(int i=0; i<20; i++){ // STEPS_PER_POINT
                phase=(phase+dir+8)%8;
                digitalWrite(27, HS[phase][0]); digitalWrite(26, HS[phase][1]); digitalWrite(25, HS[phase][2]); digitalWrite(33, HS[phase][3]);
                delayMicroseconds(1200);
            }
            uint32_t t=millis()+50; while(!vl53.dataReady() && millis()<t) vTaskDelay(1);
            if(vl53.dataReady()){
                uint16_t d=vl53.distance(); vl53.clearInterrupt();
                xSemaphoreTake(serialMutex, portMAX_DELAY); Serial.print("SCAN:"); Serial.print(idx*(360.0/200),1); Serial.print(","); Serial.println(d); xSemaphoreGive(serialMutex);
            }
            if(++idx >= 200){ idx=0; dir*=-1; xSemaphoreTake(serialMutex, portMAX_DELAY); Serial.println("SCAN_DONE"); xSemaphoreGive(serialMutex); }
        } else vTaskDelay(50/portTICK_PERIOD_MS);
    }
}

void telemetryTask(void *p) {
    uint32_t last = micros();
    while(1) {
        if(imu_ready){
            float ax,ay,az,gx,gy,gz; readMPU(ax,ay,az,gx,gy,gz);
            uint32_t now = micros(); float dt = (now-last)/1000000.0; last=now;
            yaw += (gz - off_gz)*dt;
            xSemaphoreTake(serialMutex, portMAX_DELAY);
            Serial.print("IMU:"); Serial.print(ax-off_ax,2); Serial.print(","); Serial.print(ay-off_ay,2); Serial.print(","); Serial.print(az-off_az,2); Serial.print(","); 
            Serial.print(gx-off_gx,2); Serial.print(","); Serial.print(gy-off_gy,2); Serial.print(","); Serial.print(gz-off_gz,2); Serial.print(","); Serial.println(degrees(yaw),1);
            xSemaphoreGive(serialMutex);
        }
        long l=encL; long r=encR; encL=0; encR=0;
        xSemaphoreTake(serialMutex, portMAX_DELAY); Serial.print("ENC:"); Serial.print(l); Serial.print(","); Serial.println(r); xSemaphoreGive(serialMutex);
        vTaskDelay(100/portTICK_PERIOD_MS);
    }
}

void setup() {
    Serial.begin(115200); serialMutex = xSemaphoreCreateMutex();
    Wire.begin(SDA_PIN, SCL_PIN); Wire.setClock(400000);
    pinMode(5, OUTPUT); pinMode(19, OUTPUT); pinMode(15, OUTPUT); pinMode(17, OUTPUT); pinMode(18, OUTPUT); pinMode(2, OUTPUT);
    pinMode(27, OUTPUT); pinMode(26, OUTPUT); pinMode(25, OUTPUT); pinMode(33, OUTPUT);
    pinMode(36, INPUT); pinMode(39, INPUT); pinMode(34, INPUT); pinMode(35, INPUT);
    attachInterrupt(36, isrL, CHANGE); attachInterrupt(34, isrR, CHANGE);

    // Start tasks IMMEDIATELY so D-pad works no matter what
    xTaskCreatePinnedToCore(serialTask, "Ser", 4096, NULL, 3, NULL, 0);
    xTaskCreatePinnedToCore(hardwareTask, "Hw", 4096, NULL, 2, NULL, 1);
    xTaskCreatePinnedToCore(telemetryTask, "Tel", 4096, NULL, 1, NULL, 1);

    // Non-blocking Sensor Init
    Wire.beginTransmission(IMU_ADDR); if(Wire.endTransmission()==0){
        Wire.beginTransmission(IMU_ADDR); Wire.write(0x6B); Wire.write(0); Wire.endTransmission(true);
        imu_ready = true;
        for(int i=0; i<50; i++){ float a,b,c,d,e,f; readMPU(a,b,c,d,e,f); off_ax+=a; off_ay+=b; off_az+=c; off_gx+=d; off_gy+=e; off_gz+=f; delay(2); }
        off_ax/=50.0; off_ay/=50.0; off_az=(off_az/50.0)-1.0; off_gx/=50.0; off_gy/=50.0; off_gz/=50.0;
    }
    if(vl53.begin(0x29, &Wire)){ vl53.setTimingBudget(33); vl53.startRanging(); lidar_ready = true; }
    
    Serial.println("ACK:BOOT_COMPLETE");
}
void loop() { vTaskDelay(1000); }
