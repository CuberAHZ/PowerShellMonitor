import os
import sys
import configparser
import json


# 默认配置值
TASK1_COMMAND = """
while ($true) {
    Write-Output "当前时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Output "进程ID: $PID"
    Write-Output "运行状态: 正常"
    Write-Output "---"
    Start-Sleep -Seconds 5
}
"""

TASK2_COMMAND = """
while ($true) {
    Write-Output "任务2运行中: $(Get-Date)"
    Start-Sleep -Seconds 5
}
"""

DEFAULT_TASKS = {
	"task1": {
	    "name": "示例任务 1",
	    "enabled": True,
	    "ps_command": TASK1_COMMAND,
	    "time_stamp": True
	},
    "task2": {
        "name": "示例任务 2",
        "ps_command": TASK2_COMMAND,
        "time_stamp": False,
        "enabled": False
    }
}

# 获取程序所在目录
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置文件路径
CONFIG_FILE = os.path.join(APP_DIR, "config.ini")


def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()

    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(CONFIG_FILE):
        config['DEFAULT'] = {
            'TASKS': json.dumps(DEFAULT_TASKS, ensure_ascii=False)
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        print(f"创建默认配置文件: {CONFIG_FILE}")
        return DEFAULT_TASKS

    # 读取配置文件
    try:
        config.read(CONFIG_FILE, encoding='utf-8')
        tasks_json = config.get('DEFAULT', 'TASKS', fallback=json.dumps(DEFAULT_TASKS))
        tasks = json.loads(tasks_json)
        print(f"已加载 {len(tasks)} 个任务配置")
        return tasks
    except Exception as e:
        print(f"读取配置文件时出错: {e}, 使用默认配置")
        return DEFAULT_TASKS


def save_config(tasks):
    """保存配置到文件"""
    try:
        config = configparser.ConfigParser()
        config['DEFAULT'] = {
            'TASKS': json.dumps(tasks, ensure_ascii=False, indent=2)
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        print(f"配置已保存: {len(tasks)} 个任务")
        return True
    except Exception as e:
        print(f"保存配置时出错: {e}")
        return False
