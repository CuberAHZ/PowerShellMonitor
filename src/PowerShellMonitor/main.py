import sys
from PySide6.QtWidgets import QApplication
from system_tray import SystemTrayApp
from utils import check_single_instance


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
