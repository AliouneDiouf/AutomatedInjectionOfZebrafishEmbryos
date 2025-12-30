#include <AccelStepper.h>
#include <Wire.h>
#include <AS5600.h>

// =========================
// HARDWARE
// =========================
const int dirPin = 3;
const int stepPin = 4;
const int enPin = 5;

AccelStepper stepper(AccelStepper::DRIVER, stepPin, dirPin);
AS5600 encoder;

// =========================
// GLOBALS
// =========================
String input = "";
bool executing_profile = false;
int direction = 1;

long tour = 0;
int last_raw = 0;

float pos_deg = 0;
float last_pos_deg = 0;
float actual_speed_deg = 0;   // vitesse mesurée en deg/s
unsigned long lastT = 0;

// =========================
// CONVERSION
// =========================
const float STEPS_PER_REV = 3200.0;
const float STEPS_TO_DEG  = 360.0 / STEPS_PER_REV;
const float DEG_TO_STEPS  = STEPS_PER_REV / 360.0;

// =========================
// PROFIL COURT 4 POINTS (inject)
// =========================
const int N = 4;

float profil_steps_s[N] = {
   -300.0,   // P1
   -2000.0,   // P2
    300.0,   // P3
      0.0    // P4
};

unsigned int profil_dt[N] = {
  100,   // ms
  300,
  200,
  200
};

// =========================
// AS5600 UPDATE
// =========================
void updateAS5600() {

  int raw = encoder.readAngle();
  int d = raw - last_raw;

  if (d > 2048)      tour--;
  else if (d < -2048) tour++;

  unsigned long now = millis();
  float dt = (now - lastT) / 1000.0;
  if (dt < 0.0001) dt = 0.0001;

  pos_deg = tour * 360.0 + (raw * 360.0 / 4096.0);

  actual_speed_deg = (pos_deg - last_pos_deg) / dt;

  last_pos_deg = pos_deg;
  last_raw = raw;
  lastT = now;
}

// =========================
// PLAY INJECTION PROFILE 4
// =========================
void playProfile4() {

  Serial.println("t_ms,target_speed_deg,actual_speed_deg");

  executing_profile = true;
  unsigned long t0_all = millis();

  for (int i = 0; i < N; i++) {

    float target_steps = profil_steps_s[i];

    if (target_steps > 800)  target_steps = 800;
    if (target_steps < -800) target_steps = -800;

    float target_speed_deg = target_steps * STEPS_TO_DEG;

    stepper.setSpeed(target_steps);

    unsigned long t0 = millis();
    while (millis() - t0 < profil_dt[i]) {

      stepper.runSpeed();
      updateAS5600();

      unsigned long t_ms = millis() - t0_all;

      Serial.print(t_ms);             Serial.print(",");
      Serial.print(target_speed_deg); Serial.print(",");
      Serial.println(actual_speed_deg);
    }
  }

  executing_profile = false;
  stepper.setSpeed(0);
  Serial.println("CSV_END");
}

// =========================
// SERIAL COMMANDS
// =========================
void processCommand(String cmd) {
  cmd.trim();

  // -----------------------
  // Motor direction
  // -----------------------
  if (cmd == "dir_forward") {
    direction = 1;
    Serial.println("DIR=forward");
  }

  else if (cmd == "dir_backward") {
    direction = -1;
    Serial.println("DIR=backward");
  }

  // -----------------------
  // Speed control
  // -----------------------
  else if (cmd.startsWith("setSpeed")) {
    float v = cmd.substring(9).toFloat();
    stepper.setSpeed(direction * v);
    Serial.print("SPEED=");
    Serial.println(direction * v);
  }

  // -----------------------
  // Start / Stop profile
  // -----------------------
  else if (cmd == "start_profile") {
    executing_profile = true;
    stepper.setCurrentPosition(0);
    Serial.println("▶ start_profile");
  }

  else if (cmd == "end_profile") {
    executing_profile = false;
    stepper.stop();
    Serial.println("✔ end_profile");
  }

  // -----------------------
  // Injection command → new short profile
  // -----------------------
  else if (cmd == "inject") {
    playProfile4();
  }

  // -----------------------
  // AS5600 position request
  // -----------------------
  else if (cmd == "AS_POS") {
    Serial.print("POS=");
    Serial.println(pos_deg, 3);
  }

  // -----------------------
  // Unknown command
  // -----------------------
  else {
    Serial.println("ERR,UNKNOWN_CMD");
  }
}

// =========================
// SETUP
// =========================
void setup() {
  Serial.begin(115200);
  Wire.begin();

  pinMode(enPin, OUTPUT);
  digitalWrite(enPin, LOW);

  stepper.setMaxSpeed(800);

  encoder.begin();
  last_raw = encoder.readAngle();
  pos_deg = (last_raw * 360.0) / 4096.0;
  last_pos_deg = pos_deg;
  lastT = millis();

  Serial.println("READY_PROFILE4_FULL_COMMANDS");
}

// =========================
// LOOP
// =========================
void loop() {

  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      processCommand(input);
      input = "";
    } 
    else input += c;
  }

  if (executing_profile)
    stepper.runSpeed();

  updateAS5600();
}
