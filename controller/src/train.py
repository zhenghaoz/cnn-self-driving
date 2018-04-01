from PyQt5 import Qt
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import config
from dataset import DataFile
from policy import Network


class TrainForm(QMainWindow):

    def __init__(self, model: Network):
        super().__init__()
        self.model = model
        # Set title
        self.setWindowTitle("训练模型")
        # Setup panel
        tool_panel = QToolBar()
        self.addToolBar(Qt.LeftToolBarArea, tool_panel)
        tool_panel.setMovable(False)
        # Training options
        tool_panel.addWidget(QLabel("训练批量"))
        self.spin_batch_size = QSpinBox()
        self.spin_batch_size.setMinimum(100)
        self.spin_batch_size.setMaximum(1000)
        self.spin_batch_size.setSingleStep(1)
        self.spin_batch_size.setValue(100)
        tool_panel.addWidget(self.spin_batch_size)
        tool_panel.addWidget(QLabel("训练次数"))
        self.spin_iter = QSpinBox()
        self.spin_iter.setMinimum(100)
        self.spin_iter.setMaximum(100000)
        self.spin_iter.setSingleStep(1)
        self.spin_iter.setValue(100)
        tool_panel.addWidget(self.spin_iter)
        tool_panel.addWidget(QLabel("报告间隔"))
        self.spin_print_iter = QSpinBox()
        self.spin_print_iter.setMinimum(10)
        self.spin_print_iter.setMaximum(1000)
        self.spin_print_iter.setSingleStep(100)
        self.spin_print_iter.setValue(10)
        tool_panel.addWidget(self.spin_print_iter)
        self.check_incremental = QCheckBox("增量训练")
        self.check_incremental.setChecked(True)
        tool_panel.addWidget(self.check_incremental)
        self.btn_start_train = QPushButton("开始训练")
        self.btn_start_train.clicked.connect(self.train_model)
        tool_panel.addWidget(self.btn_start_train)
        self.btn_save_model = QPushButton("保存模型")
        self.btn_save_model.clicked.connect(self.save_model)
        self.btn_save_model.setDisabled(True)
        tool_panel.addWidget(self.btn_save_model)
        tool_panel.addSeparator()
        # Visualization options
        tool_panel.addWidget(QLabel("可视化选项"))
        self.check_plot_loss = QCheckBox("可视化损失函数值")
        self.check_plot_loss.setChecked(True)
        tool_panel.addWidget(self.check_plot_loss)
        self.check_plot_acc = QCheckBox("可视化准确率")
        self.check_plot_acc.setChecked(True)
        tool_panel.addWidget(self.check_plot_acc)
        self.btn_save_image = QPushButton("保存图片")
        self.btn_save_image.clicked.connect(self.save_image)
        tool_panel.addWidget(self.btn_save_image)
        # Setup log board
        self.label_log = QLabel("")
        tool_panel.addSeparator()
        tool_panel.addWidget(self.label_log)
        # Setup progress bar
        tool_progress = QToolBar()
        self.addToolBar(Qt.BottomToolBarArea, tool_progress)
        self.progress_bar = QProgressBar()
        tool_progress.addWidget(self.progress_bar)
        tool_progress.setMovable(False)
        # Setup canvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.setCentralWidget(self.canvas)
        # Center windows
        screen_size = QDesktopWidget().screenGeometry()
        frame_size = self.frameSize()
        self.move((screen_size.width() / 2) - (frame_size.width() / 2),
                  (screen_size.height() / 2) - (frame_size.height() / 2))

    def setLog(self, text):
        self.label_log.setText(text)

    def train_model(self):
        # Load data
        self.setLog("正在加载数据...")
        data_file = DataFile(config.DIR_DATA + config.DATA_FILE)
        train_obs, train_act, test_obs, test_act = data_file.gen_train_set()
        # Clear history
        self.loss_hist = []
        self.acc_hist = []
        # Initialize network
        if not self.check_incremental:
            self.setLog("初始化模型")
            self.model.initialize()
        # Start train
        self.setLog("正在训练模型...")
        self.model.fit(train_obs, train_act, test_obs, test_act,
                       batch_size=self.spin_batch_size.value(),
                       iters=self.spin_iter.value(),
                       print_iters=self.spin_print_iter.value(),
                       report_func=self.report_progress)
        self.setLog("训练完成")
        self.btn_save_model.setDisabled(False)

    def report_progress(self, iter, hist):
        self.progress_bar.setValue((iter+1) / self.spin_iter.value() * 100)
        if self.check_plot_loss.checkState() and self.check_plot_acc.checkState():
            # Plot loss
            loss = hist['loss']
            loss_plot = self.figure.add_subplot(211)
            loss_plot.clear()
            loss_plot.plot(loss, '*-')
            # Plot acc
            train_acc = hist['train_acc']
            val_acc = hist['val_acc']
            acc_plot = self.figure.add_subplot(212)
            acc_plot.clear()
            acc_plot.plot(train_acc, '*-')
            acc_plot.plot(val_acc, '*-')
            acc_plot.legend(["train accuracy", "test accuracy"])
        elif self.check_plot_loss.checkState():
            # Plot loss
            loss = hist['loss']
            loss_plot = self.figure.add_subplot(111)
            loss_plot.clear()
            loss_plot.plot(loss, '*-')
        elif self.check_plot_acc.checkState():
            # Plot acc
            train_acc = hist['train_acc']
            val_acc = hist['val_acc']
            acc_plot = self.figure.add_subplot(111)
            acc_plot.clear()
            acc_plot.plot(train_acc, '*-')
            acc_plot.plot(val_acc, '*-')
            acc_plot.legend(["train accuracy", "test accuracy"])
        self.canvas.draw()

    def save_model(self):
        self.btn_save_model.setDisabled(True)
        self.model.save(config.MODEL_FILE)

    def save_image(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "保存图片")
        if file_name:
            canvas_size = self.canvas.size()
            canvas_width, canvas_height = canvas_size.width(), canvas_size.height()
            image = QImage(self.canvas.buffer_rgba(), canvas_width, canvas_height, QImage.Format_RGBA8888)
            image.save(file_name)
