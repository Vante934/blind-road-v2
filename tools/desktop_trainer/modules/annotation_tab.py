# ============================================================
# annotation_tab.py - 数据标注 Tab
# ============================================================
import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QGroupBox, QFileDialog, QMessageBox,
    QFrame
)
from PyQt5.QtCore import Qt, QSettings

from config import (
    CATEGORIES, BTN_PRIMARY, BTN_SUCCESS,
    BTN_WARNING, BTN_DANGER, BTN_SECONDARY
)
from modules.shared.canvas_widget import AnnotationCanvas


class AnnotationTab(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings('BlindRoadV2', 'DesktopTrainer')
        self.image_dir = None
        self.label_dir = None
        self.image_files = []
        self.current_idx = -1

        self._init_ui()
        self.setAcceptDrops(True)
        self._try_restore_last_dir()

    def _init_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        root.addWidget(self._build_left_panel(), 0)
        root.addWidget(self._build_center_panel(), 1)
        root.addWidget(self._build_right_panel(), 0)

    def _build_left_panel(self):
        w = QWidget()
        w.setFixedWidth(240)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        g_folder = QGroupBox('图片来源')
        g_lay = QVBoxLayout(g_folder)
        g_lay.setSpacing(6)

        self.btn_open = QPushButton('选择文件夹')
        self.btn_open.setStyleSheet(BTN_PRIMARY)
        self.btn_open.clicked.connect(self._select_folder)
        g_lay.addWidget(self.btn_open)

        self.btn_open_files = QPushButton('选择多张图片')
        self.btn_open_files.setStyleSheet(BTN_PRIMARY)
        self.btn_open_files.clicked.connect(self._select_files)
        g_lay.addWidget(self.btn_open_files)

        tip = QLabel('也可以直接拖拽图片\n或文件夹到窗口')
        tip.setStyleSheet('color: #4A9BF5; font-size: 11px; padding: 4px; '
                          'background: #EBF4FB; border-radius: 4px;')
        tip.setAlignment(Qt.AlignCenter)
        g_lay.addWidget(tip)

        self.lbl_folder = QLabel('未选择')
        self.lbl_folder.setWordWrap(True)
        self.lbl_folder.setStyleSheet('color: #888; font-size: 11px;')
        g_lay.addWidget(self.lbl_folder)
        lay.addWidget(g_folder)

        g_cat = QGroupBox('标注类别')
        c_lay = QVBoxLayout(g_cat)
        c_lay.setSpacing(4)
        self.cat_buttons = []
        for cat in CATEGORIES:
            btn = QPushButton(f"  {cat['name']}")
            btn.setCheckable(True)
            btn.setStyleSheet(self._cat_btn_style(cat['color'], False))
            btn.clicked.connect(lambda checked, cid=cat['id']: self._select_category(cid))
            c_lay.addWidget(btn)
            self.cat_buttons.append(btn)
        self.cat_buttons[0].setChecked(True)
        self.cat_buttons[0].setStyleSheet(self._cat_btn_style(CATEGORIES[0]['color'], True))
        lay.addWidget(g_cat)

        g_op = QGroupBox('操作')
        op_lay = QVBoxLayout(g_op)
        op_lay.setSpacing(4)
        self.btn_undo = QPushButton('撤销 (Z)')
        self.btn_undo.setStyleSheet(BTN_WARNING)
        self.btn_undo.clicked.connect(self._undo)
        op_lay.addWidget(self.btn_undo)

        self.btn_clear = QPushButton('清空标注')
        self.btn_clear.setStyleSheet(BTN_DANGER)
        self.btn_clear.clicked.connect(self._clear)
        op_lay.addWidget(self.btn_clear)

        self.btn_save = QPushButton('保存 (S)')
        self.btn_save.setStyleSheet(BTN_SUCCESS)
        self.btn_save.clicked.connect(self._save_current)
        op_lay.addWidget(self.btn_save)
        lay.addWidget(g_op)

        lay.addStretch()
        return w

    def _build_center_panel(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        top = QFrame()
        top.setStyleSheet('background: white; border: 1px solid #D0E8F8; border-radius: 6px;')
        top.setFixedHeight(72)
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(16, 10, 16, 10)
        top_lay.setSpacing(8)

        self.btn_prev = QPushButton('上一张')
        self.btn_prev.setStyleSheet(BTN_SECONDARY)
        self.btn_prev.setFixedWidth(140)
        self.btn_prev.clicked.connect(lambda: self._navigate(-1))
        top_lay.addWidget(self.btn_prev)

        self.lbl_img_info = QLabel('未加载图片')
        self.lbl_img_info.setAlignment(Qt.AlignCenter)
        self.lbl_img_info.setStyleSheet('font-weight: 600; color: #333; font-size: 18px;')
        top_lay.addWidget(self.lbl_img_info, 1)

        self.btn_next = QPushButton('下一张')
        self.btn_next.setStyleSheet(BTN_SECONDARY)
        self.btn_next.setFixedWidth(140)
        self.btn_next.clicked.connect(lambda: self._navigate(1))
        top_lay.addWidget(self.btn_next)

        lay.addWidget(top)

        self.canvas = AnnotationCanvas()
        self.canvas.annotation_added.connect(self._on_annotations_changed)
        lay.addWidget(self.canvas, 1)

        return w

    def _build_right_panel(self):
        w = QWidget()
        w.setFixedWidth(240)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        g_list = QGroupBox('图片列表')
        l_lay = QVBoxLayout(g_list)
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._on_list_click)
        self.list_widget.setStyleSheet(
            'QListWidget { border: 1px solid #D0E8F8; border-radius: 6px; background: white; font-size: 16px; }'
            'QListWidget::item { padding: 5px 6px; }'
            'QListWidget::item:selected { background: #DCF0FF; color: #4A9BF5; }'
        )
        l_lay.addWidget(self.list_widget)
        lay.addWidget(g_list, 1)

        g_stat = QGroupBox('统计')
        s_lay = QVBoxLayout(g_stat)
        self.lbl_ann_count = QLabel('当前: 0 个标注')
        self.lbl_ann_count.setStyleSheet('font-size: 16px;')
        self.lbl_labeled_count = QLabel('已标注: 0 / 0')
        self.lbl_labeled_count.setStyleSheet('font-size: 16px;')
        s_lay.addWidget(self.lbl_ann_count)
        s_lay.addWidget(self.lbl_labeled_count)
        lay.addWidget(g_stat)

        g_kbd = QGroupBox('快捷键')
        k_lay = QVBoxLayout(g_kbd)
        tip = QLabel('Z    撤销\nS    保存\n<-  上一张\n->  下一张\n1-6  选类别')
        tip.setStyleSheet('color: #666; font-size: 16px;')
        k_lay.addWidget(tip)
        lay.addWidget(g_kbd)

        return w

    def _cat_btn_style(self, color, active):
        if active:
            return (f'QPushButton {{ background: {color}; color: white; '
                    f'border-radius: 5px; padding: 7px; text-align: left; '
                    f'font-weight: 600; font-size: 17px; }}')
        return (f'QPushButton {{ background: #F0F6FC; color: {color}; '
                f'border: 1.5px solid {color}; border-radius: 5px; '
                f'padding: 7px; text-align: left; font-size: 17px; }}'
                f'QPushButton:hover {{ background: #DCF0FF; }}')

    def _try_restore_last_dir(self):
        last = self.settings.value('last_image_dir', '')
        if last and os.path.isdir(last):
            self._load_folder(last)

    def _select_folder(self):
        last = self.settings.value('last_image_dir', str(Path.home()))
        d = QFileDialog.getExistingDirectory(self, '选择图片文件夹', last)
        if d:
            self._load_folder(d)

    def _load_folder(self, folder: str):
        self.image_dir = folder
        self.label_dir = os.path.join(os.path.dirname(folder), 'labels')
        os.makedirs(self.label_dir, exist_ok=True)

        from PyQt5.QtGui import QImageReader
        supported = {bytes(x).decode().lower() for x in QImageReader.supportedImageFormats()}
        supported |= {'jpg', 'jpeg', 'png', 'bmp', 'webp', 'gif', 'tif', 'tiff'}

        try:
            all_files = os.listdir(folder)
        except Exception as e:
            QMessageBox.warning(self, '错误', f'无法读取文件夹:\n{e}')
            return

        self.image_files = sorted([
            f for f in all_files
            if os.path.isfile(os.path.join(folder, f))
            and Path(f).suffix.lower().lstrip('.') in supported
        ])

        print(f'[标注] 扫描到 {len(self.image_files)} 张图片，路径: {folder}')

        self.settings.setValue('last_image_dir', folder)
        display = folder if len(folder) < 30 else '...' + folder[-27:]
        self.lbl_folder.setText(display)
        self._refresh_list()

        if self.image_files:
            self._goto(0)
        else:
            QMessageBox.information(self, '提示',
                f'该文件夹内没有可识别的图片\n\n支持的格式: {", ".join(sorted(supported))}')

    def _refresh_list(self):
        self.list_widget.clear()
        labeled = 0
        for name in self.image_files:
            item = QListWidgetItem(name)
            if self._has_label(name):
                item.setForeground(Qt.darkGreen)
                labeled += 1
            self.list_widget.addItem(item)
        self.lbl_labeled_count.setText(f'已标注: {labeled} / {len(self.image_files)}')

    def _has_label(self, img_name: str) -> bool:
        if not self.label_dir:
            return False
        p = os.path.join(self.label_dir, Path(img_name).stem + '.txt')
        return os.path.exists(p) and os.path.getsize(p) > 0

    def _goto(self, idx: int):
        if not self.image_files:
            return
        idx = max(0, min(idx, len(self.image_files) - 1))
        self.current_idx = idx
        name = self.image_files[idx]
        path = os.path.join(self.image_dir, name)

        if not self.canvas.load_image(path):
            QMessageBox.warning(self, '错误', f'无法加载图片: {name}')
            return

        anns = self._load_label(name)
        self.canvas.set_annotations(anns)

        self.lbl_img_info.setText(f'{name}   ({idx + 1} / {len(self.image_files)})')
        self.list_widget.setCurrentRow(idx)
        self._update_stats()

    def _navigate(self, delta: int):
        self._goto(self.current_idx + delta)

    def _on_list_click(self, item):
        idx = self.list_widget.row(item)
        self._goto(idx)

    def _select_category(self, cat_id: int):
        for i, btn in enumerate(self.cat_buttons):
            btn.setChecked(i == cat_id)
            btn.setStyleSheet(self._cat_btn_style(CATEGORIES[i]['color'], i == cat_id))
        self.canvas.set_category(cat_id)

    def _undo(self):
        self.canvas.undo_last()

    def _clear(self):
        if not self.canvas.get_annotations():
            return
        r = QMessageBox.question(self, '确认', '清空当前图片的所有标注?')
        if r == QMessageBox.Yes:
            self.canvas.clear_all()

    def _save_current(self):
        if self.current_idx < 0:
            return
        name = self.image_files[self.current_idx]
        anns = self.canvas.get_annotations()
        self._write_label(name, anns)
        self._refresh_list()
        self.list_widget.setCurrentRow(self.current_idx)
        QMessageBox.information(self, '已保存', f'{name} 保存了 {len(anns)} 个标注')

    def _load_label(self, img_name: str):
        if not self.label_dir:
            return []
        p = os.path.join(self.label_dir, Path(img_name).stem + '.txt')
        if not os.path.exists(p):
            return []
        anns = []
        try:
            with open(p, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) != 5:
                        continue
                    anns.append({
                        'cat': int(parts[0]),
                        'cx':  float(parts[1]),
                        'cy':  float(parts[2]),
                        'w':   float(parts[3]),
                        'h':   float(parts[4]),
                    })
        except Exception as e:
            print(f'读取标注失败: {e}')
        return anns

    def _write_label(self, img_name: str, anns):
        p = os.path.join(self.label_dir, Path(img_name).stem + '.txt')
        with open(p, 'w', encoding='utf-8') as f:
            for a in anns:
                f.write(f"{a['cat']} {a['cx']:.6f} {a['cy']:.6f} {a['w']:.6f} {a['h']:.6f}\n")

    def _on_annotations_changed(self):
        self._update_stats()

    def _on_annotation_selected(self, idx: int):
        pass

    def _update_stats(self):
        n = len(self.canvas.get_annotations())
        self.lbl_ann_count.setText(f'当前: {n} 个标注')

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Z:
            self._undo()
        elif key == Qt.Key_S:
            self._save_current()
        elif key == Qt.Key_Left:
            self._navigate(-1)
        elif key == Qt.Key_Right:
            self._navigate(1)
        elif Qt.Key_1 <= key <= Qt.Key_6:
            self._select_category(key - Qt.Key_1)
        else:
            super().keyPressEvent(event)

    def _select_files(self):
        """选择多张图片文件"""
        last = self.settings.value('last_image_dir', str(Path.home()))
        files, _ = QFileDialog.getOpenFileNames(
            self, '选择图片文件', last,
            '图片文件 (*.jpg *.jpeg *.png *.bmp *.webp *.gif *.tif *.tiff);;所有文件 (*)'
        )
        if not files:
            return
        folder = os.path.dirname(files[0])
        self._load_folder(folder)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if os.path.isdir(path):
            self._load_folder(path)
        elif os.path.isfile(path):
            folder = os.path.dirname(path)
            self._load_folder(folder)
            fname = os.path.basename(path)
            if fname in self.image_files:
                self._goto(self.image_files.index(fname))
