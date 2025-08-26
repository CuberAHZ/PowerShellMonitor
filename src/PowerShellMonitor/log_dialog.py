import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QPushButton, QTextEdit, QMessageBox)
from PySide6.QtGui import QIcon, QFont, QTextCursor
from PySide6.QtCore import Qt

from utils import get_app_dir


class LogDialog(QDialog):
    """输入日志"""

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
        """创建程序图标"""
        from PySide6.QtGui import QPixmap, QPainter, QColor
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(50, 150, 250))
        painter.drawEllipse(4, 4, 24, 24)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "PS")
        painter.end()
        return pixmap

    def clear_log(self):
        """清除日志"""
        self.text_edit.clear()
        log_file = os.path.join(get_app_dir(), "powershell_output.log")
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("")
        except Exception as e:
            QMessageBox.critical(self, "PowerShell 输出日志", f"清空日志失败: {e}")

    def append_text(self, text):
        """添加文本"""
        self.text_edit.append(text)
        # 自动滚动到底部
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)
