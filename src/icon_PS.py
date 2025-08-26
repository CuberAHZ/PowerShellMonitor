from PySide6.QtGui import QPixmap, QPainter, QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication  # 添加这行导入
import sys  # 添加这行导入


def create_icon(size):
    """创建指定尺寸的图标"""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))  # 透明背景

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # 绘制圆形背景
    painter.setBrush(QColor(50, 150, 250))
    margin = size // 8  # 边距为尺寸的1/8
    painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)

    painter.setPen(QColor(255, 255, 255))
    font = painter.font()
    font.setPixelSize(size // 2)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "PS")

    painter.end()
    return pixmap


def create_and_save_icons():
    """创建并保存多种尺寸的图标"""
    sizes = [16, 24, 32, 48, 64, 128, 256]

    for size in sizes:
        pixmap = create_icon(size)
        filename = f"tray_icon_{size}x{size}.png"
        pixmap.save(filename, "PNG")
        print(f"图标已保存为 {filename}")


if __name__ == "__main__":
    # 创建 QApplication 实例
    app = QApplication(sys.argv)

    # 创建并保存图标
    create_and_save_icons()

    # 不需要进入事件循环，直接退出
    sys.exit(0)