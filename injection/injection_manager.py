# injection/injection_manager.py

import threading
import time
from injection.alignment import is_aligned


class InjectionManager:
    def __init__(
        self,
        stage_ctrl,
        injector_ctrl,
        profile_runner,
        processed_memory,
        exclusion_zone,
        slow_speed=250.0,
        front_margin_px=12
    ):
        self.stage = stage_ctrl
        self.injector = injector_ctrl
        self.profile = profile_runner
        self.memory = processed_memory
        self.exclusion = exclusion_zone

        self.slow_speed = slow_speed
        self.front_margin_px = front_margin_px

        # states
        self.align_active = False
        self.is_injecting = False
        self.slow_active = False
        self.contact_handled = False
        self.pending_center = None

        # “forced first backward” logic
        self.slow_started_once = False

        # home angle for retreat
        self.home_angle = None

    def set_home_angle(self, angle):
        self.home_angle = angle

    def start_alignment(self):
        self.align_active = True

    def stop_alignment(self):
        self.align_active = False

    def can_process(self):
        return self.align_active and (not self.is_injecting)

    def pick_candidates(self, centers, tip):
        tipx, tipy = tip
        cands = []
        for pt in centers:
            if pt[0] < tipx - self.front_margin_px and not self.memory.contains(pt):
                if not self.exclusion.contains(pt):
                    cands.append(pt)
        cands.sort(key=lambda p: p[1], reverse=True)  # lowest first
        return cands

    def try_alignment_step(self, centers, tip, base_eps_deg=1.0):
        """
        Called every frame.
        If aligned -> start slow approach.
        Else -> stage prev step.
        """
        if tip is None or not self.can_process():
            return

        candidates = self.pick_candidates(centers, tip)

        for cand in candidates:
            if is_aligned(cand, tip, base_eps_deg=base_eps_deg):
                self.start_slow_approach(cand, anchor=tip)
                return

        # no aligned candidate
        self.stage.move_threaded("prev")

    # -----------------------------
    # Slow approach + contact
    # -----------------------------
    def start_slow_approach(self, center, anchor=None):
        def worker():
            try:
                self.stop_alignment()
                self.pending_center = center
                self.stage.stop()

                self.is_injecting = False
                self.slow_active = True
                self.contact_handled = False

                self.injector.send_safe("start_profile")

                # forced first backward
                if not self.slow_started_once:
                    self.injector.send_safe("dir_backward")
                    self.slow_started_once = True
                else:
                    # your safety logic: default backward
                    self.injector.send_safe("dir_backward")

                self.injector.send_safe(f"setSpeed {self.slow_speed:.1f}")

            except Exception as e:
                print(f"[InjectionManager] start_slow_approach error: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def on_contact(self):
        """
        Call when contact_detected becomes True in update loop.
        Returns True if injection was actually triggered.
        """
        if not self.slow_active or self.contact_handled or self.is_injecting:
            return False

        self.contact_handled = True
        self.is_injecting = True

        def worker():
            try:
                # stop slow approach
                self.injector.send_safe("setSpeed 0")
                self.injector.send_safe("end_profile")

                self.stage.stop()
                time.sleep(0.05)

                self.profile.run(retreat_home_angle=self.home_angle)

                if self.pending_center is not None:
                    self.memory.add(self.pending_center)
                    self.exclusion.enable(self.pending_center)

                self.post_injection_move()

            finally:
                self.is_injecting = False
                self.slow_active = False
                self.contact_handled = False
                self.pending_center = None

        threading.Thread(target=worker, daemon=True).start()
        return True

    def post_injection_move(self):
        """
        Equivalent to your post_injection_move: prev then disable exclusion.
        """
        time.sleep(0.5)
        self.stage.send("prev")
        time.sleep(0.6)
        self.exclusion.disable()
        self.start_alignment()
