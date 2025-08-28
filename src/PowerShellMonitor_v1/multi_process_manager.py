import subprocess
import threading
from datetime import datetime
from PySide6.QtCore import QObject, Signal


class MultiProcessManager(QObject):
    """多任务进程管理器"""

    update_signal = Signal(str, str)  # (task_id, message)
    status_changed = Signal(str, bool)  # (task_id, is_running)

    def __init__(self):
        super().__init__()
        self.tasks = {}  # 存储所有任务信息
        self.processes = {}  # 存储进程对象
        self.output_threads = {}  # 存储输出线程

    def add_task(self, task_id, task_config, log_file):
        """添加任务"""
        self.tasks[task_id] = {
            'config': task_config,
            'log_file': log_file,
            'is_running': False
        }

    def start_task(self, task_id):
        """启动指定任务"""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        ps_command = task['config']['ps_command']
        time_stamp = task['config']['time_stamp']
        log_file = task['log_file']

        try:
            # 检查是否是 PowerShell 命令还是可执行文件
            if ps_command.lower().endswith('.exe'):
                command_parts = ps_command.split()
                executable = command_parts[0]
                args = command_parts[1:] if len(command_parts) > 1 else []

                process = subprocess.Popen(
                    [executable] + args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=False,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                process = subprocess.Popen(
                    ["powershell", "-Command", ps_command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=False,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

            self.processes[task_id] = process
            task['is_running'] = True
            self.status_changed.emit(task_id, True)

            # 启动线程来读取输出
            output_thread = threading.Thread(
                target=self._read_output,
                args=(task_id, process, log_file, time_stamp)
            )
            output_thread.daemon = True
            output_thread.start()
            self.output_threads[task_id] = output_thread

            return True

        except Exception as e:
            error_msg = f"启动任务 {task_id} 失败: {str(e)}"
            self.update_signal.emit(task_id, error_msg)
            return False

    def _read_output(self, task_id, process, log_file, time_stamp):
        """读取进程输出"""
        while process and process.stdout:
            try:
                raw_line = process.stdout.readline()
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

                if decoded_line is None:
                    decoded_line = raw_line.decode('utf-8', errors='replace')

                # 写入日志文件
                self._write_log(log_file, decoded_line, time_stamp)

                # 发送更新信号
                self.update_signal.emit(task_id, decoded_line)

            except Exception as e:
                error_msg = f"读取任务 {task_id} 输出时出错: {str(e)}"
                self.update_signal.emit(task_id, error_msg)
                break

    def _write_log(self, log_file, text, time_stamp):
        """写入日志文件"""
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                if time_stamp:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {text}")
                else:
                    f.write(text)
        except Exception as e:
            self.update_signal.emit("system", f"写入日志文件时出错: {e}")

    def stop_task(self, task_id):
        """停止指定任务"""
        if task_id in self.processes:
            try:
                process = self.processes[task_id]
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                               capture_output=True)
            except Exception as e:
                self.update_signal.emit(task_id, f"终止进程时出错: {e}")

            del self.processes[task_id]

        if task_id in self.tasks:
            self.tasks[task_id]['is_running'] = False
            self.status_changed.emit(task_id, False)

    def stop_all_tasks(self):
        """停止所有任务"""
        for task_id in list(self.processes.keys()):
            self.stop_task(task_id)

    def get_task_status(self, task_id):
        """获取任务状态"""
        return self.tasks.get(task_id, {}).get('is_running', False)

    def remove_task(self, task_id):
        """移除任务"""
        if task_id in self.processes:
            self.stop_task(task_id)
        if task_id in self.tasks:
            del self.tasks[task_id]
