import os.path
import socket
import sys
import webbrowser
from datetime import datetime
from threading import Thread
import numpy as np
import config
import cv2
import util
from PyQt5 import Qt
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from car import Car
from dataset import DataFile
from editor import FrameEditor
from explorer import ExplorerForm
from form import ContentForm
from cnn import CNN
from train import TrainForm


class MainForm(ContentForm):

    def __init__(self):
        # Setup form
        super().__init__('../res/main.json')
        self.show()
        # Setup status
        self.camera_mode = False
        self.video_mode = False
        self.data_mode = False
        self.test_mode = False
        self.auto_mode = False
        self.key_stack = [Qt.Key_Space]
        self.key_status = {}
        self.total_frame = 0
        self.auto_frame = 0
        # Setup folder
        for dir in [config.DIR_DATA, config.video_dir, config.image_dir]:
            if not os.path.exists(dir):
                os.makedirs(dir)
        # Setup event
        self.setEvent("截图", self.action_camera)
        self.setEvent("录制视频", self.action_video)
        self.setEvent("录制数据", self.action_data)
        self.setEvent("性能测试", self.action_test)
        self.setEvent("打开截图位置", self.action_open_photo_folder)
        self.setEvent("打开视频位置", self.action_open_video_folder)
        self.setEvent("打开数据位置", self.action_open_data_folder)
        self.setEvent("浏览训练数据", self.open_data_explorer)
        self.setEvent("开始训练模型", self.open_train)
        self.setEvent("项目主页", self.action_browse_home_page)
        self.setEvent("帮助", self.action_usage)
        # Create sub forms
        self.cnn = CNN([config.observation_height, config.observation_width, config.observation_channel], model_file=config.model_file)
        self.explorer = ExplorerForm(self.cnn)
        self.train = TrainForm(self.cnn)
        # Connect
        try:
            self.car = Car(config.host)
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

    def closeEvent(self, event: QCloseEvent):
        self.keep_streamer = False
        # self.keep_sensor = False
        self.thread_streamer.join()
        # self.thread_sensor.join()

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
            self.action_set["录制视频"].setIcon(QIcon("../res/video.png"))
        else:
            file_name = config.video_dir + datetime.utcnow().strftime('%Y-%m-%dL%H:%M:%S:%f') + '.mkv'
            self.setText("状态栏", "开始录制视频：" + file_name)
            self.video_writer = cv2.VideoWriter(file_name, config.video_fourcc,
                                                config.stream_fps, (config.stream_width, config.stream_height))
            self.video_mode = True
            # Reset action to [stop]
            self.action_set["录制视频"].setText("停止录制视频")
            self.action_set["录制视频"].setIcon(QIcon("../res/video_stop.png"))

    def action_data(self):
        if self.data_mode:
            self.data_mode = False
            # Save video
            self.data_file = DataFile(config.data_file)
            self.data_file.append(self.data_observations, self.data_actions)
            self.setText("状态栏", "视频录制完成：" + file_name)
            # Reset action to [start]
            self.action_set["录制数据"].setText("录制数据")
            self.action_set["录制数据"].setIcon(QIcon("../res/data.png"))
        else:
            self.setText("状态栏", "开始录制数据")
            self.data_observations = []
            self.data_actions = []
            self.data_mode = True
            # Reset action to [stop]
            self.action_set["录制数据"].setText("停止录制数据")
            self.action_set["录制数据"].setIcon(QIcon("../res/data_stop.png"))

    def action_test(self):
        if self.test_mode:
            self.test_mode = False
            if self.total_frame > 0:
                self.setText("状态栏", "性能指标：%f" % (self.auto_frame/self.total_frame))
            self.auto_frame = 0
            self.total_frame = 0
            self.action_set["性能测试"].setText("性能测试")
            self.action_set["性能测试"].setIcon(QIcon("../res/test.png"))
        else:
            self.test_mode = True
            self.action_set["性能测试"].setText("停止性能测试")
            self.action_set["性能测试"].setIcon(QIcon("../res/test_stop.png"))

    @staticmethod
    def action_open_photo_folder():
        util.open_file_xdg(config.image_dir)

    @staticmethod
    def action_open_video_folder():
        util.open_file_xdg(config.video_dir)

    @staticmethod
    def action_open_data_folder():
        util.open_file_xdg(config.DIR_DATA)

    def open_data_explorer(self):
        self.explorer.show()

    def open_train(self):
        self.train.show()
        self.cnn.load(config.model_file)

    @staticmethod
    def action_browse_home_page():
        webbrowser.open('https://github.com/ZhangZhenghao/raspberry-autonomous')

    def action_usage(self):
        qbox = QMessageBox(self)
        qbox.setWindowTitle('使用帮助')
        qbox.setText('W\t前进\nS\t后退\nA\t左转\nD\t右转\n空格\t刹车\n↑\t自动驾驶模式')
        qbox.show()

    def streamer(self):
        frame_editor = FrameEditor(config.stream_height,
                                   config.stream_width,
                                   config.stream_channel,
                                   config.observation_height,
                                   config.observation_width)

        while self.keep_streamer:
            ret, frame = self.car.read_camera()
            if not ret:
                self.setText("状态栏", "视频信号中断")
                break
            frame_editor.set_frame(frame)
            observation = frame_editor.get_observation()
            # # Predict actions
            probs, salients = self.cnn.predict([observation])
            prob = probs[0]
            salient = salients[0]
            action = np.argmax(prob)
            frame_editor.set_direction(prob)
            frame_editor.set_salient(salient)
            frame = frame_editor.render(draw_salient=self.isChecked("显示观测区域活跃度"),
                                  draw_prob=self.isChecked("显示预测置信度"),
                                  draw_border=self.isChecked("显示观测区域边框"))
            # Convert image
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            self.setContent(QPixmap.fromImage(image))
            # Camera mode
            if self.camera_mode:
                file_name = config.image_dir + datetime.utcnow().strftime('%Y-%m-%dL%H:%M:%S:%f') + '.png'
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
            # Self driving
            if self.auto_mode:
                self.car.step(action)
            if self.test_mode:
                if self.auto_mode:
                    self.auto_frame += 1
                    self.total_frame += 1
                elif self.key_stack[-1] != Qt.Key_Space:
                    self.total_frame += 1


if __name__ == '__main__':
    app = QApplication(sys.argv)
    form = MainForm()
    sys.exit(app.exec_())
