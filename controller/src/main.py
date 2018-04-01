import os.path
import socket
import sys
import time
import webbrowser
from datetime import datetime
from threading import Thread

import cv2
from PyQt5 import Qt
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import config
import util
from car import Car
from editor import FrameEditor
from form import ContentForm
from dataset import DataFile
from policy import Network, Policy
from explorer import ExplorerForm

class MainForm(ContentForm):

    def __init__(self):
        # Setup form
        super().__init__('../res/main.json')
        self.show()
        # Setup status
        self.camera_mode = False
        self.video_mode = False
        self.data_mode = False
        self.auto_mode = False
        self.key_stack = [Qt.Key_Space]
        self.key_status = {}
        self.left_sensor = 0
        self.right_sensor = 0
        # Setup folder
        for dir in [config.DIR_DATA, config.DIR_VIDEO, config.DIR_PHOTO]:
            if not os.path.exists(dir):
                os.makedirs(dir)
        # Setup event
        self.setEvent("截图", self.action_camera)
        self.setEvent("录制视频", self.action_video)
        self.setEvent("录制数据", self.action_data)
        self.setEvent("打开截图位置", self.action_open_photo_folder)
        self.setEvent("打开视频位置", self.action_open_video_folder)
        self.setEvent("打开数据位置", self.action_open_data_folder)
        self.setEvent("浏览训练数据", self.open_data_explorer)
        self.setEvent("项目主页", self.action_browse_home_page)
        self.setEvent("帮助", self.action_usage)
        self.policy = Policy('model/driver.ckpt', '../data/m')
        self.explorer = ExplorerForm(self.policy.policy)
        # Connect
        try:
            self.car = Car('192.168.1.1')
            self.setText("状态栏", "连接成功")
            self.key_map = {
                Qt.Key_Space: self.car.stop,
                Qt.Key_W: self.car.forward,
                Qt.Key_S: self.car.backward,
                Qt.Key_A: self.car.turn_left,
                Qt.Key_D: self.car.turn_right
            }
        except socket.timeout as e:
            self.setText("状态栏", "连接超时")
        except socket.error as e:
            self.setText("状态栏", e.strerror)
        # Start streamer
        self.keep_streamer = True
        self.thread_streamer = Thread(target=self.streamer)
        self.thread_streamer.start()
        self.keep_sensor = True
        self.thread_sensor = Thread(target=self.sensor)
        self.thread_sensor.start()

    def closeEvent(self, event: QCloseEvent):
        self.keep_streamer = False
        self.keep_sensor = False
        self.thread_streamer.join()
        self.thread_sensor.join()

    def keyPressEvent(self, event: QKeyEvent):
        # Ignore auto repeat
        if event.isAutoRepeat():
            return
        if event.key() == Qt.Key_Up:
            self.auto_mode = True
            return
        if event.key() in self.key_map.keys():
            # Save key status
            self.key_status[event.key()] = True
            # Append action
            self.key_stack.append(event.key())
            # Send action
            self.key_map[self.key_stack[-1]]()

    def keyReleaseEvent(self, event: QKeyEvent):
        # Ignore auto repeat
        if event.isAutoRepeat():
            return
        if event.key() == Qt.Key_Up:
            self.auto_mode = False
            self.car.stop()
            return
        # Recover previous action
        if event.key() in self.key_map.keys():
            # Save key status
            self.key_status[event.key()] = False
            # Clear stack
            while len(self.key_stack) > 1 \
                    and self.key_status[self.key_stack[-1]] is False:
                self.key_stack.pop()
            self.key_map[self.key_stack[-1]]()

    def action_camera(self):
        self.camera_mode = True

    def action_video(self):
        if self.video_mode:
            self.video_mode = False
            # Save video
            self.video_writer.release()
            self.setText("状态栏", "视频录制完成")
            # Reset action to [start]
            self.action_set["录制视频"].setText("录制视频")
            self.action_set["录制视频"].setIcon(QIcon("../res/start_record.png"))
        else:
            file_name = config.DIR_VIDEO + datetime.utcnow().strftime('%Y-%m-%dL%H:%M:%S:%f') + '.mkv'
            self.setText("状态栏", "开始录制视频：" + file_name)
            self.video_writer = cv2.VideoWriter(file_name, config.STREAN_FOURCC,
                                                config.STREAM_FPS, (config.STREAM_WIDTH, config.STREAM_HEIGHT))
            self.video_mode = True
            # Reset action to [stop]
            self.action_set["录制视频"].setText("停止录制视频")
            self.action_set["录制视频"].setIcon(QIcon("../res/stop_record.png"))

    def action_data(self):
        if self.data_mode:
            self.data_mode = False
            # Save video
            file_name = config.DIR_DATA + config.DATA_FILE
            self.data_file = DataFile(file_name)
            self.data_file.append(self.data_observations, self.data_actions)
            self.setText("状态栏", "视频录制完成：" + file_name)
            # Reset action to [start]
            self.action_set["录制数据"].setText("录制数据")
            self.action_set["录制数据"].setIcon(QIcon("../res/start_record.png"))
        else:
            self.setText("状态栏", "开始录制数据")
            self.data_observations = []
            self.data_actions = []
            self.data_mode = True
            # Reset action to [stop]
            self.action_set["录制数据"].setText("停止录制数据")
            self.action_set["录制数据"].setIcon(QIcon("../res/stop_record.png"))

    @staticmethod
    def action_open_photo_folder():
        util.open_file_xdg(config.DIR_PHOTO)

    @staticmethod
    def action_open_video_folder():
        util.open_file_xdg(config.DIR_VIDEO)

    @staticmethod
    def action_open_data_folder():
        util.open_file_xdg(config.DIR_DATA)

    def open_data_explorer(self):
        self.explorer.show()

    @staticmethod
    def action_browse_home_page():
        webbrowser.open('https://github.com/ZhangZhenghao/raspberry-autonomous')

    def action_usage(self):
        qbox = QMessageBox(self)
        qbox.setWindowTitle('使用帮助')
        qbox.setText('W\t前进\nS\t后退\nA\t左转\nD\t右转\n空格\t刹车\n↑\t自动驾驶模式')
        qbox.show()

    def sensor(self):
        while self.keep_sensor:
            self.left_sensor, self.right_sensor = 0, 0 #self.car.read_sensor()
            time.sleep(0.02)

    def streamer(self):
        frame_editor = FrameEditor(config.STREAM_HEIGHT,
                             config.STREAM_WIDTH,
                             config.STREAM_CHANNEL,
                             Network.INPUT_HEIGHT,
                             Network.INPUT_WIDTH)

        while self.keep_streamer:
            ret, frame = self.car.read_camera()
            if not ret:
                self.setText("状态栏", "视频信号中断")
                break
            frame_editor.set_frame(frame)
            observation = frame_editor.get_observation()
            # # Predict actions
            action, prob, salient = self.policy.get_action(observation, self.left_sensor, self.right_sensor, self.auto_mode)
            frame_editor.set_direction(prob)
            frame_editor.set_salient(salient)
            frame_editor.set_sensor(self.left_sensor == 1, self.right_sensor == 1)
            frame = frame_editor.render(draw_salient=self.isChecked("显示观测区域活跃度"),
                                  draw_prob=self.isChecked("显示预测置信度"),
                                  draw_border=self.isChecked("显示观测区域边框"),
                                        draw_sensor=self.isChecked("显示红外线传感器状态"))
            # Convert image
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            self.setContent(QPixmap.fromImage(image))
            # Camera mode
            if self.camera_mode:
                file_name = config.DIR_PHOTO + datetime.utcnow().strftime('%Y-%m-%dL%H:%M:%S:%f') + '.png'
                cv2.imwrite(file_name, frame)
                self.setText("状态栏", "截图保存至：%s" % file_name)
                self.camera_mode = False
            # Video Record
            if self.video_mode:
                self.video_writer.write(frame)
            # Data Record
            if self.data_mode and self.key_stack[-1] in [Qt.Key_A, Qt.Key_D, Qt.Key_W]:
                self.data_observations.append(observation)
                action_map = {Qt.Key_A:0, Qt.Key_D:1, Qt.Key_W:2}
                self.data_actions.append(action_map[self.key_stack[-1]])
            # # Self driving
            # if self.task_self_driving:
            #     self.car.step(action)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    form = MainForm()
    sys.exit(app.exec_())
