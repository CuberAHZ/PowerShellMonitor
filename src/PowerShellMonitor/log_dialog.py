from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QPushButton, QTextEdit)
from PySide6.QtGui import QIcon, QFont, QTextCursor
from PySide6.QtCore import Qt


class LogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PowerShell 输出日志")
        self.setGeometry(100, 100, 800, 600)

        self.setWindowIcon(QIcon(self.create_icon()))

        layout = QVBoxLayout()

        # 日志显示区域
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier New", 10))
        layout.addWidget(self.text_edit)

        # 按钮区域
        button_layout = QHBoxLayout()
        self.clear_button = QPushButton("清空日志")
        self.close_button = QPushButton("关闭")
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 连接信号
        self.clear_button.clicked.connect(self.clear_log)
        self.close_button.clicked.connect(self.accept)

    def create_icon(self):
        # 创建一个简单的程序图标
        from PySide6.QtGui import QPixmap, QPainter, QColor
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))  # 透明背景
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(50, 150, 250))
        painter.drawEllipse(4, 4, 24, 24)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "PS")
        painter.end()
        return pixmap

    def clear_log(self):
        self.text_edit.clear()

    def append_text(self, text):
        self.text_edit.append(text)
        # 自动滚动到底部
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)
