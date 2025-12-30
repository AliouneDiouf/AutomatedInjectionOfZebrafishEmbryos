# utils/converters.py
import cv2
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt


def cv_to_pixmap(bgr_img, label):
    if len(bgr_img.shape) == 2:
        rgb = cv2.cvtColor(bgr_img, cv2.COLOR_GRAY2RGB)
    else:
        rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)

    h, w, ch = rgb.shape
    qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)

    return QPixmap.fromImage(qimg).scaled(
        label.width(),
        label.height(),
        Qt.KeepAspectRatio,
        Qt.FastTransformation
    )
