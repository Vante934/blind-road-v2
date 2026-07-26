# ============================================================
# config.py — 全局配置
# 「视界」盲道智能导航系统 - 桌面训练工具
# ============================================================
import os
from pathlib import Path

# ---------- 路径 ----------
ROOT_DIR    = Path(__file__).parent                          # desktop_trainer/
MODELS_DIR  = ROOT_DIR / 'models'
RESULTS_DIR = ROOT_DIR / 'results'
DATASETS_DIR= ROOT_DIR / 'datasets'
DEMO_DIR    = DATASETS_DIR / 'demo'

# 确保目录存在
for _d in [MODELS_DIR, RESULTS_DIR, DATASETS_DIR, DEMO_DIR / 'images', DEMO_DIR / 'labels']:
    _d.mkdir(parents=True, exist_ok=True)

# ---------- 类别 ----------
CATEGORIES = [
    {'id': 0, 'name': '盲道',   'en': 'blind_path',      'color': '#4A9BF5'},
    {'id': 1, 'name': '障碍物', 'en': 'obstacle',         'color': '#F5222D'},
    {'id': 2, 'name': '行人',   'en': 'person',           'color': '#52C41A'},
    {'id': 3, 'name': '车辆',   'en': 'vehicle',          'color': '#FAAD14'},
    {'id': 4, 'name': '坑洼',   'en': 'pothole',          'color': '#722ED1'},
    {'id': 5, 'name': '台阶',   'en': 'step',             'color': '#13C2C2'},
]
CAT_NAMES_EN = [c['en'] for c in CATEGORIES]
CAT_NAMES_ZH = [c['name'] for c in CATEGORIES]

# ---------- 支持的模型 ----------
MODELS = [
    {'name': 'YOLOv8n', 'file': 'yolov8n.pt', 'desc': '最快，适合实时检测'},
    {'name': 'YOLOv8s', 'file': 'yolov8s.pt', 'desc': '速度与精度平衡'},
    {'name': 'YOLO11n', 'file': 'yolo11n.pt', 'desc': '新架构，轻量高效'},
    {'name': 'YOLO11s', 'file': 'yolo11s.pt', 'desc': '新架构，精度更高'},
]

# ---------- 训练默认参数 ----------
TRAIN_DEFAULTS = {
    'epochs': 50,
    'batch':  16,
    'imgsz':  640,
    'workers': 4,
    'patience': 20,
}

# ---------- 全局样式表 ----------
STYLE_SHEET = """
QMainWindow, QDialog {
    background-color: #EBF4FB;
}
QWidget {
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 18px;
}
QTabWidget::pane {
    border: 1px solid #D0E8F8;
    background: white;
    border-radius: 0 8px 8px 8px;
}
QTabBar::tab {
    padding: 16px 40px;
    font-size: 20px;
    font-weight: 500;
    background: #F0F6FC;
    color: #5A7A90;
    border: 1px solid #D0E8F8;
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background: #4A9BF5;
    color: white;
    border-color: #4A9BF5;
}
QTabBar::tab:hover:!selected {
    background: #DCF0FF;
    color: #4A9BF5;
}
QPushButton {
    padding: 14px 28px;
    font-size: 17px;
    border-radius: 8px;
    border: none;
    font-weight: 500;
}
QPushButton:disabled {
    background: #C0C0C0 !important;
    color: #888 !important;
}
QGroupBox {
    font-weight: bold;
    font-size: 17px;
    border: 1.5px solid #D0E8F8;
    border-radius: 8px;
    margin-top: 20px;
    padding-top: 24px;
    background: white;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 10px;
    color: #4A9BF5;
}
QLabel { font-size: 17px; color: #333; }
QLineEdit, QComboBox, QSpinBox {
    padding: 10px 14px;
    font-size: 17px;
    border: 1.5px solid #D0E8F8;
    border-radius: 6px;
    background: white;
    min-height: 24px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #4A9BF5;
}
QTextEdit {
    border: 1.5px solid #D0E8F8;
    border-radius: 6px;
    font-size: 15px;
    background: #FAFCFF;
}
QProgressBar {
    border: 1px solid #D0E8F8;
    border-radius: 6px;
    text-align: center;
    font-size: 16px;
    background: #F0F6FC;
    height: 28px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4A9BF5, stop:1 #74B9FF);
    border-radius: 5px;
}
QCheckBox {
    font-size: 17px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
}
QTableWidget {
    font-size: 16px;
}
QHeaderView::section {
    font-size: 17px;
    padding: 10px;
    font-weight: 600;
}
QScrollBar:vertical {
    width: 12px;
    background: #F0F6FC;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #B0D4EF;
    border-radius: 6px;
    min-height: 40px;
}
"""

# ---------- 按钮颜色辅助 ----------
def btn_style(color: str, text_color: str = 'white') -> str:
    """生成按钮样式字符串"""
    from PyQt5.QtGui import QColor
    c = QColor(color)
    hover = c.darker(115).name()
    return (f"QPushButton {{ background:{color}; color:{text_color}; }}"
            f"QPushButton:hover {{ background:{hover}; }}")

BTN_PRIMARY  = btn_style('#4A9BF5')
BTN_SUCCESS  = btn_style('#52C41A')
BTN_WARNING  = btn_style('#FAAD14')
BTN_DANGER   = btn_style('#F5222D')
BTN_SECONDARY= btn_style('#8C8C8C')