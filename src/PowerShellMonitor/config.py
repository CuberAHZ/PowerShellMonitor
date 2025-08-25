import os
import sys
import configparser


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

DEFAULT_TIME = False

# 获取程序所在目录
if getattr(sys, 'frozen', False):
    # 如果是打包后的可执行文件
    APP_DIR = os.path.dirname(sys.executable)
else:
    # 如果是脚本运行
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置文件路径
CONFIG_FILE = os.path.join(APP_DIR, "config.ini")


def load_config():
    """加载配置文件"""
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
        return DEFAULT_PS_COMMAND, DEFAULT_TIME

    # 读取配置文件
    try:
        config.read(CONFIG_FILE, encoding='utf-8')
        ps_command = config.get('DEFAULT', 'PS_COMMAND', fallback=DEFAULT_PS_COMMAND)
        time_stamp = config.getboolean('DEFAULT', 'TIME', fallback=DEFAULT_TIME)
        print(f"已加载配置: PS_COMMAND={ps_command}, TIME={time_stamp}")
        return ps_command, time_stamp
    except Exception as e:
        print(f"读取配置文件时出错: {e}, 使用默认配置")
        return DEFAULT_PS_COMMAND, DEFAULT_TIME
