/*
  STEP / DIR control — NO library
  FULL STEP motor (200 steps/rev)

  Commands:
    dir_forward
    dir_backward
    setSpeed <steps_per_sec>
    stop
    inject
*/

const int dirPin  = 2;
const int stepPin = 3;

// =========================
// FULL STEP CONVERSION
// =========================
const float STEPS_PER_REV = 200.0;
const float STEPS_TO_DEG  = 360.0 / STEPS_PER_REV; // 1.8° / step

// =========================
// SERIAL
// =========================
String input = "";

// =========================
// SPEED ENGINE
// =========================
float current_sps = 0.0;   // steps per second (signed)
int direction = 1;

// timing
unsigned long step_interval_us = 0;
unsigned long last_step_us = 0;

// pulse width (safe for DRV8825)
const unsigned int STEP_PULSE_US = 5;

// =========================
// INJECTION PROFILE
// =========================
const int N = 3;

float profil_sps[N] = {
  -1500.0,   // inject
    500.0,   // retract
      0.0
};

unsigned int profil_dt[N] = { 200, 200, 200 };

bool executing_profile = false;
int prof_i = 0;
unsigned long prof_t0 = 0;
unsigned long prof_all0 = 0;

// =========================
// SPEED SETTER (NO LIMIT)
// =========================
void setSpeedSPS(float sps) {

  current_sps = sps;

  if (sps > 0.0) {
    digitalWrite(dirPin, HIGH);
    step_interval_us = (unsigned long)(1000000.0 / sps);
  }
  else if (sps < 0.0) {
    digitalWrite(dirPin, LOW);
    step_interval_us = (unsigned long)(1000000.0 / (-sps));
  }
  else {
    step_interval_us = 0;
  }

  last_step_us = micros();
}

// =========================
// STEP PULSE ENGINE
// =========================
void stepUpdate() {
  if (step_interval_us == 0) return;

  unsigned long now = micros();
  if (now - last_step_us >= step_interval_us) {
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(STEP_PULSE_US);
    digitalWrite(stepPin, LOW);
    last_step_us += step_interval_us;
  }
}

// =========================
// PROFILE CONTROL
// =========================
void startInject() {
  executing_profile = true;
  prof_i = 0;
  prof_t0 = millis();
  prof_all0 = prof_t0;

  Serial.println("t_ms,target_speed_deg");

  setSpeedSPS(profil_sps[0]);
}

void profileUpdate() {
  if (!executing_profile) return;

  unsigned long now = millis();
  if (now - prof_t0 >= profil_dt[prof_i]) {

    prof_i++;
    if (prof_i >= N) {
      executing_profile = false;
      setSpeedSPS(0);
      Serial.println("CSV_END");
      return;
    }

    prof_t0 = now;
    setSpeedSPS(profil_sps[prof_i]);

    unsigned long t_ms = now - prof_all0;
    Serial.print(t_ms);
    Serial.print(",");
    Serial.println(profil_sps[prof_i] * STEPS_TO_DEG);
  }
}

// =========================
// SERIAL COMMANDS
// =========================
void processCommand(String cmd) {
  cmd.trim();

  if (cmd == "dir_forward") {
    direction = 1;
    Serial.println("DIR=forward");
  }
  else if (cmd == "dir_backward") {
    direction = -1;
    Serial.println("DIR=backward");
  }
  else if (cmd.startsWith("setSpeed")) {
    float v = cmd.substring(8).toFloat();
    executing_profile = false;
    setSpeedSPS(direction * v);
    Serial.println("SPEED_SET");
  }
  else if (cmd == "stop") {
    executing_profile = false;
    setSpeedSPS(0);
    Serial.println("STOP");
  }
  else if (cmd == "inject") {
    startInject();
    Serial.println("▶ inject");
  }
  else {
    Serial.println("ERR");
  }
}

// =========================
// SETUP / LOOP
// =========================
void setup() {
  Serial.begin(115200);

  pinMode(dirPin, OUTPUT);
  pinMode(stepPin, OUTPUT);

  digitalWrite(stepPin, LOW);
  digitalWrite(dirPin, HIGH);

  Serial.println("READY_STEP_DIR_FULL_STEP_NO_LIMIT");
}

void loop() {

  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (input.length()) processCommand(input);
      input = "";
    } else {
      input += c;
    }
  }

  profileUpdate();
  stepUpdate();
}
