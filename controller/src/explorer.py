import math

import cv2
import numpy as np
from PyQt5 import Qt
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import config
from dataset import DataFile
from form import ContentForm


class ExplorerForm(ContentForm):

    def __init__(self, model):
        super().__init__('../res/explorer.json')
        self.model = model
        # Setup progress bars
        self.progress_bars = []
        for _ in range(3):
            progress_bar = QProgressBar(self)
            progress_bar.setOrientation(Qt.Vertical)
            self.progress_bars.append(progress_bar)
        self.progress_bars[0].setGeometry(10, 10, 20, 70)
        self.progress_bars[2].setGeometry(40, 10, 20, 70)
        self.progress_bars[1].setGeometry(70, 10, 20, 70)
        # Setup action icons
        action_labels = []
        for _ in range(3):
            action_label = QLabel(self)
            action_label.setScaledContents(True)
            action_labels.append(action_label)
        action_labels[0].setGeometry(10, 90, 20, 20)
        action_labels[0].setPixmap(QPixmap("../res/turn_left.png"))
        action_labels[1].setGeometry(40, 90, 20, 20)
        action_labels[1].setPixmap(QPixmap("../res/forward.png"))
        action_labels[2].setGeometry(70, 90, 20, 20)
        action_labels[2].setPixmap(QPixmap("../res/turn_right.png"))
        # Setup check labels
        self.check_labels = []
        for _ in range(3):
            check_label = QLabel(self)
            check_label.setScaledContents(True)
            check_label.setPixmap(QPixmap("../res/check.png"))
            self.check_labels.append(check_label)
        self.check_labels[0].setGeometry(10, 120, 20, 20)
        self.check_labels[2].setGeometry(40, 120, 20, 20)
        self.check_labels[1].setGeometry(70, 120, 20, 20)
        # Setup events
        self.setEvent("上一张", self.prev_image)
        self.setEvent("下一张", self.next_image)
        self.setEvent("查找错误分类图片", self.find_miss)
        self.setEvent("删除", self.delete_image)
        self.setEvent("保存", self.save_image)

    def showEvent(self, a0: QShowEvent):
        # Load data
        self.data_file = DataFile(config.data_file)
        self.data_obs = self.data_file.data['observation']
        self.data_act = self.data_file.data['action']
        self.viewer_index = 0
        if len(self.data_obs) > 0:
            self.data_pred = self.predict(self.data_obs)
            self.data_miss = np.where(self.data_act != np.argmax(self.data_pred, 1))[0]
            self.load_image()

    def load_image(self):
        assert len(self.data_obs) == len(self.data_act)
        assert len(self.data_obs) == len(self.data_pred)
        # Load image
        obs = self.data_obs[self.viewer_index]
        image = QImage(obs.data, obs.shape[1], obs.shape[0], obs.shape[1]*3, QImage.Format_RGB888)
        super().setContent(QPixmap(image))
        # Load action
        act = self.data_act[self.viewer_index]
        for check_label in self.check_labels:
            check_label.setVisible(False)
        self.check_labels[act].setVisible(True)
        # Load prediction
        pred = self.data_pred[self.viewer_index]
        assert len(pred) == len(self.progress_bars)
        for i in range(len(pred)):
            self.progress_bars[i].setValue(pred[i]*100)

    def prev_image(self):
        if len(self.data_obs) == 0:
            return
        self.viewer_index = (self.viewer_index - 1) % len(self.data_obs)
        self.load_image()

    def next_image(self):
        if len(self.data_obs) == 0:
            return
        self.viewer_index = (self.viewer_index + 1) % len(self.data_obs)
        self.load_image()

    def find_miss(self):
        if len(self.data_obs) == 0:
            return
        if len(self.data_miss) == 0:
            QMessageBox.information(self, "不存在错误预测", "所以的图像预测结果都是正确的")
        else:
            if not np.any(self.data_miss > self.viewer_index):
                self.viewer_index = 0
            self.viewer_index = self.data_miss[self.data_miss > self.viewer_index][0]
            self.load_image()

    def delete_image(self):
        if len(self.data_obs) == 0:
            return
        response = QMessageBox.question(self, "确认删除", "确认从训练数据中删除当前图片？", QMessageBox.Yes, QMessageBox.No)
        if response == QMessageBox.Yes:
            self.data_file.remove(self.viewer_index)
            del self.data_pred[self.viewer_index]
            self.next_image()

    def save_image(self):
        if len(self.data_obs) == 0:
            return
        file_name, _ = QFileDialog.getSaveFileName(self, "保存图像")
        if file_name:
            obs = self.data_obs[self.viewer_index]
            cv2.imwrite(file_name, obs)

    def predict(self, images, batch_size=128):
        num_total = len(images)
        num_batch = int(math.ceil(num_total / batch_size))
        preds = np.zeros([0,3])
        for i in range(num_batch):
            batch_images = images[i*batch_size:(i+1)*batch_size]
            batch_predict = self.model.predict(batch_images)[0]
            preds = np.concatenate([preds, batch_predict])
        return preds
