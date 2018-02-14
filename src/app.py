import os
import platform
import socket
import subprocess
import sys
import webbrowser
import csv
from datetime import datetime
from enum import Enum
from logging import Logger
from threading import Thread
from urllib import error

import cv2
import tensorflow as tf
import numpy as np
from PyQt5 import Qt
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import asset
import config
import network
from lane import LaneDetector
from display import DisplayEngine
from network import PilotNet


class MainForm(QMainWindow):

    # Enums

    STOP = -1
    TURN_LEFT = 0
    TURN_RIGHT = 1
    FORWARD = 2
    BACKWARD = 3

    # Start up

    def __init__(self):
        super().__init__()

        self.logger = Logger('Host', 30)

        self.engine = DisplayEngine(config.FRAME_HEIGHT,
                                    config.FRAME_WIDTH,
                                    config.FRAME_CHANNEL,
                                    PilotNet.INPUT_HEIGHT,
                                    PilotNet.INPUT_WIDTH,
                                    100)
        # Initialize tasks
        self.task_screen_shot = False
        self.task_video_record = False
        self.task_self_driving = False
        self.task_video_record_stream = None
        self.task_video_actions = None
        self.task_video_file_name = None

        # Initialize direction stack
        self.action_stack = [Qt.Key_Space]
        self.key_status = {}

        # Initialize command map
        self.cmd_map = {
            Qt.Key_Space: self.CMD_STOP,
            Qt.Key_W: self.CMD_FORWARD,
            Qt.Key_S: self.CMD_BACKWARD,
            Qt.Key_A: self.CMD_TURN_LEFT,
            Qt.Key_D: self.CMD_TURN_RIGHT
        }

        # Geometries
        monitor_x = 0
        monitor_y = 60
        monitor_height = 512
        monitor_width = 720
        status_height = 20
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
        take_photo_action = QAction(QIcon(asset.ICON_CAMERA), 'Screen Shot', self)
        take_photo_action.triggered.connect(self.action_screen_shot_triggered)
        self.action_video_record = QAction(QIcon(asset.ICON_START_VIDEO_RECORD), asset.STRING_START_VIDEO_RECORD, self)
        self.action_video_record.triggered.connect(self.action_video_record_triggered)
        browse_videos_action = QAction('Browse Videos', self)
        browse_videos_action.triggered.connect(self.action_browse_video_triggered)
        browse_photos_action = QAction('Browse Photos', self)
        browse_photos_action.triggered.connect(self.action_browse_photo_triggered)
        self.driving_action = QAction(QIcon(asset.ICON_SELF_DRIVING_OFF), asset.STRING_START_SELF_DRIVING, self)
        self.driving_action.setShortcut('Up')
        self.driving_action.triggered.connect(self.action_self_driving_triggered)
        train_action = QAction(QIcon(asset.ICON_START_TRAIN), 'Start Training', self)
        load_action = QAction(QIcon(asset.ICON_OPEN), 'Load Model', self)
        load_action.setShortcut('Ctrl+O')
        load_action.triggered.connect(self.action_load_model_triggered)
        save_action = QAction(QIcon(asset.ICON_SAVE), 'Save Model', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.action_save_model_triggered)
        self.action_view_watch = QAction("Display Watch Region", self, checkable=True, checked=True)
        self.action_view_detect = QAction('Display Detect Region', self, checkable=True, checked=True)
        self.action_view_direction = QAction('Display Directions', self, checkable=True, checked=True)
        self.action_view_salient = QAction('Display Salient Map', self, checkable=True, checked=True)
        browse_home_page_action = QAction(QIcon(asset.ICON_GITHUB), 'Home Page', self)
        browse_home_page_action.triggered.connect(self.action_browse_home_page_triggered)
        show_usage_action = QAction('Usage', self)
        show_usage_action.triggered.connect(self.action_usage_triggered)

        # Draw menu
        menu = self.menuBar()
        menu_record = menu.addMenu('Record')
        menu_record.addAction(take_photo_action)
        menu_record.addAction(self.action_video_record)
        menu_record.addSeparator()
        menu_record.addAction(browse_photos_action)
        menu_record.addAction(browse_videos_action)
        menu_learn = menu.addMenu('Intelligence')
        menu_learn.addAction(self.driving_action)
        menu_learn.addAction(train_action)
        menu_learn.addSeparator()
        menu_learn.addAction(load_action)
        menu_learn.addAction(save_action)
        menu_view = menu.addMenu('View')
        menu_view.addAction(self.action_view_watch)
        menu_view.addAction(self.action_view_detect)
        menu_view.addAction(self.action_view_direction)
        menu_view.addAction(self.action_view_salient)
        menu_about = menu.addMenu('About')
        menu_about.addAction(browse_home_page_action)
        menu_about.addSeparator()
        menu_about.addAction(show_usage_action)

        # Draw toolbar
        tool_bar_record = self.addToolBar('Record')
        tool_bar_record.setMovable(False)
        tool_bar_record.addAction(take_photo_action)
        tool_bar_record.addAction(self.action_video_record)
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
            self.socket_control.settimeout(config.CONNECTION_TIME_OUT)
            self.socket_control.connect(address)
            self.label_ctl_status.setText('Control: Online')
        except socket.timeout as e:
            self.logger.error('Control: timed out')
            self.label_ctl_status.setText('Control: timed out')

    # Internal Events

    def keyPressEvent(self, event: QKeyEvent):
        # Ignore auto repeat
        if event.isAutoRepeat():
            return
        if event.key() in self.cmd_map.keys():
            # Save key status
            self.key_status[event.key()] = True
            # Append action
            self.action_stack.append(event.key())
            # Send action
            self.socket_control.send(self.cmd_map[self.action_stack[-1]])

    def keyReleaseEvent(self, event: QKeyEvent):
        # Ignore auto repeat
        if event.isAutoRepeat():
            return
        # Recover previous action
        if event.key() in self.cmd_map.keys():
            # Save key status
            self.key_status[event.key()] = False
            # Clear stack
            while len(self.action_stack) > 1 \
                    and self.key_status[self.action_stack[-1]] is False:
                self.action_stack.pop()
            self.socket_control.send(self.cmd_map[self.action_stack[-1]])

    def closeEvent(self, event: QCloseEvent):
        self.keep_streamer = False
        self.socket_control.close()
        self.thread_streamer.join()

    # Action Events

    def action_screen_shot_triggered(self):
        self.task_screen_shot = True

    def action_video_record_triggered(self):
        if self.task_video_record:
            self.task_video_record_stream.release()
            print(self.task_video_actions)
            with open(self.task_video_file_name + '.csv', 'w') as csv_file:
                wr = csv.writer(csv_file, delimiter=',')
                wr.writerows(self.task_video_actions)
            self.label_op_status.setText('Save video at ' + self.task_video_file_name + '.mkv')
            self.task_video_actions = None
            self.task_video_record = False
            # Reset action for start
            self.action_video_record.setText(asset.STRING_START_VIDEO_RECORD)
            self.action_video_record.setIcon(QIcon(asset.ICON_START_VIDEO_RECORD))
        else:
            self.task_video_record = True
            self.task_video_actions = []
            self.task_video_file_name = config.DIR_VIDEO + datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
            self.task_video_record_stream = cv2.VideoWriter(self.task_video_file_name + '.mkv', config.FOUR_CC, config.FPS,
                                                            (config.RESOLUTION_WIDTH, config.RESOLUTION_HEIGHT))
            # Reset action for stop
            self.action_video_record.setText(asset.STRING_STOP_VIDEO_RECORD)
            self.action_video_record.setIcon(QIcon(asset.ICON_STOP_VIDEO_RECORD))

    @staticmethod
    def action_browse_video_triggered():
        open_file(config.DIR_VIDEO)

    @staticmethod
    def action_browse_photo_triggered():
        open_file(config.DIR_PHOTO)

    def action_self_driving_triggered(self):
        if self.task_self_driving:
            self.task_self_driving = False
            self.action_stack.pop()
            self.socket_control.send(self.cmd_map[self.action_stack[-1]])
            # Reset action for start
            self.driving_action.setText(asset.STRING_START_SELF_DRIVING)
            self.driving_action.setIcon(QIcon(asset.ICON_SELF_DRIVING_OFF))
        else:
            self.task_self_driving = True
            self.action_stack.append(self.Direction.FORWARD)
            self.socket_control.send(self.cmd_map[self.action_stack[-1]])
            # Reset action for stop
            self.driving_action.setText(asset.STRING_STOP_SELF_DRIVING)
            self.driving_action.setIcon(QIcon(asset.ICON_SELF_DRIVING_ON))

    def action_load_model_triggered(self):
        file_name = QFileDialog.getOpenFileName(self, 'Load Model', './', 'Model (*.ckpt);;All Files (*.*)')

    def action_save_model_triggered(self):
        file_name = QFileDialog.getSaveFileName(self, 'Save Model', './', 'Model (*.ckpt);;All Files (*.*)')

    @staticmethod
    def action_browse_home_page_triggered():
        webbrowser.open(config.URL_HOME_PAGE)

    def action_usage_triggered(self):
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
        detector = LaneDetector()
        try:
            stream = cv2.VideoCapture(config.URL_STREAM)
            self.label_stream_status.setText('Stream: Online')
            while self.keep_streamer:
                ret, raw = stream.read()
                self.engine.set_frame(raw)
                watch = self.engine.watch_sample()
                # detect = self.engine.detect_sample()
                # _, detected = detector.detect(detect)
                # self.engine.set_detected(detected)
                frame = self.engine.render(draw_salient=self.action_view_salient.isChecked(),
                                           draw_detected=self.action_view_detect.isChecked(),
                                           draw_direction=self.action_view_direction.isChecked(),
                                           draw_watch=self.action_view_watch.isChecked())
                frame_display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                qimg = QImage(frame_display.data, frame_display.shape[1], frame_display.shape[0], QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                self.monitor.setPixmap(pixmap.scaled(self.monitor.width(), self.monitor.height(), Qt.KeepAspectRatio))
                # Screen shot
                if self.task_screen_shot:
                    file_name = config.DIR_PHOTO + datetime.utcnow().strftime('%Y%m%d%H%M%S%f') + '.png'
                    cv2.imwrite(file_name, raw)
                    self.label_op_status.setText('Save image at ' + file_name)
                    self.task_screen_shot = False
                # Video Record
                if self.task_video_record and self.action_stack[-1] != self.STOP:
                    self.task_video_record_stream.write(raw)
                    self.task_video_actions.append((len(self.task_video_actions), self.action_stack[-1]))
                # Self driving
                # if self.task_self_driving:
                #     pass
        except error.URLError as e:
            self.logger.error('Stream: %s' % e.reason)
            self.label_stream_status.setText('Stream: %s' % e.reason)
        finally:
            return


def select_white(image):
    converted = cv2.cvtColor(image, cv2.COLOR_RGB2HLS)
    # black color mask
    lower = np.uint8([  0, 200,   0])
    upper = np.uint8([255, 255, 255])
    white_mask = cv2.inRange(converted, lower, upper)
    # combine the mask
    masked = cv2.bitwise_and(image, image, mask=white_mask)
    return masked


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
