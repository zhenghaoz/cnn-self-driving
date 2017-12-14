import sys
import socket
from logging import Logger
from urllib import request, error
from threading import Thread
from PyQt5 import Qt
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class MainForm(QMainWindow):

    CMD_STOP = b'\xff\x00\x00\x00\xff'
    CMD_FORWARD = b'\xff\x00\x01\x00\xff'
    CMD_BACKWARD = b'\xff\x00\x02\x00\xff'
    CMD_TURN_LEFT = b'\xff\x00\x03\x00\xff'
    CMD_TURN_RIGHT = b'\xff\x00\x04\x00\xff'

    def __init__(self):
        super().__init__()

        self.logger = Logger('Host', 30)

        # Geometries
        form_height = 600
        form_width = 760
        monitor_height = 560
        monitor_width = form_width

        # Draw monitor
        self.pixmap = QPixmap('offline.jpg')
        self.monitor = QLabel(self)
        self.monitor.setGeometry(0, 0, monitor_width, monitor_height)
        self.monitor.setAlignment(Qt.AlignCenter)
        self.monitor.setPixmap(self.pixmap.scaled(self.monitor.width(), self.monitor.height(), Qt.KeepAspectRatio))

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

        # Connect agent
        try:
            address = ('192.168.1.1', 2001)
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(1)
            self.sock.connect(address)
        except socket.timeout as e:
            self.logger.error('Control: %s' % e.strerror)

    def cmd_left_speed(self, speed):
        assert speed <= 100
        return b'\xff\x02\x01' + bytes([speed]) + b'\xff'

    def cmd_right_speed(self, speed):
        assert speed <= 100
        return b'\xff\x02\x02' + bytes([speed]) + b'\xff'

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_W:
            self.sock.send(self.cmd_left_speed(100))
            self.sock.send(self.cmd_right_speed(100))
            self.sock.send(b'\xff\x00\x01\x00\xff')
        elif event.key() == Qt.Key_S:
            pass
        elif event.key() == Qt.Key_A:
            pass
        elif event.key() == Qt.Key_D:
            pass

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_W:
            self.sock.send(b'\xff\x00\x00\x00\xff')
        elif event.key() == Qt.Key_S:
            pass
        elif event.key() == Qt.Key_A:
            pass
        elif event.key() == Qt.Key_D:
            pass

    def closeEvent(self, event: QCloseEvent):
        self.streamer_running = False
        self.statusBar().showMessage('Exiting...')
        self.sock.close()
        self.thread_streamer.join()

    def streamer(self):
        try:
            stream = request.urlopen('http://192.168.1.1:8080/?action=stream', timeout=1)
            data = bytes()
            while self.streamer_running:
                data += stream.read(1024)
                a = data.find(b'\xff\xd8')
                b = data.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    jpg = data[a:b + 2]
                    data = data[b + 2:]
                    self.pixmap.loadFromData(jpg)
                    self.monitor.setPixmap(self.pixmap.scaled(self.monitor.width(), self.monitor.height(), Qt.KeepAspectRatio))
        except error.URLError as e:
            self.logger.error('Stream: %s' % e.reason)
        finally:
            return


if __name__ == '__main__':
    app = QApplication(sys.argv)
    form = MainForm()
    sys.exit(app.exec_())
