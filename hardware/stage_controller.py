import serial
import threading
import time


class StageController:
    def __init__(self, port, baudrate=115200, move_interval=0.4):
        self.port = serial.Serial(port, baudrate, timeout=1)
        time.sleep(1.0)

        self.lock = threading.Lock()

        # 🔥 États séparés X / Y
        self.moving_x = False
        self.moving_y = False
        self.last_move_ts_x = 0.0
        self.last_move_ts_y = 0.0

        self.move_interval = move_interval

    # =====================
    # LOW LEVEL
    # =====================
    def send(self, cmd: str):
        try:
            self.port.write((cmd + "\n").encode("utf-8"))
            self.port.flush()
        except Exception as e:
            print(f"[STAGE ERROR] {e}")

    # =====================
    # AXE X
    # =====================
    def move_left(self, steps: int):
        self.send(f"adj -{steps}")

    def move_right(self, steps: int):
        self.send(f"adj {steps}")

    # =====================
    # AXE Y
    # =====================
    def move_up(self, steps: int):
        self.send(f"adjY {steps}")

    def move_down(self, steps: int):
        self.send(f"adjY -{steps}")

    # =====================
    # COMBINÉ
    # =====================
    def move(self, dx=0, dy=0):
        if dx != 0:
            self.send(f"adj {dx}")
        if dy != 0:
            self.send(f"adjY {dy}")

    # =====================
    # CONTINU (CORRIGÉ)
    # =====================
    def move_threaded(self, direction_cmd: str):
        """
        direction_cmd = "next" | "prev" | "nextY" | "prevY"
        """

        is_y = direction_cmd.endswith("Y")
        now = time.time()

        if is_y:
            if self.moving_y or now - self.last_move_ts_y < self.move_interval:
                return
            self.last_move_ts_y = now
        else:
            if self.moving_x or now - self.last_move_ts_x < self.move_interval:
                return
            self.last_move_ts_x = now

        def worker():
            with self.lock:
                if is_y:
                    self.moving_y = True
                else:
                    self.moving_x = True

                self.send(direction_cmd)
                time.sleep(0.3)

                if is_y:
                    self.moving_y = False
                else:
                    self.moving_x = False

        threading.Thread(target=worker, daemon=True).start()

    # =====================
    # STOP
    # =====================
    def stop(self):
        self.send("stop")
        self.moving_x = False
        self.moving_y = False

    def close(self):
        try:
            self.port.close()
        except Exception:
            pass
