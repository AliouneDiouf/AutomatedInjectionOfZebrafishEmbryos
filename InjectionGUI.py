# -*- coding: utf-8 -*-

import sys
import time
import datetime
import cv2
import torch
import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QSlider, QFrame
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QSizePolicy

# =========================
# CONFIG
# =========================
from config.constants import *
from config.paths import MODEL_PATH, MODEL_CLASSIFY
from config.hardware import (
    SERIAL_PORT_STAGE, SERIAL_PORT_INJECT,
    BAUDRATE_STAGE, BAUDRATE_INJECT,
    SLOW_APPROACH_SPEED
)

# =========================
# UTILS
# =========================
from utils.converters import cv_to_pixmap
from utils.video_recorder import VideoRecorder
from utils.fps import FPSCounter

# =========================
# HARDWARE
# =========================
from hardware.stage_controller import StageController
from hardware.injector_controller import InjectorController
from hardware.camera_basler import BaslerCamera

# =========================
# VISION
# =========================
from vision.yolo_detector import YoloDetector
from vision.tip_tracker import TipTracker
from vision.embryo_tracker import EmbryoTracker
from vision.contact_classifier import ContactClassifier

# =========================
# INJECTION LOGIC
# =========================
from injection.processed_memory import ProcessedMemory
from injection.exclusion_zone import ExclusionZone
from injection.human_profile_runner import HumanProfileRunner
from injection.injection_manager import InjectionManager

INJECTION_ZONE_RADIUS = 30   # px (à ajuster)
ZONE_COLOR = (0, 255, 255)   # jaune
ZONE_THICKNESS = 2

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🔥 YOLO running on {device.upper()}")


