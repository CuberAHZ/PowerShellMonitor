import subprocess
import threading
from datetime import datetime
from PySide6.QtCore import QObject, Signal


class ProcessManager(QObject):
    """进程管理器"""

    update_signal = Signal(str)

    def __init__(self, ps_command, time_stamp, log_file):
        super().__init__()
        self.ps_command = ps_command
        self.time_stamp = time_stamp
        self.log_file = log_file
        self.process = None
        self.is_running = False
        self.output_thread = None

    def start(self):
        """启动 PowerShell 子进程"""
        try:
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
                    ["powershell", "-Command", self.ps_command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=False,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

            self.is_running = True

            # 启动线程来读取输出
            self.output_thread = threading.Thread(target=self._read_output)
            self.output_thread.daemon = True
            self.output_thread.start()
            return True

        except Exception as e:
            self.update_signal.emit(f"启动进程失败: {str(e)}")
            return False

    def _read_output(self):
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
                self.update_signal.emit(decoded_line)

            except Exception as e:
                error_msg = f"读取输出时出错: {str(e)}"
                self.update_signal.emit(error_msg)
                break

    def stop(self):
        """停止进程"""
        if self.process:
            try:
                # 在 Windows 上使用 taskkill 终止进程树
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                               capture_output=True)
            except Exception as e:
                self.update_signal.emit(f"终止进程时出错: {e}")

            self.process = None

        self.is_running = False

    def write_log(self, text):
        """写入日志文件"""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                if self.time_stamp:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {text}")
                else:
                    f.write(text)
        except Exception as e:
            self.update_signal.emit(f"写入日志文件时出错: {e}")
            