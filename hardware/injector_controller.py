# hardware/injector_controller.py

import serial
import time


class InjectorController:
    def __init__(self, port, baudrate=115200):
        self.port = serial.Serial(port, baudrate, timeout=1)
        time.sleep(1.0)

        # sécurité
        self.send_safe("setSpeed 0")
        self.send_safe("end_profile")

    # -----------------------------
    # LOW LEVEL
    # -----------------------------
    def send_safe(self, cmd: str, delay: float = 0.05):
        try:
            self.port.write((cmd + "\n").encode("utf-8"))
            self.port.flush()
            time.sleep(delay)
        except Exception as e:
            print(f"[INJECT ERROR] {e}")

    # -----------------------------
    # MANUAL CONTROL
    # -----------------------------
    def start_profile(self):
        self.send_safe("start_profile")

    def stop_profile(self):
        self.send_safe("setSpeed 0")
        self.send_safe("end_profile")

    def set_speed(self, speed: float):
        self.send_safe(f"setSpeed {speed}")

    def dir_forward(self):
        self.send_safe("dir_forward")

    def dir_backward(self):
        self.send_safe("dir_backward")

    # -----------------------------
    # SENSOR READ (AS5600)
    # -----------------------------
    def read_angle_deg(self, timeout=0.2):
        try:
            self.port.reset_input_buffer()
            self.port.write(b"AS_POS\n")
            time.sleep(0.02)

            t0 = time.time()
            while time.time() - t0 < timeout:
                line = self.port.readline().decode(errors="ignore").strip()
                if line.startswith("POS="):
                    return float(line.split("=", 1)[1])
            return None

        except Exception as e:
            print(f"[AS5600 ERROR] {e}")
            return None

    # -----------------------------
    # RETREAT TO HOME
    # -----------------------------
    def retreat_to_home(self, home_angle, epsilon=2.0, speed=300, max_time=6.0):
        if home_angle is None:
            print("[INJECT] Home angle undefined")
            return False

        self.start_profile()
        self.dir_forward()
        self.set_speed(speed)

        t0 = time.time()
        while time.time() - t0 < max_time:
            angle = self.read_angle_deg()
            if angle is None:
                continue
            if abs(angle - home_angle) <= epsilon:
                break

        self.stop_profile()
        return True

    def close(self):
        try:
            self.stop_profile()
            self.port.close()
        except Exception:
            pass
