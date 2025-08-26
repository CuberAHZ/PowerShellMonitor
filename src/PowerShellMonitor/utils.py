import os
import sys
import atexit
import ctypes
from pathlib import Path


def get_app_dir():
    """获取应用程序目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


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
                    from PySide6.QtWidgets import QMessageBox
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
