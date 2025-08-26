import os
import sys
import winreg
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction, QTextCursor
from PySide6.QtCore import Qt

from config import load_config
from process_manager import ProcessManager
from log_dialog import LogDialog
from utils import get_app_dir, is_process_running


class SystemTrayApp(QSystemTrayIcon):
    def __init__(self):
        super().__init__()

        # 初始化变量
        self.is_running = False
        self.log_file = os.path.join(get_app_dir(), "powershell_output.log")
        self.log_dialog = None

        # 加载配置
        self.ps_command, self.time_stamp = load_config()

        # 设置托盘图标
        self.setIcon(QIcon(self.create_icon()))
        self.setToolTip("PowerShell 监控器")

        # 创建进程管理器
        self.process_manager = ProcessManager(self.ps_command, self.time_stamp, self.log_file)
        self.process_manager.update_signal.connect(self.update_log)

        # 创建菜单
        self.menu = QMenu()

        # 添加菜单项
        self.status_action = QAction("查看状态", self)
        self.toggle_action = QAction("停止", self)
        self.autostart_action = QAction("开机自启动", self, checkable=True)
        self.reload_config_action = QAction("重新加载配置", self)
        self.exit_action = QAction("退出", self)

        # 检查当前自启动状态
        self.autostart_action.setChecked(self.is_autostart_enabled())

        self.menu.addAction(self.status_action)
        self.menu.addAction(self.toggle_action)
        self.menu.addSeparator()
        self.menu.addAction(self.autostart_action)
        self.menu.addAction(self.reload_config_action)
        self.menu.addSeparator()
        self.menu.addAction(self.exit_action)

        self.setContextMenu(self.menu)

        # 连接信号
        self.status_action.triggered.connect(self.show_status)
        self.toggle_action.triggered.connect(self.toggle_process)
        self.autostart_action.triggered.connect(self.toggle_autostart)
        self.reload_config_action.triggered.connect(self.reload_config)
        self.exit_action.triggered.connect(self.exit_app)
        self.activated.connect(self.on_tray_activated)

        # 启动 PowerShell 进程
        self.start_process()

        # 显示托盘图标
        self.show()

        # 显示启动消息
        self.showMessage("PowerShell 监控器", "程序已启动并在后台运行", QSystemTrayIcon.Information, 2000)

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
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "PS")
        painter.end()
        return pixmap

    def reload_config(self):
        """重新加载配置文件"""
        self.ps_command, self.time_stamp = load_config()
        self.process_manager.ps_command = self.ps_command
        self.process_manager.time_stamp = self.time_stamp

        self.showMessage("配置已重新加载", f"PS_COMMAND: {self.ps_command}\nTIME: {self.time_stamp}",
                         QSystemTrayIcon.Information, 3000)

        # 如果进程正在运行，重启进程以应用新配置
        if self.is_running:
            self.stop_process()
            self.start_process()

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
                # 获取当前可执行文件的路径
                exe_path = os.path.abspath(sys.argv[0])
                # 添加到注册表
                winreg.SetValueEx(key, "PowerShellMonitor", 0, winreg.REG_SZ, f'"{exe_path}"')
                self.showMessage("开机自启动", "已启用开机自启动", QSystemTrayIcon.Information, 2000)
            else:
                # 从注册表删除
                try:
                    winreg.DeleteValue(key, "PowerShellMonitor")
                except FileNotFoundError:
                    pass  # 如果值不存在，忽略错误
                self.showMessage("开机自启动", "已禁用开机自启动", QSystemTrayIcon.Information, 2000)

            winreg.CloseKey(key)

        except Exception as e:
            self.showMessage("错误", f"设置开机自启动失败: {str(e)}", QSystemTrayIcon.Critical, 3000)
            # 恢复复选框状态
            self.autostart_action.setChecked(not enabled)

    def start_process(self):
        """启动进程"""
        if self.process_manager.start():
            self.is_running = True
            self.toggle_action.setText("停止")

    def stop_process(self):
        """停止进程"""
        self.process_manager.stop()
        self.is_running = False
        self.toggle_action.setText("运行")

    def toggle_process(self):
        """切换进程状态（运行/停止）"""
        if self.is_running:
            self.stop_process()
            self.showMessage("PowerShell 监控器", "进程已停止", QSystemTrayIcon.Information, 2000)
        else:
            self.start_process()
            self.showMessage("PowerShell 监控器", "进程已启动", QSystemTrayIcon.Information, 2000)

    def update_log(self, text):
        """更新日志"""
        self.process_manager.write_log(text)

        # 如果日志对话框正在显示，则更新它
        if self.log_dialog and self.log_dialog.isVisible():
            self.log_dialog.append_text(text)

    def show_status(self):
        """显示状态对话框"""
        if self.log_dialog is None or not self.log_dialog.isVisible():
            self.log_dialog = LogDialog()

            # 读取日志文件内容并显示
            try:
                if os.path.exists(self.log_file):
                    with open(self.log_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.log_dialog.text_edit.setPlainText(content)
                    # 移动光标到末尾
                    cursor = self.log_dialog.text_edit.textCursor()
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    self.log_dialog.text_edit.setTextCursor(cursor)
            except Exception as e:
                self.log_dialog.text_edit.setPlainText(f"读取日志文件时出错: {str(e)}")

        self.log_dialog.show()
        self.log_dialog.raise_()
        self.log_dialog.activateWindow()

    def exit_app(self):
        """退出应用程序"""
        if self.is_running:
            self.stop_process()
        QApplication.quit()

    def on_tray_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_status()
