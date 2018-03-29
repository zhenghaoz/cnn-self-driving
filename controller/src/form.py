import json

from PyQt5 import Qt, QtGui
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class QFlexLabel(QLabel):

    def __init__(self):
        super().__init__()
        self.setMinimumSize(1,1)

    def setPixmap(self, a0: QtGui.QPixmap):
        super().setPixmap(a0.scaled(self.size(), Qt.KeepAspectRatio))

    def resizeEvent(self, a0: QtGui.QResizeEvent):
        if self.pixmap():
            super().setPixmap(self.pixmap().scaled(self.size(), Qt.KeepAspectRatio))


class ContentForm(QMainWindow):

    def __init__(self, layout_file: str):
        super().__init__()
        # Load configuration
        with open(layout_file, 'r') as file:
            layout = json.load(file)
        # Setup action
        self.action_set = {}
        action_layout = layout["action"]
        for item_layout in action_layout:
            title = item_layout["title"]
            self.action_set[title] = QAction(title, self)
            if "checkable" in item_layout.keys():
                self.action_set[title].setCheckable(item_layout["checkable"])
            if "checked" in item_layout.keys():
                self.action_set[title].setChecked(item_layout["checked"])
            if "icon" in item_layout.keys():
                self.action_set[title].setIcon(QIcon(item_layout["icon"]))
        # Setup menu
        menu_layout = layout['menu']
        menu_bar = self.menuBar()
        for item_layout in menu_layout:
            menu_item = menu_bar.addMenu(item_layout["title"])
            if "action" in item_layout.keys():
                for action in item_layout["action"]:
                    if action == "-":
                        menu_item.addSeparator()
                    else:
                        menu_item.addAction(self.action_set[action])
        # Setup toolbar
        toolbar_layout = layout["toolbar"]
        for item_layout in toolbar_layout:
            toobar_item = self.addToolBar(item_layout["title"])
            if "movable" in item_layout.keys():
                toobar_item.setMovable(item_layout["movable"])
            if "action" in item_layout.keys():
                for action in item_layout["action"]:
                    toobar_item.addAction(self.action_set[action])
        # Setup status bar
        self.statusbar_set = {}
        statusbar_layout = layout["status"]
        for item_layout in statusbar_layout:
            statusbar_item = QLabel()
            statusbar_item.setText(item_layout["text"])
            self.statusBar().addPermanentWidget(statusbar_item, item_layout["stretch"])
            self.statusbar_set[item_layout["title"]] = statusbar_item
        # Setup form
        self.setWindowTitle(layout["title"])
        self.setWindowIcon(QIcon(layout["icon"]))
        if "center" in layout.keys() and layout["center"]:
            screen_size = QDesktopWidget().screenGeometry()
            frame_size = self.frameSize()
            self.move((screen_size.width() / 2) - (frame_size.width() / 2),
                      (screen_size.height() / 2) - (frame_size.height() / 2))
        # Setup content
        self.content_label = QFlexLabel()
        self.setCentralWidget(self.content_label)
        self.content_label.setStyleSheet('background-color: ' + layout["background-color"])
        self.content_label.setAlignment(Qt.AlignCenter)
        self.setContent(QPixmap(layout["default-content"]))

    def setContent(self, content: QPixmap):
        self.content = content
        self.content_label.setPixmap(self.content)

    def setEvent(self, action, func):
        self.action_set[action].triggered.connect(func)

    def setText(self, statusbar, text):
        self.statusbar_set[statusbar].setText(text)
