import sys
import time
import urllib.request
from threading import Thread
from PyQt5 import Qt
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class MainForm(QMainWindow):

    def __init__(self):
        super().__init__()

        # Geometries
        form_height = 600
        form_width = 760
        monitor_height = 560
        monitor_width = form_width

        # Draw monitor
        self.monitor = QLabel(self)
        self.monitor.setGeometry(0, 0, monitor_width, monitor_height)
        self.monitor.setAlignment(Qt.AlignCenter)

        # Draw form
        self.statusBar().showMessage('Ready')
        self.setWindowTitle('Grand Raspberry Auto Host')
        self.setWindowIcon(QIcon('icon.png'))
        self.setFixedSize(form_width, form_height)
        # Move the form to the center of current screen
        screen_size = QDesktopWidget().screenGeometry()
        frame_size = self.frameSize()
        self.move((screen_size.width() / 2) - (frame_size.width() / 2),
                  (screen_size.height() / 2) - (frame_size.height() / 2))
        self.show()

        # Start streamer
        self.streamer_running = True
        self.thread_streamer = Thread(target=self.streamer)
        self.thread_streamer.start()

    def keyPressEvent(self, event: QKeyEvent):
        print(event.key())

    def keyReleaseEvent(self, event: QKeyEvent):
        print(event.key())

    def closeEvent(self, event: QCloseEvent):
        self.statusBar().showMessage('Exiting...')
        self.streamer_running = False
        self.thread_streamer.join()

    def streamer(self):
        stream = urllib.request.urlopen('http://192.168.1.1:8080/?action=stream')
        pixmap = QPixmap()
        data = bytes()
        while self.streamer_running:
            data += stream.read(1024)
            a = data.find(b'\xff\xd8')
            b = data.find(b'\xff\xd9')
            if a != -1 and b != -1:
                jpg = data[a:b + 2]
                data = data[b + 2:]
                pixmap.loadFromData(jpg)
                self.monitor.setPixmap(pixmap.scaled(self.monitor.width(), self.monitor.height(), Qt.KeepAspectRatio))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    form = MainForm()
    sys.exit(app.exec_())
