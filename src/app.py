import csv
import os
import platform
import socket
import subprocess
import sys
import webbrowser
from datetime import datetime
from logging import Logger
from threading import Thread
from urllib import error

import cv2
import numpy as np
from PyQt5 import Qt
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import asset
import config
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

        self.engine = DisplayEngine(config.MONITOR_HEIGHT,
                                    config.MONITOR_WIDTH,
                                    config.MONITOR_CHANNEL,
                                    PilotNet.INPUT_HEIGHT,
                                    PilotNet.INPUT_WIDTH)

        self.net = PilotNet()
        self.net.load('model/driver.ckpt')

        # Initialize tasks
        self.task_screen_shot = False
        self.task_video_record = False
        self.task_self_driving = False
        self.task_video_frames = None
        self.task_video_actions = None
        self.task_video_file_name = None
        self.self_driving_clock = 0

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
        status_height = 20
        form_height = monitor_y + config.MONITOR_HEIGHT + status_height
        form_width = config.MONITOR_WIDTH

        # Draw monitor
        self.pixmap = QPixmap(asset.IMAGE_OFFLINE)
        self.monitor = QLabel(self)
        self.monitor.setStyleSheet('background-color: black')
        self.monitor.setGeometry(monitor_x, monitor_y, config.MONITOR_WIDTH, config.MONITOR_HEIGHT)
        self.monitor.setAlignment(Qt.AlignCenter)
        self.monitor.setPixmap(self.pixmap.scaled(self.monitor.width(), self.monitor.height(), Qt.KeepAspectRatio))

        # Setup actions
        take_photo_action = QAction(QIcon(asset.ICON_CAMERA), 'Screen Shot', self)
        take_photo_action.triggered.connect(self.action_screen_shot_triggered)
        self.action_video_record = QAction(QIcon(asset.ICON_START_RECORD), asset.STRING_START_RECORD, self)
        self.action_video_record.triggered.connect(self.action_video_record_triggered)
        browse_videos_action = QAction('Browse Data', self)
        browse_videos_action.triggered.connect(self.action_browse_video_triggered)
        browse_photos_action = QAction('Browse Photos', self)
        browse_photos_action.triggered.connect(self.action_browse_photo_triggered)
        train_action = QAction(QIcon(asset.ICON_START_TRAIN), 'Start Training', self)
        load_action = QAction(QIcon(asset.ICON_OPEN), 'Load Model', self)
        load_action.setShortcut('Ctrl+O')
        load_action.triggered.connect(self.action_load_model_triggered)
        save_action = QAction(QIcon(asset.ICON_SAVE), 'Save Model', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.action_save_model_triggered)
        self.action_view_watch = QAction("Display Watch Region", self, checkable=True, checked=True)
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
        menu_learn.addAction(train_action)
        menu_learn.addSeparator()
        menu_learn.addAction(load_action)
        menu_learn.addAction(save_action)
        menu_view = menu.addMenu('View')
        menu_view.addAction(self.action_view_watch)
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
        if event.key() == Qt.Key_Up:
            self.task_self_driving = True
            self.self_driving_clock = 0
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
        if event.key() == Qt.Key_Up:
            self.task_self_driving = False
            self.socket_control.send(self.cmd_map[Qt.Key_Space])
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
            self.task_video_record = False
            # Save data
            file_name = config.DIR_DATA + datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
            np.savez_compressed(file_name, image=self.task_video_frames, label=self.task_video_actions)
            self.label_op_status.setText('Save data at ' + file_name + '.npz')
            # Reset data
            self.task_video_frames = None
            self.task_video_actions = None
            # Reset action for start
            self.action_video_record.setText(asset.STRING_START_RECORD)
            self.action_video_record.setIcon(QIcon(asset.ICON_START_RECORD))
        else:
            self.task_video_actions = []
            self.task_video_frames = []
            self.task_video_record = True
            # Reset action for stop
            self.action_video_record.setText(asset.STRING_STOP_RECORD)
            self.action_video_record.setIcon(QIcon(asset.ICON_STOP_RECORD))

    @staticmethod
    def action_browse_video_triggered():
        open_file_xdg(config.DIR_DATA)

    @staticmethod
    def action_browse_photo_triggered():
        open_file_xdg(config.DIR_PHOTO)

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
        try:
            stream = cv2.VideoCapture(config.URL_STREAM)
            self.label_stream_status.setText('Stream: Online')
            while self.keep_streamer:
                ret, raw = stream.read()
                if not ret:
                    print('Panic')
                self.engine.set_frame(raw)
                watch = self.engine.watch_sample()
                # Predict actions
                actions, salients = self.net.predict(np.asarray([watch]))
                self.engine.set_direction(actions[0])
                self.engine.set_salient(salients[0,:,:,0])
                frame = self.engine.render(draw_salient=self.action_view_salient.isChecked(),
                                           draw_direction=self.action_view_direction.isChecked(),
                                           draw_watch=self.action_view_watch.isChecked())
                frame_display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                qimg = QImage(frame_display.data, frame_display.shape[1], frame_display.shape[0], QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                self.monitor.setPixmap(pixmap)
                # Screen shotwwww
                if self.task_screen_shot:
                    file_name = config.DIR_PHOTO + datetime.utcnow().strftime('%Y%m%d%H%M%S%f') + '.png'
                    cv2.imwrite(file_name, watch)
                    self.label_op_status.setText('Save image at ' + file_name)
                    self.task_screen_shot = False
                # Video Record
                if self.task_video_record and self.action_stack[-1] in [Qt.Key_A, Qt.Key_D, Qt.Key_W]:
                    self.task_video_frames.append(watch)
                    self.task_video_actions.append(self.action_stack[-1])
                # Self driving
                if self.task_self_driving:
                    keys = [Qt.Key_A, Qt.Key_D, Qt.Key_W]
                    action = np.argmax(actions[0])
                    self.socket_control.send(self.cmd_map[keys[action]])
                    self.self_driving_clock = (self.self_driving_clock + 1) % 30
        except error.URLError as e:
            self.logger.error('Stream: %s' % e.reason)
            self.label_stream_status.setText('Stream: %s' % e.reason)
        finally:
            return


def open_file_xdg(path):
    """
    Open file or directory in system's file manager.
    :param path: file/directory path
    """
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
