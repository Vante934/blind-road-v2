# ============================================================
# canvas_widget.py — 可标注画布控件
# ============================================================
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QPixmap, QFont, QBrush


class AnnotationCanvas(QWidget):
    """支持画框标注的画布控件"""

    annotation_added = pyqtSignal()
    annotation_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        self.setMouseTracking(True)
        self.setStyleSheet('background: #1a1a2e; border-radius: 6px;')

        self.pixmap = None
        self.img_w = 0
        self.img_h = 0

        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.annotations = []
        self.selected_idx = -1

        self.current_cat = 0
        self.cat_names = ['盲道', '障碍物', '行人', '车辆', '坑洼', '台阶']
        self.cat_colors = ['#4A9BF5', '#F5222D', '#52C41A', '#FAAD14', '#722ED1', '#13C2C2']

        self.drawing = False
        self.start_pt = None
        self.current_rect = None

    def load_image(self, path: str) -> bool:
        pix = QPixmap(path)
        if pix.isNull():
            return False
        self.pixmap = pix
        self.img_w = pix.width()
        self.img_h = pix.height()
        self.annotations = []
        self.selected_idx = -1
        self._fit_view()
        self.update()
        return True

    def set_annotations(self, anns):
        self.annotations = list(anns)
        self.selected_idx = -1
        self.update()

    def get_annotations(self):
        return list(self.annotations)

    def set_category(self, cat_id: int):
        self.current_cat = cat_id

    def undo_last(self):
        if self.annotations:
            self.annotations.pop()
            self.selected_idx = -1
            self.update()
            self.annotation_added.emit()

    def clear_all(self):
        self.annotations = []
        self.selected_idx = -1
        self.update()
        self.annotation_added.emit()

    def delete_selected(self):
        if 0 <= self.selected_idx < len(self.annotations):
            self.annotations.pop(self.selected_idx)
            self.selected_idx = -1
            self.update()
            self.annotation_added.emit()

    def _fit_view(self):
        if not self.pixmap:
            return
        cw, ch = self.width(), self.height()
        s = min(cw / self.img_w, ch / self.img_h) * 0.95
        self.scale = s
        self.offset_x = (cw - self.img_w * s) / 2
        self.offset_y = (ch - self.img_h * s) / 2

    def resizeEvent(self, event):
        self._fit_view()
        super().resizeEvent(event)

    def _widget_to_img(self, x, y):
        ix = (x - self.offset_x) / self.scale
        iy = (y - self.offset_y) / self.scale
        return ix, iy

    def _img_to_widget(self, ix, iy):
        return ix * self.scale + self.offset_x, iy * self.scale + self.offset_y

    def mousePressEvent(self, event):
        if not self.pixmap or event.button() != Qt.LeftButton:
            return

        ix, iy = self._widget_to_img(event.x(), event.y())
        hit = -1
        for i in range(len(self.annotations) - 1, -1, -1):
            a = self.annotations[i]
            x1 = (a['cx'] - a['w'] / 2) * self.img_w
            y1 = (a['cy'] - a['h'] / 2) * self.img_h
            x2 = (a['cx'] + a['w'] / 2) * self.img_w
            y2 = (a['cy'] + a['h'] / 2) * self.img_h
            if x1 <= ix <= x2 and y1 <= iy <= y2:
                hit = i
                break

        if hit >= 0:
            self.selected_idx = hit
            self.annotation_selected.emit(hit)
            self.update()
        else:
            self.selected_idx = -1
            self.drawing = True
            self.start_pt = QPoint(event.x(), event.y())
            self.current_rect = None
            self.update()

    def mouseMoveEvent(self, event):
        if not self.drawing:
            return
        self.current_rect = QRect(self.start_pt, QPoint(event.x(), event.y())).normalized()
        self.update()

    def mouseReleaseEvent(self, event):
        if not self.drawing or event.button() != Qt.LeftButton:
            return
        self.drawing = False
        if not self.current_rect or self.current_rect.width() < 5 or self.current_rect.height() < 5:
            self.current_rect = None
            self.update()
            return

        x1, y1 = self._widget_to_img(self.current_rect.left(), self.current_rect.top())
        x2, y2 = self._widget_to_img(self.current_rect.right(), self.current_rect.bottom())
        x1 = max(0, min(self.img_w, x1))
        y1 = max(0, min(self.img_h, y1))
        x2 = max(0, min(self.img_w, x2))
        y2 = max(0, min(self.img_h, y2))

        if (x2 - x1) < 3 or (y2 - y1) < 3:
            self.current_rect = None
            self.update()
            return

        self.annotations.append({
            'cat': self.current_cat,
            'cx': (x1 + x2) / 2 / self.img_w,
            'cy': (y1 + y2) / 2 / self.img_h,
            'w':  (x2 - x1) / self.img_w,
            'h':  (y2 - y1) / self.img_h,
        })
        self.current_rect = None
        self.update()
        self.annotation_added.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#1a1a2e'))

        if not self.pixmap:
            painter.setPen(QColor('#888'))
            painter.setFont(QFont('Microsoft YaHei', 20))
            painter.drawText(self.rect(), Qt.AlignCenter,
                '请先选择图片文件夹\n\n拖拽画框即可标注')
            return

        target = QRect(
            int(self.offset_x), int(self.offset_y),
            int(self.img_w * self.scale), int(self.img_h * self.scale)
        )
        painter.drawPixmap(target, self.pixmap)

        for i, a in enumerate(self.annotations):
            color = QColor(self.cat_colors[a['cat']])
            x1, y1 = self._img_to_widget((a['cx'] - a['w'] / 2) * self.img_w,
                                          (a['cy'] - a['h'] / 2) * self.img_h)
            w = a['w'] * self.img_w * self.scale
            h = a['h'] * self.img_h * self.scale

            fill = QColor(color)
            fill.setAlpha(40)
            painter.fillRect(int(x1), int(y1), int(w), int(h), fill)

            pen = QPen(color, 3 if i == self.selected_idx else 2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(int(x1), int(y1), int(w), int(h))

            label = self.cat_names[a['cat']]
            painter.setFont(QFont('Microsoft YaHei', 10, QFont.Bold))
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(label) + 12
            th = fm.height() + 4
            painter.fillRect(int(x1), int(y1) - th, tw, th, color)
            painter.setPen(QColor('white'))
            painter.drawText(int(x1) + 6, int(y1) - 5, label)

        if self.current_rect:
            color = QColor(self.cat_colors[self.current_cat])
            pen = QPen(color, 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.current_rect)
