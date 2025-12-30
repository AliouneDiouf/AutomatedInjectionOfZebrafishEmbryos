#include <AccelStepper.h>

// === PINS AXE X ===
const int dirPin  = 4;
const int stepPin = 2;
const int enPin   = 8;

AccelStepper stepper(AccelStepper::DRIVER, stepPin, dirPin);

// === PINS AXE Y ===
const int dirPinY  = 7;
const int stepPinY = 6;
const int enPinY   = 9;

AccelStepper stepperY(AccelStepper::DRIVER, stepPinY, dirPinY);

String serialCommand = "";
bool isRunning  = false;
bool isRunningY = false;

void setup() {
  Serial.begin(115200);

  pinMode(enPin, OUTPUT);
  pinMode(enPinY, OUTPUT);
  digitalWrite(enPin, LOW);
  digitalWrite(enPinY, LOW);

  stepper.setMaxSpeed(1000);
  stepper.setAcceleration(2000);
  stepper.setSpeed(1000);

  stepperY.setMaxSpeed(1000);
  stepperY.setAcceleration(2000);
  stepperY.setSpeed(1000);
}

void loop() {

  // ======================
  // SERIAL PARSING
  // ======================
  if (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n') {
      serialCommand.trim();

      // ======================
      // 🆕 AXE Y (DOIT ÊTRE AVANT adj)
      // ======================
      if (serialCommand.startsWith("adjY")) {
        int steps = serialCommand.substring(5).toInt();
        stepperY.move(steps);
        isRunningY = true;
      }

      else if (serialCommand == "nextY") {
        stepperY.move(500);
        isRunningY = true;
      }

      else if (serialCommand == "prevY") {
        stepperY.move(-500);
        isRunningY = true;
      }

      // ======================
      // AXE X (EXISTANT)
      // ======================
      else if (serialCommand == "next") {
        stepper.move(-500);
        isRunning = true;
      }

      else if (serialCommand == "prev") {
        stepper.move(500);
        isRunning = true;
      }

      else if (serialCommand.startsWith("adj")) {
        int steps = serialCommand.substring(4).toInt();
        stepper.move(steps);
        isRunning = true;
      }

      else if (serialCommand == "stop") {
        stepper.stop();
        stepperY.stop();
        isRunning  = false;
        isRunningY = false;
      }

      serialCommand = "";
    }
    else {
      serialCommand += c;
    }
  }

  // ======================
  // RUN MOTORS
  // ======================
  if (isRunning) {
    stepper.run();
    if (stepper.distanceToGo() == 0)
      isRunning = false;
  }

  if (isRunningY) {
    stepperY.run();
    if (stepperY.distanceToGo() == 0)
      isRunningY = false;
  }
}
