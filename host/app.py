import sys
import socket
import asset
import os
import subprocess
import platform
import config
import webbrowser
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
        monitor_x = 0
        monitor_y = 96
        monitor_height = 760
        monitor_width = 1000
        status_height = 32
        form_height = monitor_y + monitor_height + status_height
        form_width = monitor_width

        # Draw monitor
        self.pixmap = QPixmap(asset.IMAGE_OFFLINE)
        self.monitor = QLabel(self)
        self.monitor.setStyleSheet('background-color: black')
        self.monitor.setGeometry(monitor_x, monitor_y, monitor_width, monitor_height)
        self.monitor.setAlignment(Qt.AlignCenter)
        self.monitor.setPixmap(self.pixmap.scaled(self.monitor.width(), self.monitor.height(), Qt.KeepAspectRatio))

        # Setup actions
        record_video_action = QAction(QIcon(asset.ICON_START_VIDEO_RECORD), 'Start Video Record', self)
        record_data_action = QAction(QIcon(asset.ICON_START_DATA_RECORD), 'Start Data Record', self)
        browse_videos_action = QAction('Browse Videos', self)
        browse_videos_action.triggered.connect(self.browse_video)
        browse_datum_action = QAction('Browse Datum', self)
        browse_datum_action.triggered.connect(self.browse_data)
        train_action = QAction(QIcon(asset.ICON_START_TRAIN), 'Start training', self)
        load_action = QAction(QIcon(asset.ICON_OPEN), 'Load Model', self)
        save_action = QAction(QIcon(asset.ICON_SAVE), 'Save Model', self)
        browse_home_page = QAction(QIcon(asset.ICON_GITHUB), 'Home Page', self)
        browse_home_page.triggered.connect(self.browse_home_page)

        # Draw menu
        menu = self.menuBar()
        menu_record = menu.addMenu('Record')
        menu_record.addAction(record_video_action)
        menu_record.addAction(record_data_action)
        menu_record.addSeparator()
        menu_record.addAction(browse_videos_action)
        menu_record.addAction(browse_datum_action)
        menu_learn = menu.addMenu('Learn')
        menu_learn.addAction(train_action)
        menu_learn.addSeparator()
        menu_learn.addAction(load_action)
        menu_learn.addAction(save_action)
        menu_about = menu.addMenu('About')
        menu_about.addAction(browse_home_page)

        # Draw toolbar
        tool_bar_record = self.addToolBar('Record')
        tool_bar_record.setMovable(False)
        tool_bar_record.addAction(record_video_action)
        tool_bar_record.addAction(record_data_action)
        tool_bar_learn = self.addToolBar('Learn')
        tool_bar_learn.setMovable(False)
        tool_bar_learn.addAction(train_action)
        tool_bar_learn.addAction(load_action)
        tool_bar_learn.addAction(save_action)
        tool_bar_about = self.addToolBar('About')
        tool_bar_about.setMovable(False)
        tool_bar_about.addAction(browse_home_page)

        # Draw form
        self.status = QLabel()
        self.status.setText('Ready')
        self.statusBar().addPermanentWidget(self.status)
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
        self.status.setText('Exiting...')
        self.sock.close()
        self.thread_streamer.join()

    @staticmethod
    def browse_video():
        open_file(config.VIDEO_DIR)

    @staticmethod
    def browse_data():
        open_file(config.DATA_DIR)

    @staticmethod
    def browse_home_page():
        webbrowser.open(asset.URL_HOME_PAGE)

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


def open_file(path):
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


if __name__ == '__main__':
    app = QApplication(sys.argv)
    form = MainForm()
    sys.exit(app.exec_())
