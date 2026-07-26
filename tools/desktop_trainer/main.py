# ============================================================
# main.py — 程序入口
# 「视界」盲道智能导航系统 - 桌面训练工具
# ============================================================

# ⚠️ matplotlib 必须在任何 Qt import 之前设置后端，否则可能崩溃
import matplotlib
matplotlib.use('Agg')

import sys
import os
from pathlib import Path

# 确保可以 import 同级模块
sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

from config import STYLE_SHEET


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('视界 · 盲道智能导航 — 训练工具')
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        self._init_ui()

    def _init_ui(self):
        # 中央 Tab 控件
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setDocumentMode(True)
        self.setCentralWidget(self.tabs)

        # 延迟导入各 Tab（加快启动速度 + 隔离崩溃）
        self._load_tabs()

    def _load_tabs(self):
        """加载三个功能 Tab，任意一个失败都不影响其他 Tab"""
        tab_specs = [
            ('数据标注', 'modules.annotation_tab', 'AnnotationTab'),
            ('模型训练', 'modules.training_tab',   'TrainingTab'),
            ('模型评估', 'modules.testing_tab',    'TestingTab'),
        ]
        for title, module_path, class_name in tab_specs:
            try:
                import importlib
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                widget = cls()
            except Exception as e:
                widget = self._make_error_tab(title, str(e))
            self.tabs.addTab(widget, title)

    @staticmethod
    def _make_error_tab(title: str, error: str) -> QWidget:
        """Tab 加载失败时显示错误信息，而非整体崩溃"""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignCenter)
        icon = QLabel('加载失败')
        icon.setAlignment(Qt.AlignCenter)
        icon.setFont(QFont('', 36))
        msg = QLabel(f'{title} 加载失败\n\n{error}')
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet('color: #F5222D; font-size: 14px;')
        lay.addWidget(icon)
        lay.addWidget(msg)
        return w


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE_SHEET)

    # 全局字体
    font = QFont('Microsoft YaHei', 12)
    font.setHintingPreference(QFont.PreferNoHinting)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()