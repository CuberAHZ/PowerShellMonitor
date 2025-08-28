from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QTextEdit, QCheckBox, QPushButton,
                               QGroupBox, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon


class TaskEditDialog(QDialog):
    """任务编辑器"""

    def __init__(self, task_data=None, parent=None):
        super().__init__(parent)
        self.task_data = task_data or {}
        self.is_new_task = not task_data

        self.setWindowTitle("PSMonitor - 编辑任务 - {}".format(task_data["name"]) if task_data else "PSMonitor - 添加新任务")
        self.setGeometry(200, 200, 600, 500)

        self.init_ui()
        self.load_task_data()

    def init_ui(self):
        layout = QVBoxLayout()

        self.setWindowIcon(QIcon(self.create_icon()))

        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QVBoxLayout()

        # 任务名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("任务名称:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        basic_layout.addLayout(name_layout)

        # 启用复选框
        self.enabled_check = QCheckBox("启用此任务")
        self.enabled_check.setChecked(True)
        basic_layout.addWidget(self.enabled_check)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # PowerShell命令组
        ps_group = QGroupBox("PowerShell 命令")
        ps_layout = QVBoxLayout()

        self.ps_edit = QTextEdit()
        self.ps_edit.setPlaceholderText("请输入 PowerShell 命令或可执行文件路径...")
        self.ps_edit.setMinimumHeight(150)
        ps_layout.addWidget(self.ps_edit)

        # 示例按钮
        example_btn = QPushButton("插入示例命令")
        example_btn.clicked.connect(self.insert_example)
        ps_layout.addWidget(example_btn)

        ps_group.setLayout(ps_layout)
        layout.addWidget(ps_group)

        # 选项组
        options_group = QGroupBox("选项")
        options_layout = QVBoxLayout()

        self.timestamp_check = QCheckBox("在日志中添加时间戳")
        self.timestamp_check.setChecked(True)
        options_layout.addWidget(self.timestamp_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")

        self.save_btn.clicked.connect(self.save_task)
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def create_icon(self):
        """创建图标"""
        from PySide6.QtGui import QPixmap, QPainter, QColor
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(50, 150, 250))
        painter.drawEllipse(4, 4, 24, 24)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "MPS")
        painter.end()
        return pixmap

    def load_task_data(self):
        """加载现有任务数据"""
        if self.task_data:
            self.name_edit.setText(self.task_data.get('name', ''))
            self.enabled_check.setChecked(self.task_data.get('enabled', True))
            self.ps_edit.setPlainText(self.task_data.get('ps_command', ''))
            self.timestamp_check.setChecked(self.task_data.get('time_stamp', True))

    def insert_example(self):
        """插入示例命令"""
        example = """while ($true) {
    Write-Output "当前时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Output "计算机名: $env:COMPUTERNAME"
    Write-Output "用户名: $env:USERNAME"
    Write-Output "---"
    Start-Sleep -Seconds 10
}"""
        self.ps_edit.setPlainText(example)

    def save_task(self):
        """保存任务"""
        name = self.name_edit.text().strip()
        ps_command = self.ps_edit.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "错误", "请输入任务名称")
            return

        if not ps_command:
            QMessageBox.warning(self, "错误", "请输入 PowerShell 命令")
            return

        self.task_data = {
            'name': name,
            'enabled': self.enabled_check.isChecked(),
            'ps_command': ps_command,
            'time_stamp': self.timestamp_check.isChecked()
        }

        self.accept()

    def get_task_data(self):
        """获取任务数据"""
        return self.task_data
