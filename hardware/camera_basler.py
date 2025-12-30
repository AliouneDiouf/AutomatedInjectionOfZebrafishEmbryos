# hardware/camera_basler.py

from pypylon import pylon
import cv2


class BaslerCamera:
    def __init__(self, width=860, height=640, exposure=5000.0, gain=10.0):
        self.camera = pylon.InstantCamera(
            pylon.TlFactory.GetInstance().CreateFirstDevice()
        )
        self.camera.Open()

        self.camera.Width.SetValue(width)
        self.camera.Height.SetValue(height)
        self.camera.ExposureTime.SetValue(exposure)
        self.camera.Gain.SetValue(gain)

        self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        self.converter = pylon.ImageFormatConverter()
        self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

    def grab(self):
        if not self.camera.IsGrabbing():
            return None

        grab = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        if not grab.GrabSucceeded():
            grab.Release()
            return None

        image = self.converter.Convert(grab)
        frame = image.GetArray()
        grab.Release()
        return frame

    def close(self):
        try:
            if self.camera.IsGrabbing():
                self.camera.StopGrabbing()
            self.camera.Close()
        except Exception:
            pass
