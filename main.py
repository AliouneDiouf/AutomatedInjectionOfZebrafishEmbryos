# main.py
import sys
from PyQt5.QtWidgets import QApplication
from InjectionGUI import InjectionGUI
from utils.video_recorder import VideoRecorder



def main():
    app = QApplication(sys.argv)
    gui = InjectionGUI()
    gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()



