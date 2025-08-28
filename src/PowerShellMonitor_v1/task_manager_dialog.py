import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                               QPushButton, QLabel, QListWidgetItem, QCheckBox,
                               QWidget, QMessageBox)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon
import uuid

from task_edit_dialog import TaskEditDialog
from config import save_config
from log_dialog import LogDialog


class TaskManagerDialog(QDialog):
    """任务管理器"""

    tasks_updated = Signal()  # 任务更新信号

    def __init__(self, tasks, process_manager, log_files, parent=None):
        # 正确的父类初始化方式
        super().__init__(parent)
        self.tasks = tasks
        self.process_manager = process_manager

        self.setWindowTitle("PSMonitor - 任务管理器")
        self.setGeometry(100, 100, 700, 500)

        self.task_log_dialogs = {}
        self.log_files = log_files

        self.init_ui()
        self.update_task_list()

    def init_ui(self):
        layout = QVBoxLayout()

        self.setWindowIcon(QIcon(self.create_icon()))

        # 任务列表
        self.task_list = QListWidget()
        self.task_list.itemDoubleClicked.connect(self.edit_selected_task)
        layout.addWidget(QLabel("任务列表:"))
        layout.addWidget(self.task_list)

        # 按钮区域
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("启动")
        self.stop_btn = QPushButton("停止")
        self.edit_btn = QPushButton("编辑")
        self.add_btn = QPushButton("添加")
        self.delete_btn = QPushButton("删除")
        self.log_btn = QPushButton("查看日志")
        self.close_btn = QPushButton("关闭")


        self.start_btn.clicked.connect(self.start_selected_task)
        self.stop_btn.clicked.connect(self.stop_selected_task)
        self.edit_btn.clicked.connect(self.edit_selected_task)
        self.add_btn.clicked.connect(self.add_new_task)
        self.delete_btn.clicked.connect(self.delete_selected_task)
        self.log_btn.clicked.connect(self.show_log_task)
        self.close_btn.clicked.connect(self.accept)

        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.log_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)

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

    def update_task_list(self):
        """更新任务列表显示"""
        self.task_list.clear()

        for task_id, task_config in self.tasks.items():
            item = QListWidgetItem()
            widget = TaskListItemWidget(task_id, task_config,
                                        self.process_manager.get_task_status(task_id))
            item.setSizeHint(widget.sizeHint())

            self.task_list.addItem(item)
            self.task_list.setItemWidget(item, widget)

    def get_selected_task_id(self):
        """获取选中的任务ID"""
        current_item = self.task_list.currentItem()
        if current_item:
            widget = self.task_list.itemWidget(current_item)
            return widget.task_id
        return None

    def start_selected_task(self):
        """启动选中的任务"""
        task_id = self.get_selected_task_id()
        if task_id:
            self.process_manager.start_task(task_id)
            self.update_task_list()

    def stop_selected_task(self):
        """停止选中的任务"""
        task_id = self.get_selected_task_id()
        if task_id:
            self.process_manager.stop_task(task_id)
            self.update_task_list()

    def edit_selected_task(self):
        """编辑选中的任务"""
        task_id = self.get_selected_task_id()
        if task_id:
            dialog = TaskEditDialog(self.tasks[task_id], self)
            if dialog.exec():
                new_data = dialog.get_task_data()
                self.tasks[task_id] = new_data
                self.save_config_and_update()

    def add_new_task(self):
        """添加新任务"""
        dialog = TaskEditDialog(None, self)
        if dialog.exec():
            new_data = dialog.get_task_data()
            # 生成唯一的任务ID
            new_task_id = f"task_{uuid.uuid4().hex[:8]}"
            self.tasks[new_task_id] = new_data

            # 添加到进程管理器
            log_file = f"task_{new_task_id}.log"
            self.process_manager.add_task(new_task_id, new_data, log_file)

            # 如果任务启用，自动启动
            if new_data.get('enabled', False):
                self.process_manager.start_task(new_task_id)

            self.save_config_and_update()

    def delete_selected_task(self):
        """删除选中的任务"""
        task_id = self.get_selected_task_id()
        if task_id:
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除任务 '{self.tasks[task_id].get('name', '未知任务')}' 吗？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 停止任务
                self.process_manager.stop_task(task_id)
                # 从任务列表中移除
                del self.tasks[task_id]
                self.save_config_and_update()

    def show_log_task(self):
        """显示任务日志"""
        task_id = self.get_selected_task_id()
        log_file = self.log_files[task_id]

        if task_id not in self.task_log_dialogs:
            self.task_log_dialogs[task_id] = LogDialog(log_file)
            self.task_log_dialogs[task_id].setWindowTitle(
                f"PSMonitor - 任务日志 - {self.tasks[task_id].get('name', f'任务 {task_id}')}")

        # 读取并显示日志内容
        try:
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    content = f.read()
                self.task_log_dialogs[task_id].text_edit.setPlainText(content)
        except Exception as e:
            self.task_log_dialogs[task_id].text_edit.setPlainText(
                f"读取日志文件时出错: {str(e)}")

        self.task_log_dialogs[task_id].show()
        self.task_log_dialogs[task_id].raise_()
        self.task_log_dialogs[task_id].activateWindow()

    def save_config_and_update(self):
        """保存配置并更新界面"""
        if save_config(self.tasks):
            self.update_task_list()
            self.tasks_updated.emit()  # 发出更新信号
            QMessageBox.information(self, "成功", "配置已保存")
        else:
            QMessageBox.warning(self, "错误", "保存配置失败")


class TaskListItemWidget(QWidget):
    def __init__(self, task_id, task_config, is_running, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.task_config = task_config

        layout = QHBoxLayout()

        # 状态指示图标
        status_icon = QLabel("●")
        status_icon.setStyleSheet(f"color: {'green' if is_running else 'red'}; font-weight: bold;")
        layout.addWidget(status_icon)

        # 任务名称
        self.name_label = QLabel(task_config.get('name', f'任务 {task_id}'))
        layout.addWidget(self.name_label)

        # 状态文本
        status_text = "运行中" if is_running else "已停止"
        self.status_label = QLabel(status_text)
        layout.addWidget(self.status_label)

        # 启用复选框
        self.enabled_check = QCheckBox("启用")
        self.enabled_check.setChecked(task_config.get('enabled', False))
        self.enabled_check.setEnabled(False)  # 在列表中不可编辑
        layout.addWidget(self.enabled_check)

        layout.addStretch()
        self.setLayout(layout)
