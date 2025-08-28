import os
import sys
import winreg
from PySide6.QtWidgets import (QSystemTrayIcon, QMenu, QApplication,
                               QWidget, QMessageBox)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt

from config import load_config, save_config
from multi_process_manager import MultiProcessManager
from log_dialog import LogDialog
from utils import get_app_dir
from task_manager_dialog import TaskManagerDialog
from task_edit_dialog import TaskEditDialog


__version__ = "1.0.0"


class MultiSystemTrayApp(QSystemTrayIcon):
    def __init__(self):
        super().__init__()

        # 初始化变量
        self.log_files = {}
        self.task_log_dialogs = {}
        self.manager_dialog = None

        # 加载配置
        self.tasks = load_config()

        # 设置托盘图标
        self.setIcon(QIcon(self.create_icon()))
        self.setToolTip("多任务 PowerShell 监控器")

        # 创建多任务进程管理器
        self.process_manager = MultiProcessManager()
        self.process_manager.update_signal.connect(self.update_log)
        self.process_manager.status_changed.connect(self.on_task_status_changed)

        # 初始化所有任务
        self.initialize_tasks()

        # 创建菜单
        self.create_menu()

        # 显示托盘图标
        self.show()

        # 启动启用的任务
        self.start_enabled_tasks()

        self.showMessage("多任务 PowerShell 监控器",
                         f"程序a，共加载 {len(self.tasks)} 个任务",
                         QSystemTrayIcon.Information, 2000)

        if hasattr(self.manager_dialog, 'tasks_updated'):
            self.manager_dialog.tasks_updated.connect(self.on_tasks_updated)

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

    def initialize_tasks(self):
        """初始化所有任务"""
        for task_id, task_config in self.tasks.items():
            log_file = os.path.join(get_app_dir(), f"task_{task_id}.log")
            self.log_files[task_id] = log_file
            self.process_manager.add_task(task_id, task_config, log_file)

    def create_menu(self):
        """创建系统托盘菜单"""
        self.menu = QMenu()

        # 任务管理菜单项
        self.manage_tasks_action = QAction("任务管理", self)
        self.manage_tasks_action.triggered.connect(self.show_task_manager)

        # 全局操作菜单项
        self.start_all_action = QAction("启动所有任务", self)
        self.stop_all_action = QAction("停止所有任务", self)
        self.reload_config_action = QAction("重新加载配置", self)

        # 系统设置菜单项
        self.autostart_action = QAction("开机自启动", self, checkable=True)
        self.autostart_action.setChecked(self.is_autostart_enabled())

        # 退出菜单项
        self.about_action = QAction("关于", self)
        self.exit_action = QAction("退出", self)

        # 连接信号
        self.start_all_action.triggered.connect(self.start_all_tasks)
        self.stop_all_action.triggered.connect(self.stop_all_tasks)
        self.reload_config_action.triggered.connect(self.reload_config)
        self.autostart_action.triggered.connect(self.toggle_autostart)
        self.exit_action.triggered.connect(self.exit_app)
        self.about_action.triggered.connect(self.about)
        self.activated.connect(self.on_tray_activated)

        # 构建菜单结构
        self.menu.addAction(self.manage_tasks_action)
        self.menu.addSeparator()

        # 添加任务子菜单
        self.task_menu = self.menu.addMenu("任务列表")
        self.update_task_menu()

        self.menu.addSeparator()
        self.menu.addAction(self.start_all_action)
        self.menu.addAction(self.stop_all_action)
        self.menu.addAction(self.reload_config_action)
        self.menu.addSeparator()
        self.menu.addAction(self.autostart_action)
        self.menu.addSeparator()
        self.menu.addAction(self.about_action)
        self.menu.addAction(self.exit_action)

        self.setContextMenu(self.menu)

    def update_task_menu(self):
        """更新任务子菜单"""
        self.task_menu.clear()

        for task_id, task_config in self.tasks.items():
            task_name = task_config.get('name', f'任务 {task_id}')
            task_action = QAction(task_name, self)
            task_action.setCheckable(True)
            task_action.setChecked(self.process_manager.get_task_status(task_id))

            # 为每个任务创建上下文菜单
            task_menu = QMenu(task_name)

            # 添加任务操作
            start_stop_action = QAction("启动/停止", self)
            view_log_action = QAction("查看日志", self)
            configure_action = QAction("配置", self)

            # 连接信号
            start_stop_action.triggered.connect(
                lambda checked, tid=task_id: self.toggle_task(tid))
            view_log_action.triggered.connect(
                lambda checked, tid=task_id: self.show_task_log(tid))
            configure_action.triggered.connect(
                lambda checked, tid=task_id: self.configure_task(tid))

            task_menu.addAction(start_stop_action)
            task_menu.addAction(view_log_action)
            task_menu.addAction(configure_action)

            task_action.setMenu(task_menu)
            self.task_menu.addAction(task_action)

    def toggle_task(self, task_id):
        """切换任务状态"""
        if self.process_manager.get_task_status(task_id):
            self.process_manager.stop_task(task_id)
        else:
            self.process_manager.start_task(task_id)

    def show_task_log(self, task_id):
        """显示任务日志"""
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

    def configure_task(self, task_id):
        """配置任务"""
        self.parent_widget = QWidget()
        self.parent_widget.hide()
        dialog = TaskEditDialog(self.tasks[task_id])
        if dialog.exec():
            new_data = dialog.get_task_data()
            self.tasks[task_id] = new_data
            self.save_config_and_update()

    def save_config_and_update(self):
        """保存配置并更新界面"""
        if save_config(self.tasks):
            self.update_task_list()
            self.tasks_updated.emit()  # 发出更新信号
            QMessageBox.information(None, "成功", "配置已保存")
        else:
            QMessageBox.warning(None, "错误", "保存配置失败")

    def show_task_manager(self):
        """显示任务管理器对话框"""
        # 每次重新创建对话框以确保显示最新数据
        self.manager_dialog = TaskManagerDialog(self.tasks, self.process_manager, self.log_files)

        # 连接任务更新信号
        self.manager_dialog.tasks_updated.connect(self.on_tasks_updated)

        self.manager_dialog.show()
        self.manager_dialog.raise_()
        self.manager_dialog.activateWindow()

    def start_enabled_tasks(self):
        """启动所有启用的任务"""
        for task_id, task_config in self.tasks.items():
            if task_config.get('enabled', False):
                self.process_manager.start_task(task_id)

    def start_all_tasks(self):
        """启动所有任务"""
        for task_id in self.tasks.keys():
            self.process_manager.start_task(task_id)

    def stop_all_tasks(self):
        """停止所有任务"""
        self.process_manager.stop_all_tasks()

    def reload_config(self):
        """重新加载配置"""
        new_tasks = load_config()
        self.tasks = new_tasks

        # 停止所有当前任务
        self.process_manager.stop_all_tasks()

        # 重新初始化任务
        self.initialize_tasks()

        # 更新菜单
        self.update_task_menu()

        # 启动启用的任务
        self.start_enabled_tasks()

        self.showMessage("配置已重新加载",
                         f"已加载 {len(self.tasks)} 个任务",
                         QSystemTrayIcon.Information, 3000)

    def update_log(self, task_id, text):
        """更新日志"""
        # 如果对应任务的日志对话框正在显示，则更新它
        if task_id in self.task_log_dialogs and self.task_log_dialogs[task_id].isVisible():
            self.task_log_dialogs[task_id].append_text(text)

    def on_task_status_changed(self, task_id, is_running):
        """任务状态变化处理"""
        # 更新菜单显示
        self.update_task_menu()

        # 显示状态通知
        task_name = self.tasks[task_id].get('name', f'任务 {task_id}')
        status = "启动" if is_running else "停止"
        self.showMessage(f"任务状态变化", f"{task_name} 已{status}",
                         QSystemTrayIcon.Information, 2000)

    def on_tasks_updated(self):
        """当任务更新时的处理"""
        # 重新加载配置
        self.reload_config()

        # 更新菜单
        self.update_task_menu()

        # 显示通知
        self.showMessage("任务已更新", "任务列表已刷新", QSystemTrayIcon.Information, 2000)

    # 以下方法保持与原来相同（is_autostart_enabled, toggle_autostart, exit_app）
    def is_autostart_enabled(self):
        """检查是否已设置开机自启动"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ
            )
            try:
                value, _ = winreg.QueryValueEx(key, "PowerShellMonitor")
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False

    def toggle_autostart(self, enabled):
        """切换开机自启动设置"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_WRITE
            )

            if enabled:
                exe_path = os.path.abspath(sys.argv[0])
                winreg.SetValueEx(key, "PowerShellMonitor", 0, winreg.REG_SZ, f'"{exe_path}"')
                self.showMessage("开机自启动", "已启用开机自启动", QSystemTrayIcon.Information, 2000)
            else:
                try:
                    winreg.DeleteValue(key, "PowerShellMonitor")
                except FileNotFoundError:
                    pass
                self.showMessage("开机自启动", "已禁用开机自启动", QSystemTrayIcon.Information, 2000)

            winreg.CloseKey(key)

        except Exception as e:
            self.showMessage("错误", f"设置开机自启动失败: {str(e)}", QSystemTrayIcon.Critical, 3000)
            self.autostart_action.setChecked(not enabled)

    def about(self):
        """关于此程序"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowIcon(QIcon(self.create_icon()))
        msg.setWindowTitle("PSMonitor - 关于")
        msg.setText(f"PSMonitor v{__version__}\n项目地址: https://github.com/CuberAHZ/PowerShellMonitor\n作者邮箱: my@cuberliu.xyz")
        msg.exec()

    def exit_app(self):
        """退出应用程序"""
        self.process_manager.stop_all_tasks()
        QApplication.quit()

    def on_tray_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_task_manager()
