import sys
import os
import subprocess
import threading
import winreg
import configparser
import atexit
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu,
                               QMessageBox, QTextEdit, QDialog, QVBoxLayout,
                               QHBoxLayout, QPushButton)
from PySide6.QtGui import QIcon, QAction, QFont, QTextCursor
from PySide6.QtCore import Qt, QObject, Signal


# 默认配置值
DEFAULT_PS_COMMAND = """
while ($true) {
    Write-Output "当前时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Output "进程ID: $PID"
    Write-Output "运行状态: 正常"
    Write-Output "---"
    Start-Sleep -Seconds 5
}
"""

# 获取程序所在目录
if getattr(sys, 'frozen', False):
    # 如果是打包后的可执行文件
    APP_DIR = os.path.dirname(sys.executable)
else:
    # 如果是脚本运行
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置文件路径
CONFIG_FILE = os.path.join(APP_DIR, "config.ini")
LOG_FILE = os.path.join(APP_DIR, "powershell_output.log")

DEFAULT_TIME = False

# 初始化配置变量
PS_COMMAND = DEFAULT_PS_COMMAND
TIME = DEFAULT_TIME


def check_single_instance(app_name="PowerShellTrayManager"):
    """使用文件锁检查是否已有实例在运行"""
    # 创建锁文件路径
    lock_file = Path(os.environ.get('TEMP', '')) / f"{app_name}.lock"

    try:
        # 检查锁文件是否存在
        if lock_file.exists():
            # 读取锁文件中的进程ID
            try:
                with open(lock_file, 'r') as f:
                    pid = int(f.read().strip())

                # 检查该进程是否仍在运行
                if is_process_running(pid):
                    QMessageBox.warning(
                        None,
                        "程序已运行",
                        "PowerShell Tray Manager 已经在运行中，请检查系统托盘。"
                    )
                    return False
            except:
                # 如果读取失败，可能是陈旧的锁文件
                pass

        # 创建锁文件并写入当前进程ID
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))

        # 注册退出时清理锁文件的函数
        atexit.register(cleanup_lock_file, lock_file)

        return True
    except Exception as e:
        print(f"检查单实例时出错: {e}")
        return True


def is_process_running(pid):
    """检查指定PID的进程是否在运行"""
    try:
        # 在Windows上，我们可以尝试向进程发送信号0（不实际发送信号，只检查权限）
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_INFORMATION
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    except:
        return False


def cleanup_lock_file(lock_file):
    """清理锁文件"""
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
    except:
        pass


