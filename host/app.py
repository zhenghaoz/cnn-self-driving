from datetime import datetime
import io
import os
import platform
import socket
import subprocess
import sys
import webbrowser
from enum import Enum
from logging import Logger
from threading import Thread, Lock
from urllib import request, error

import cv2
import numpy as np
from PIL import Image
from PyQt5 import Qt
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import asset
import config


class MainForm(QMainWindow):

    # Enums

    class Direction(Enum):
        STOP = 0
        FORWARD = 1
        BACKWARD = 2
        TURN_LEFT = 3
        TURN_RIGHT = 4

    # Start up

    def __init__(self):
        super().__init__()

        self.logger = Logger('Host', 30)

        # Initialize tasks
        self.task_screen_shot = False
        self.task_video_record = None
        self.task_data_record = False
        self.lock_video_record = Lock()

        # Initialize direction stack
        self.direction_stack = [self.Direction.STOP]

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
        take_photo_action = QAction(QIcon(asset.ICON_CAMERA), 'Take Photo', self)
        take_photo_action.triggered.connect(self.action_screen_shot_triggered)
        self.actiion_video_record = QAction(QIcon(asset.ICON_START_VIDEO_RECORD), asset.STRING_START_VIDEO_RECORD, self)
        self.actiion_video_record.triggered.connect(self.action_video_record_triggered)
        self.action_data_record = QAction(QIcon(asset.ICON_START_DATA_RECORD), asset.STRING_START_DATA_RECORD, self)
        self.action_data_record.triggered.connect(self.action_data_record_triggered)
        browse_videos_action = QAction('Browse Videos', self)
        browse_videos_action.triggered.connect(self.action_browse_video_triggered)
        browse_datum_action = QAction('Browse Datum', self)
        browse_datum_action.triggered.connect(self.action_browse_data_triggered)
        browse_photos_action = QAction('Browse Photos', self)
        browse_photos_action.triggered.connect(self.action_browse_photo_triggered)
        self.driving_action = QAction(QIcon(asset.ICON_SELF_DRIVING_OFF), asset.STRING_START_SELF_DRIVING, self)
        self.driving_action.triggered.connect(self.self_driving)
        train_action = QAction(QIcon(asset.ICON_START_TRAIN), 'Start Training', self)
        load_action = QAction(QIcon(asset.ICON_OPEN), 'Load Model', self)
        load_action.setShortcut('Ctrl+O')
        load_action.triggered.connect(self.load_model)
        save_action = QAction(QIcon(asset.ICON_SAVE), 'Save Model', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_model)
        browse_home_page_action = QAction(QIcon(asset.ICON_GITHUB), 'Home Page', self)
        browse_home_page_action.triggered.connect(self.browse_home_page)
        show_usage_action = QAction('Usage', self)
        show_usage_action.triggered.connect(self.usage)

        # Draw menu
        menu = self.menuBar()
        menu_record = menu.addMenu('Record')
        menu_record.addAction(take_photo_action)
        menu_record.addAction(self.actiion_video_record)
        menu_record.addAction(self.action_data_record)
        menu_record.addSeparator()
        menu_record.addAction(browse_photos_action)
        menu_record.addAction(browse_videos_action)
        menu_record.addAction(browse_datum_action)
        menu_learn = menu.addMenu('Intelligence')
        menu_learn.addAction(self.driving_action)
        menu_learn.addAction(train_action)
        menu_learn.addSeparator()
        menu_learn.addAction(load_action)
        menu_learn.addAction(save_action)
        menu_about = menu.addMenu('About')
        menu_about.addAction(browse_home_page_action)
        menu_about.addSeparator()
        menu_about.addAction(show_usage_action)

        # Draw toolbar
        tool_bar_record = self.addToolBar('Record')
        tool_bar_record.setMovable(False)
        tool_bar_record.addAction(take_photo_action)
        tool_bar_record.addAction(self.actiion_video_record)
        tool_bar_record.addAction(self.action_data_record)
        tool_bar_learn = self.addToolBar('Intelligence')
        tool_bar_learn.setMovable(False)
        tool_bar_learn.addAction(self.driving_action)
        tool_bar_learn.addAction(train_action)
        tool_bar_learn.addAction(load_action)
        tool_bar_learn.addAction(save_action)
        tool_bar_about = self.addToolBar('About')
        tool_bar_about.setMovable(False)
        tool_bar_about.addAction(browse_home_page_action)

        # Draw status bars
        self.label_ctl_status = QLabel()
        self.label_ctl_status.setText('Control: Connecting...')
        self.label_stream_status = QLabel()
        self.label_stream_status.setText('Stream: Connecting...')
        self.label_op_status = QLabel()

        # Draw form
        self.statusBar().addPermanentWidget(self.label_ctl_status, 1)
        self.statusBar().addPermanentWidget(self.label_stream_status, 1)
        self.statusBar().addPermanentWidget(self.label_op_status, 2)
        self.setWindowTitle('Grand Raspberry Auto Host')
        self.setWindowIcon(QIcon(asset.ICON_ICON))
        self.setFixedSize(form_width, form_height)
        # Move the form to the center of current screen
        screen_size = QDesktopWidget().screenGeometry()
        frame_size = self.frameSize()
        self.move((screen_size.width() / 2) - (frame_size.width() / 2),
                  (screen_size.height() / 2) - (frame_size.height() / 2))
        self.show()

        # Start streamer
        self.keep_streamer = True
        self.thread_streamer = Thread(target=self.streamer)
        self.thread_streamer.start()

        # Connect agent
        try:
            address = ('192.168.1.1', 2001)
            self.socket_control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_control.settimeout(1)
            self.socket_control.connect(address)
            self.label_ctl_status.setText('Control: Online')
        except socket.timeout as e:
            self.logger.error('Control: timed out')
            self.label_ctl_status.setText('Control: timed out')

    # Internal Events

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_W:
            self.direction_stack.append(self.Direction.FORWARD)
            self.socket_control.send(self.CMD_FORWARD)
        elif event.key() == Qt.Key_S:
            self.direction_stack.append(self.Direction.BACKWARD)
            self.socket_control.send(self.CMD_BACKWARD)
        elif event.key() == Qt.Key_A:
            self.direction_stack.append(self.Direction.TURN_LEFT)
            self.socket_control.send(self.CMD_TURN_LEFT)
        elif event.key() == Qt.Key_D:
            self.direction_stack.append(self.Direction.TURN_RIGHT)
            self.socket_control.send(self.CMD_TURN_RIGHT)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_W \
                or event.key() == Qt.Key_S \
                or event.key() == Qt.Key_A \
                or event.key() == Qt.Key_D:
            self.direction_stack.pop()
            if self.direction_stack[-1] == self.Direction.STOP:
                self.socket_control.send(self.CMD_STOP)
            elif self.direction_stack[-1] == self.Direction.TURN_LEFT:
                self.socket_control.send(self.CMD_TURN_LEFT)
            elif self.direction_stack[-1] == self.Direction.TURN_RIGHT:
                self.socket_control.send(self.CMD_TURN_RIGHT)
            elif self.direction_stack[-1] == self.Direction.FORWARD:
                self.socket_control.send(self.CMD_FORWARD)
            elif self.direction_stack[-1] == self.Direction.BACKWARD:
                self.socket_control.send(self.CMD_BACKWARD)

    def closeEvent(self, event: QCloseEvent):
        self.keep_streamer = False
        self.socket_control.close()
        self.thread_streamer.join()

    # Action Events

    def action_screen_shot_triggered(self):
        self.task_screen_shot = True

    def action_video_record_triggered(self):
        self.lock_video_record.acquire()
        if self.task_video_record:
            # Release video writer
            self.task_video_record.release()
            self.task_video_record = None
            # Reset action for start
            self.actiion_video_record.setText(asset.STRING_START_VIDEO_RECORD)
            self.actiion_video_record.setIcon(QIcon(asset.ICON_START_VIDEO_RECORD))
        else:
            # Create video writer
            file_name = config.DIR_VIDEO + '{0:%Y-%m-%dT%H:%M:%S.%f}.avi'.format(datetime.datetime.now())
            self.task_video_record = cv2.VideoWriter(file_name, config.FOUR_CC, config.FPS,
                                                     (config.RESOLUTION_WIDTH, config.RESOLUTION_HEIGHT))
            # Reset action for stop
            self.actiion_video_record.setText(asset.STRING_STOP_VIDEO_RECORD)
            self.actiion_video_record.setIcon(QIcon(asset.ICON_STOP_VIDEO_RECORD))
        self.lock_video_record.release()

    def action_data_record_triggered(self):
        if self.task_data_record:
            self.task_data_record = False
            # Reset action for start
            self.action_data_record.setText(asset.STRING_START_DATA_RECORD)
            self.action_data_record.setIcon(QIcon(asset.ICON_START_DATA_RECORD))
        else:
            self.task_data_record = True
            # Reset action for stop
            self.action_data_record.setText(asset.STRING_STOP_DATA_RECORD)
            self.action_data_record.setIcon(QIcon(asset.ICON_STOP_DATA_RECORD))

    @staticmethod
    def action_browse_video_triggered():
        open_file(config.DIR_VIDEO)

    @staticmethod
    def action_browse_data_triggered():
        open_file(config.DIR_DATA)

    @staticmethod
    def action_browse_photo_triggered():
        open_file(config.DIR_PHOTO)

    def self_driving(self):
        if self.driving:
            self.driving = False
            self.driving_action.setText(asset.STRING_START_SELF_DRIVING)
            self.driving_action.setIcon(QIcon(asset.ICON_SELF_DRIVING_OFF))
        else:
            self.driving = True
            self.driving_action.setText(asset.STRING_STOP_SELF_DRIVING)
            self.driving_action.setIcon(QIcon(asset.ICON_SELF_DRIVING_ON))

    def load_model(self):
        file_name = QFileDialog.getOpenFileName(self, 'Load Model', './', 'Model (*.ckpt);;All Files (*.*)')

    def save_model(self):
        file_name = QFileDialog.getSaveFileName(self, 'Save Model', './', 'Model (*.ckpt);;All Files (*.*)')

    @staticmethod
    def browse_home_page():
        webbrowser.open(config.URL_HOME_PAGE)

    def usage(self):
        qbox = QMessageBox(self)
        qbox.setWindowTitle('Usage')
        qbox.setText(asset.STRING_USAGE)
        qbox.show()

    # Commands

    CMD_STOP = b'\xff\x00\x00\x00\xff'
    CMD_FORWARD = b'\xff\x00\x01\x00\xff'
    CMD_BACKWARD = b'\xff\x00\x02\x00\xff'
    CMD_TURN_LEFT = b'\xff\x00\x03\x00\xff'
    CMD_TURN_RIGHT = b'\xff\x00\x04\x00\xff'

    @staticmethod
    def cmd_left_speed(speed):
        assert speed <= 100
        return b'\xff\x02\x01' + bytes([speed]) + b'\xff'

    @staticmethod
    def cmd_right_speed(speed):
        assert speed <= 100
        return b'\xff\x02\x02' + bytes([speed]) + b'\xff'

    # Threads

    def streamer(self):
        try:
            stream = request.urlopen(config.URL_STREAM, timeout=1)
            self.label_stream_status.setText('Stream: Online')
            data = bytes()
            while self.keep_streamer:
                data += stream.read(1024)
                a = data.find(b'\xff\xd8')
                b = data.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    jpg = data[a:b + 2]
                    data = data[b + 2:]
                    self.pixmap.loadFromData(jpg)
                    self.monitor.setPixmap(self.pixmap.scaled(self.monitor.width(), self.monitor.height(), Qt.KeepAspectRatio))
                    # Screen shot
                    if self.task_screen_shot:
                        file_name = config.DIR_PHOTO + datetime.utcnow().strftime('%Y%m%d%H%M%S%f') + '.png'
                        Image.open(io.BytesIO(jpg)).save(file_name)
                        self.label_op_status.setText('The photo has been saved at ' + file_name)
                        self.task_screen_shot = False
                    # Video Record
                    self.lock_video_record.acquire()
                    if self.task_video_record:
                        frame = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        self.task_video_record.write(frame)
                    self.lock_video_record.release()
                    # Data Record
                    if self.task_data_record and self.direction_stack[-1] != self.Direction.STOP:
                        file_name = config.DIR_DATA + datetime.utcnow().strftime('%Y%m%d%H%M%S%f') \
                                    + '-' + str(self.direction_stack[-1].value) + '.png'
                        Image.open(io.BytesIO(jpg)).save(file_name)
        except error.URLError as e:
            self.logger.error('Stream: %s' % e.reason)
            self.label_stream_status.setText('Stream: %s' % e.reason)
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