class InjectionGUI(QWidget):

    # =====================================================
    # INIT
    # =====================================================
    def __init__(self):
        super().__init__()

        # -------------------------
        # STATE
        # -------------------------
        self.frame_w = None
        self.frame_h = None
        self.dynamic_tip = None
        self.align_point = None
        self.home_angle = None
        # --- Manual control state ---
        self.manual_speed = 120       # pipette speed (steps/s)
        self.stage_step = 50          # stage step (steps)


        self.nb_injected = 0
        self.start_time = None
        self.contact_handled = False
        self.contact_armed = True          # 🔫 prêt à déclencher un contact
        self.last_touch_time = 0.0         # ⏱ pour petite temporisation
        self.rearm_delay = 0.35            # délai mini après touch (sec)



        # -------------------------
        # HARDWARE
        # -------------------------
        self.camera = BaslerCamera()
        self.stage = StageController(SERIAL_PORT_STAGE, BAUDRATE_STAGE)
        self.injector = InjectorController(SERIAL_PORT_INJECT, BAUDRATE_INJECT)

        # -------------------------
        # VISION
        # -------------------------
        self.detector = YoloDetector(MODEL_PATH, device=device)
        self.tip_tracker = TipTracker()
        self.embryo_tracker = EmbryoTracker()
        self.contact_clf = ContactClassifier(MODEL_CLASSIFY)

        # -------------------------
        # INJECTION LOGIC
        # -------------------------
        self.proc_mem = ProcessedMemory(MEMORY_TIMEOUT, DISTANCE_MIN_BASE)
        self.exclusion = ExclusionZone(DISTANCE_MIN_BASE)

        self.profile_runner = HumanProfileRunner(self.injector)

        self.inj_manager = InjectionManager(
            stage_ctrl=self.stage,
            injector_ctrl=self.injector,
            profile_runner=self.profile_runner,
            processed_memory=self.proc_mem,
            exclusion_zone=self.exclusion,
            slow_speed=SLOW_APPROACH_SPEED
        )

        # -------------------------
        # UTILS
        # -------------------------
        self.video = VideoRecorder()
        self.fps = FPSCounter()

        # -------------------------
        # UI
        # -------------------------
        self._build_ui()

        # -------------------------
        # TIMER
        # -------------------------
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(10)

    # =====================================================
    # UI
    # =====================================================
    def _build_ui(self):
        self.setWindowTitle("Zebrafish Injection — Modular Architecture")
        self.resize(1050, 870)

        # =========================
        # CREATE WIDGETS FIRST
        # =========================

        # ---- VIDEO ----
        self.label_video = QLabel()
        self.label_video.setSizePolicy(
            QSizePolicy.Expanding,
              QSizePolicy.Expanding
            )
        self.label_video.setAlignment(Qt.AlignCenter)
        self.label_video.setStyleSheet("background-color: black;")
        self.label_video.mousePressEvent = self.on_video_click

        # ---- DASHBOARD LABELS ----
        # ---- DASHBOARD LABELS ----
        self.lbl_tip = QLabel("Tip: ---")
        self.lbl_yolks = QLabel("Embryos: 0")
        self.lbl_contact = QLabel("Contact: No")
        self.lbl_fps = QLabel("FPS: ---")
        self.lbl_nb = QLabel("Injected: 0")

        dash_layout = QVBoxLayout()
        dash_layout.setSpacing(8)

        for w in [self.lbl_tip, self.lbl_yolks, self.lbl_contact, self.lbl_fps, self.lbl_nb]:
            w.setStyleSheet("""
                background-color: #f5f5f5;
                color: #111;
                padding: 8px;
                border-radius: 6px;
            """)
            dash_layout.addWidget(w)   # ✅ DANS LA BOUCLE

        dash_layout.addStretch()

        dash_frame = QFrame()
        dash_frame.setLayout(dash_layout)
        dash_frame.setFixedWidth(250)
        dash_frame.setStyleSheet("""
            QFrame {
                background-color: #eaeaea;
                border-radius: 8px;
            }
        """)

                

        # ---- CONTROL BUTTONS ----
        self.btn_start = QPushButton("▶ START AUTO")
        self.btn_stop = QPushButton("⏹ STOP")

        self.btn_start.clicked.connect(self.start_auto)
        self.btn_stop.clicked.connect(self.close_app)

        controls = QHBoxLayout()
        controls.addWidget(self.btn_start)
        controls.addWidget(self.btn_stop)

        # =========================
        # MANUAL CONTROL PANEL
        # =========================
        manual_box = QVBoxLayout()

        title_manual = QLabel("Manual control")
        title_manual.setFont(QFont("Segoe UI", 12, QFont.Bold))
        manual_box.addWidget(title_manual)

        # Pipette speed
        self.lbl_speed = QLabel(f"Pipette speed: {self.manual_speed} steps/s")
        manual_box.addWidget(self.lbl_speed)

        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(10, 1000)
        self.slider_speed.setValue(self.manual_speed)
        self.slider_speed.valueChanged.connect(self.on_speed_changed)
        manual_box.addWidget(self.slider_speed)

        # Pipette buttons
        pipette_btns = QHBoxLayout()
        self.btn_forward = QPushButton("► FORWARD")
        self.btn_backward = QPushButton("◄ BACKWARD")

        self.btn_forward.pressed.connect(self.manual_forward_start)
        self.btn_forward.released.connect(self.manual_stop)
        self.btn_backward.pressed.connect(self.manual_backward_start)
        self.btn_backward.released.connect(self.manual_stop)

        pipette_btns.addWidget(self.btn_backward)
        pipette_btns.addWidget(self.btn_forward)
        manual_box.addLayout(pipette_btns)

        # Stage step
        self.lbl_stage = QLabel(f"Stage step: {self.stage_step} steps")
        manual_box.addWidget(self.lbl_stage)

        self.slider_stage = QSlider(Qt.Horizontal)
        self.slider_stage.setRange(5, 500)
        self.slider_stage.setValue(self.stage_step)
        self.slider_stage.valueChanged.connect(self.on_stage_step_changed)
        manual_box.addWidget(self.slider_stage)

        # Stage buttons
        stage_btns = QHBoxLayout()
        self.btn_stage_left = QPushButton(" ▲ STAGE UP")
        self.btn_stage_right = QPushButton("STAGE DOWN ▼")

        self.btn_stage_left.clicked.connect(self.stage_left)
        self.btn_stage_right.clicked.connect(self.stage_right)

        stage_btns.addWidget(self.btn_stage_left)
        stage_btns.addWidget(self.btn_stage_right)
        manual_box.addLayout(stage_btns)

        # Stage buttons Y (NOUVEAU)
        stage_btns_y = QHBoxLayout()
        self.btn_stage_up = QPushButton(" ◄ STAGE LEFT")
        self.btn_stage_down = QPushButton(" ► STAGE RIGHT")

        self.btn_stage_up.clicked.connect(self.stage_up)
        self.btn_stage_down.clicked.connect(self.stage_down)

        stage_btns_y.addWidget(self.btn_stage_up)
        stage_btns_y.addWidget(self.btn_stage_down)
        manual_box.addLayout(stage_btns_y)

        manual_frame = QFrame()
        manual_frame.setLayout(manual_box)

        # =========================
        # MAIN LAYOUT (SOLUTION 1)
        # =========================
        root = QGridLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(12)

        # Video + dashboard
        root.addWidget(self.label_video, 0, 0, 1, 1)
        root.addWidget(dash_frame,       0, 1, 1, 1)

        # Controls + manual
        root.addLayout(controls,    1, 0, 1, 2)
        root.addWidget(manual_frame, 2, 0, 1, 2)

        root.setColumnStretch(0, 4)
        root.setColumnStretch(1, 1)
        root.setRowStretch(0, 1)


    # =====================================================
    # MAIN LOOP
    # =====================================================
    def on_speed_changed(self, value):
     self.manual_speed = value
     self.lbl_speed.setText(f"Pipette speed: {value} steps/s")
    def manual_forward_start(self):
        self.injector.start_profile()
        self.injector.dir_backward()   # selon ton sens mécanique
        self.injector.set_speed(self.manual_speed)

    def manual_backward_start(self):
     self.injector.start_profile()
     self.injector.dir_forward()
     self.injector.set_speed(self.manual_speed)

    def manual_stop(self):
        self.injector.stop_profile()
    def on_stage_step_changed(self, value):
     self.stage_step = value
     self.lbl_stage.setText(f"Stage step: {value} steps")
    def stage_left(self):
     self.stage.move_left(self.stage_step)

    def stage_right(self):
      self.stage.move_right(self.stage_step)

    def stage_up(self):
        self.stage.move_up(self.stage_step)

    def stage_down(self):
        self.stage.move_down(self.stage_step)





    def update_frames(self):

        # -------------------------
        # CAMERA GRAB
        # -------------------------
        frame = self.camera.grab()
        if frame is None:
            return

        if self.video.writer is None:
            self.video.start(frame.shape)

        self.frame_h, self.frame_w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # IMAGE UNIQUE D’AFFICHAGE
        yolo_view = frame.copy()
        contact = False


        # -------------------------
        # YOLO DETECTION
        # -------------------------
        pipettes, embryos = self.detector.detect(frame)
        self.dynamic_tip = self.tip_tracker.update(
         pipettes,
            self.frame_w,
             self.frame_h
             )
        
        # 🔥 OBLIGATOIRE : récupère les centres et labels des embryons
        ids, centers, labels = self.embryo_tracker.update(embryos)
        self.lbl_yolks.setText(f"Embryos: {len(ids)}")

                # -------------------------
        # DRAW INJECTION ZONES (ONE PER EMBRYO)
        # -------------------------
        for (cx, cy) in centers:
            # cercle = zone d'injection
            cv2.circle(
                yolo_view,
                (int(cx), int(cy)),
                INJECTION_ZONE_RADIUS,
                ZONE_COLOR,
                ZONE_THICKNESS
            )

            # centre exact (repère visuel)
            cv2.circle(
                yolo_view,
                (int(cx), int(cy)),
                2,
                (0, 0, 255),
                -1
            )


                # -------------------------
        # DRAW PIPETTE MASK (best)
        # -------------------------
        if False and pipettes: 
            pipettes_sorted = sorted(
                pipettes,
                key=lambda p: (p.get("x2", 0), p.get("conf", 0.0)),
                reverse=True
            )
            best = pipettes_sorted[0]
            mask = best.get("mask", None)

            if mask is not None:
                mask_u8 = (mask > 0).astype(np.uint8)

                # 🔥 CORRECTION CRITIQUE : resize masque → frame
                mask_u8 = cv2.resize(
                    mask_u8,
                    (self.frame_w, self.frame_h),
                    interpolation=cv2.INTER_NEAREST
                )

                # overlay vert
                overlay = yolo_view.copy()
                overlay[mask_u8 > 0] = (0, 50, 0)
                yolo_view = cv2.addWeighted(overlay, 0.30, yolo_view, 0.70, 0)

                # contour
                contours, _ = cv2.findContours(
                    mask_u8,
                    cv2.RETR_EXTERNAL,
                    cv2.CHAIN_APPROX_SIMPLE
                )
                cv2.drawContours(yolo_view, contours, -1, (0, 200, 0), 2)


                

        # -------------------------
        # DRAW EMBRYOS + LABELS
        # -------------------------
        for (cx, cy), lbl in zip(centers, labels):

            # 🔥 FORCE LE NOM DU LABEL
            if lbl == "CytoLivable":
                lbl_display = "YolkLivable"
            else:
                lbl_display = lbl

            cv2.circle(yolo_view, (cx, cy), 6, (0, 255, 0), -1)

            cv2.putText(
                yolo_view,
                lbl_display,
                (cx + 10, cy - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
                cv2.LINE_AA
            )

        # -------------------------
        # DRAW TIP
        # -------------------------
        if self.dynamic_tip:
            tx, ty = self.dynamic_tip
            cv2.circle(yolo_view, (tx, ty), 8, (150, 0, 0), -1)
            self.lbl_tip.setText(f"Tip: {self.dynamic_tip}")
            # -------------------------
            # 🔁 REARM CONTACT (pour embryon suivant)
            # -------------------------
            # On réarme seulement quand :
            # - on n'est plus en injection
            # - le contact est redevenu False (perte de contact)
            # - un petit délai est passé après le dernier TOUCH (anti rebond)
           

        else:
            self.lbl_tip.setText("Tip: LOST")

        # -------------------------
        # CONTACT CLASSIFICATION
        # -------------------------
        contact = False
        if self.dynamic_tip:
            contact, score, _ = self.contact_clf.classify(
                gray,
                self.dynamic_tip,
                self.frame_w,
                self.frame_h
            )
            self.lbl_contact.setText("Contact: YES" if contact else "Contact: No")
        # ✅ RÉARMER LE CONTACT POUR L’EMBRYON SUIVANT
        if (not self.inj_manager.is_injecting) and (not contact):
            if (time.time() - self.last_touch_time) > self.rearm_delay:
                self.contact_handled = False
                self.contact_armed = True


        # -------------------------
        # ALIGNMENT / INJECTION LOGIC
        # -------------------------
        anchor = self.align_point if self.align_point else self.dynamic_tip

        if anchor:
            self.inj_manager.try_alignment_step(
                centers=centers,
                tip=anchor,
                base_eps_deg=EPSILON_DEG
            )

        # -------------------------
        # 🔥 CONTACT → TOUCH
        # -------------------------
                    # 🔥 CONTACT → TOUCH (une seule fois)
        # -------------------------
# 🔥 CONTACT → TOUCH → INJECTION (UNE SEULE FOIS)
# -------------------------
        # -------------------------
# 🔥 CONTACT → TOUCH → INJECTION (UNE SEULE FOIS PAR EMBRYON)
# -------------------------
        if contact and self.contact_armed and (not self.inj_manager.is_injecting):

            triggered = self.inj_manager.on_contact()

            if triggered:
                self.contact_handled = True
                self.contact_armed = False          # 🔒 empêche multi-trigger tant que contact reste vrai
                self.last_touch_time = time.time()  # ⏱ référence pour réarmement

                # VISUEL TOUCH
                cv2.putText(
                    yolo_view,
                    "TOUCH !",
                    (50, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    2.2,
                    (0, 0, 255),
                    6,
                    cv2.LINE_AA
                )

                h, w = yolo_view.shape[:2]
                cv2.rectangle(yolo_view, (0, 0), (w - 1, h - 1), (0, 0, 255), 6)

                self.nb_injected += 1
                self.lbl_nb.setText(f"Injected: {self.nb_injected}")

        # -------------------------
        # 🔥 INJECTING (pendant l’injection)
        # -------------------------
        if self.inj_manager.is_injecting:
            cv2.putText(
                yolo_view,
                "INJECTING",
                (50, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                2.0,
                (0, 165, 255),   # orange
                5,
                cv2.LINE_AA
            )

        # -------------------------
        # FPS
        # -------------------------
        fps = self.fps.update()
        if fps:
            self.lbl_fps.setText(f"FPS: {fps:.1f}")
            cv2.putText(
                yolo_view,
                f"FPS: {fps:.1f}",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

        # -------------------------
        # RECORD + DISPLAY
        # -------------------------
        self.video.write(yolo_view)
        self.label_video.setPixmap(cv_to_pixmap(yolo_view, self.label_video))

    # =====================================================
    # EVENTS
    # =====================================================
    def on_video_click(self, event):
        if self.frame_w is None:
            return

        label_w = self.label_video.width()
        label_h = self.label_video.height()

        scale = min(label_w / self.frame_w, label_h / self.frame_h)
        offset_x = (label_w - self.frame_w * scale) / 2
        offset_y = (label_h - self.frame_h * scale) / 2

        x = int((event.x() - offset_x) / scale)
        y = int((event.y() - offset_y) / scale)

        if 0 <= x < self.frame_w and 0 <= y < self.frame_h:
            self.align_point = (x, y)
            print(f"📍 Align point set: {self.align_point}")

    # =====================================================
    # START / STOP
    # =====================================================
    def start_auto(self):
        self.start_time = time.time()

        angle = self.injector.read_angle_deg()
        if angle is None:
            print("❌ Cannot read HOME angle")
            return

        self.home_angle = angle
        self.inj_manager.set_home_angle(angle)
        self.inj_manager.start_alignment()

        self.stage.move_threaded("prev")
        print(f"🏠 HOME angle set: {angle:.2f}")

    def close_app(self):
        self.timer.stop()
        self.video.stop()
        self.camera.close()
        self.stage.close()
        self.injector.close()
        self.close()


# =====================================================
# RUN
# =====================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = InjectionGUI()
    gui.show()
    sys.exit(app.exec_())