def load_config():
    """加载配置文件"""
    global PS_COMMAND, TIME

    config = configparser.ConfigParser()

    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(CONFIG_FILE):
        config['DEFAULT'] = {
            'PS_COMMAND': DEFAULT_PS_COMMAND,
            'TIME': str(DEFAULT_TIME)
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        print(f"创建默认配置文件: {CONFIG_FILE}")
        return

    # 读取配置文件
    try:
        config.read(CONFIG_FILE, encoding='utf-8')
        PS_COMMAND = config.get('DEFAULT', 'PS_COMMAND', fallback=DEFAULT_PS_COMMAND)
        TIME = config.getboolean('DEFAULT', 'TIME', fallback=DEFAULT_TIME)
        print(f"已加载配置: PS_COMMAND={PS_COMMAND}, TIME={TIME}")
    except Exception as e:
        print(f"读取配置文件时出错: {e}, 使用默认配置")
        PS_COMMAND = DEFAULT_PS_COMMAND
        TIME = DEFAULT_TIME


# 加载配置
load_config()


# 自定义信号类，用于线程间通信
class Communicate(QObject):
    update_signal = Signal(str)


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


class SystemTrayApp(QSystemTrayIcon):
    def __init__(self):
        super().__init__()

        # 初始化变量
        self.is_running = False
        self.process = None
        self.log_file = LOG_FILE
        self.comm = Communicate()
        self.log_dialog = None

        # 加载配置
        self.ps_command = PS_COMMAND
        self.time_stamp = TIME

        # 设置托盘图标
        self.setIcon(QIcon(self.create_icon()))
        self.setToolTip("PowerShell 监控器")

        # 创建菜单
        self.menu = QMenu()

        # 添加菜单项
        self.status_action = QAction("查看状态", self)
        self.toggle_action = QAction("停止", self)  # 初始状态为运行中
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
        self.comm.update_signal.connect(self.update_log)
        self.activated.connect(self.on_tray_activated)

        # 启动 PowerShell 进程
        self.start_process()

        # 显示托盘图标
        self.show()

        # 显示启动消息
        self.showMessage("PowerShell 监控器", "程序已启动并在后台运行", QSystemTrayIcon.Information, 2000)

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

    def reload_config(self):
        """重新加载配置文件"""
        global PS_COMMAND, TIME
        load_config()
        self.ps_command = PS_COMMAND
        self.time_stamp = TIME
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
        """启动 PowerShell 子进程"""
        try:
            # 使用配置中的命令
            if self.ps_command:
                ps_command = self.ps_command
            else:
                ps_command = """
                while ($true) {
                    Write-Output "当前时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
                    Write-Output "进程ID: $PID"
                    Write-Output "运行状态: 正常"
                    Write-Output "---"
                    Start-Sleep -Seconds 5
                }
                """

            # 启动进程
            # 检查是否是 PowerShell 命令还是可执行文件
            if self.ps_command.lower().endswith('.exe'):
                # 如果是可执行文件，直接运行
                command_parts = self.ps_command.split()
                executable = command_parts[0]
                args = command_parts[1:] if len(command_parts) > 1 else []

                self.process = subprocess.Popen(
                    [executable] + args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=False,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                # 如果是 PowerShell 命令，使用 PowerShell 执行
                self.process = subprocess.Popen(
                    ["powershell", "-Command", ps_command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=False,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

            self.is_running = True
            self.toggle_action.setText("停止")

            # 启动线程来读取输出
            self.output_thread = threading.Thread(target=self.read_output)
            self.output_thread.daemon = True
            self.output_thread.start()

        except Exception as e:
            self.showMessage("错误", f"启动进程失败: {str(e)}", QSystemTrayIcon.Critical, 3000)

    def read_output(self):
        """读取进程输出并发送到主线程"""
        while self.process and self.process.stdout:
            try:
                # 读取二进制数据
                raw_line = self.process.stdout.readline()
                if not raw_line:
                    break

                # 尝试多种编码方式解码
                decoded_line = None
                encodings = ['utf-8', 'gbk', 'latin-1', 'cp1252']

                for encoding in encodings:
                    try:
                        decoded_line = raw_line.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue

                # 如果所有编码都失败，使用替代字符
                if decoded_line is None:
                    decoded_line = raw_line.decode('utf-8', errors='replace')

                # 发送到主线程更新日志
                self.comm.update_signal.emit(decoded_line)

            except Exception as e:
                error_msg = f"读取输出时出错: {str(e)}"
                self.comm.update_signal.emit(error_msg)
                break

    def update_log(self, text):
        """更新日志文件并显示在对话框中"""
        # 写入日志文件
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                if self.time_stamp:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {text}")
                else:
                    f.write(text)
        except Exception as e:
            print(f"写入日志文件时出错: {e}")

        # 如果日志对话框正在显示，则更新它
        if self.log_dialog and self.log_dialog.isVisible():
            self.log_dialog.append_text(text)

    def stop_process(self):
        """停止进程"""
        if self.process:
            # 终止进程及其子进程
            try:
                # 在 Windows 上使用 taskkill 终止进程树
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                               capture_output=True)
            except Exception as e:
                print(f"终止进程时出错: {e}")

            self.process = None

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

    def show_status(self):
        """显示状态对话框"""
        # 如果对话框不存在或已被关闭，创建新的对话框
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


def main():
    # 检查是否已有实例在运行
    if not check_single_instance():
        sys.exit(0)

    # 创建应用程序实例
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 创建系统托盘应用
    tray_app = SystemTrayApp()

    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
