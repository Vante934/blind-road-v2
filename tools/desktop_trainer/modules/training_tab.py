# ============================================================
# training_tab.py - 模型训练 Tab
# ============================================================
import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QGroupBox, QFileDialog, QMessageBox, QCheckBox, QSpinBox,
    QTextEdit, QProgressBar, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont

from config import (
    MODELS, MODELS_DIR, RESULTS_DIR, TRAIN_DEFAULTS,
    BTN_PRIMARY, BTN_SUCCESS, BTN_DANGER, BTN_SECONDARY
)


class TrainingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings('BlindRoadV2', 'DesktopTrainer')
        self.data_yaml = None
        self.workers = []
        self.pending_models = []
        self.completed_results = {}

        self._init_ui()
        self._try_restore_dataset()

    def _init_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        root.addWidget(self._build_left_panel(), 0)
        root.addWidget(self._build_right_panel(), 1)

    def _build_left_panel(self):
        w = QWidget()
        w.setFixedWidth(400)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('QScrollArea { border: none; }')
        scroll.setFixedWidth(320)

        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(10)

        g_data = QGroupBox('数据集')
        d_lay = QVBoxLayout(g_data)
        self.btn_choose_yaml = QPushButton('选择 dataset.yaml')
        self.btn_choose_yaml.setStyleSheet(BTN_PRIMARY)
        self.btn_choose_yaml.clicked.connect(self._choose_yaml)
        d_lay.addWidget(self.btn_choose_yaml)

        self.lbl_yaml = QLabel('未选择数据集')
        self.lbl_yaml.setWordWrap(True)
        self.lbl_yaml.setStyleSheet('color: #888; font-size: 16px;')
        d_lay.addWidget(self.lbl_yaml)
        lay.addWidget(g_data)

        g_models = QGroupBox('训练模型 (可多选)')
        m_lay = QVBoxLayout(g_models)
        m_lay.setSpacing(6)
        self.model_checks = []
        for m in MODELS:
            row = QHBoxLayout()
            cb = QCheckBox(m['name'])
            cb.setStyleSheet('QCheckBox { font-size: 17px; font-weight: 600; }')
            row.addWidget(cb)
            desc = QLabel(m['desc'])
            desc.setStyleSheet('color: #888; font-size: 11px;')
            row.addWidget(desc, 1)
            m_lay.addLayout(row)
            self.model_checks.append((cb, m))
        self.model_checks[0][0].setChecked(True)
        lay.addWidget(g_models)

        g_cfg = QGroupBox('训练参数')
        c_lay = QVBoxLayout(g_cfg)
        c_lay.setSpacing(8)

        c_lay.addWidget(self._row_spin('Epochs 训练轮数',
            'spin_epochs', TRAIN_DEFAULTS['epochs'], 1, 500))
        c_lay.addWidget(self._row_spin('Batch 批次大小',
            'spin_batch', TRAIN_DEFAULTS['batch'], 1, 128))
        c_lay.addWidget(self._row_spin('Imgsz 图像尺寸',
            'spin_imgsz', TRAIN_DEFAULTS['imgsz'], 320, 1280))

        lay.addWidget(g_cfg)

        g_op = QGroupBox('操作')
        op_lay = QVBoxLayout(g_op)
        self.btn_start = QPushButton('开始训练')
        self.btn_start.setStyleSheet(BTN_SUCCESS)
        self.btn_start.clicked.connect(self._start_training)
        op_lay.addWidget(self.btn_start)

        self.btn_stop = QPushButton('停止训练')
        self.btn_stop.setStyleSheet(BTN_DANGER)
        self.btn_stop.clicked.connect(self._stop_training)
        self.btn_stop.setEnabled(False)
        op_lay.addWidget(self.btn_stop)
        lay.addWidget(g_op)

        lay.addStretch()
        scroll.setWidget(inner)

        outer = QWidget()
        outer.setFixedWidth(320)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.addWidget(scroll)
        return outer

    def _row_spin(self, label, attr, default, mn, mx):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setStyleSheet('font-size: 16px;')
        lay.addWidget(lbl, 1)
        sp = QSpinBox()
        sp.setRange(mn, mx)
        sp.setValue(default)
        sp.setFixedWidth(90)
        setattr(self, attr, sp)
        lay.addWidget(sp)
        return w

    def _build_right_panel(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        g_prog = QGroupBox('训练进度')
        p_lay = QVBoxLayout(g_prog)

        self.lbl_current = QLabel('等待开始...')
        self.lbl_current.setStyleSheet('font-size: 17px; font-weight: 600; color: #333;')
        p_lay.addWidget(self.lbl_current)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat('%v / %m epochs')
        p_lay.addWidget(self.progress_bar)

        self.lbl_overall = QLabel('总进度: 0 / 0 模型')
        self.lbl_overall.setStyleSheet('color: #666; font-size: 16px;')
        p_lay.addWidget(self.lbl_overall)
        lay.addWidget(g_prog)

        g_log = QGroupBox('训练日志')
        l_lay = QVBoxLayout(g_log)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setStyleSheet(
            'QTextEdit { font-family: Consolas, "Microsoft YaHei"; font-size: 16px; '
            'background: #1e1e2e; color: #d4d4d4; border-radius: 6px; padding: 8px; }'
        )
        l_lay.addWidget(self.log_edit)
        lay.addWidget(g_log, 1)

        g_result = QGroupBox('训练结果')
        r_lay = QVBoxLayout(g_result)
        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setMaximumHeight(140)
        self.result_edit.setStyleSheet(
            'QTextEdit { font-family: Consolas; font-size: 16px; '
            'background: #FAFCFF; border: 1px solid #D0E8F8; border-radius: 6px; padding: 8px; }'
        )
        self.result_edit.setPlainText('尚无训练结果')
        r_lay.addWidget(self.result_edit)
        lay.addWidget(g_result)

        return w

    def _try_restore_dataset(self):
        last = self.settings.value('last_data_yaml', '')
        if last and os.path.isfile(last):
            self.data_yaml = last
            self.lbl_yaml.setText(self._short_path(last))

    def _choose_yaml(self):
        last_dir = os.path.dirname(self.settings.value('last_data_yaml', str(Path.home())))
        f, _ = QFileDialog.getOpenFileName(
            self, '选择 dataset.yaml', last_dir, 'YAML 文件 (*.yaml *.yml);;所有文件 (*)'
        )
        if not f:
            return
        self.data_yaml = f
        self.settings.setValue('last_data_yaml', f)
        self.lbl_yaml.setText(self._short_path(f))
        self._log(f'已选择数据集: {f}')

    def _short_path(self, p):
        return p if len(p) < 40 else '...' + p[-37:]

    def _start_training(self):
        if not self.data_yaml:
            QMessageBox.warning(self, '提示', '请先选择 dataset.yaml')
            return

        selected = [m for cb, m in self.model_checks if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, '提示', '请至少选择一个模型')
            return

        epochs = self.spin_epochs.value()
        batch  = self.spin_batch.value()
        imgsz  = self.spin_imgsz.value()

        n_models = len(selected)
        est_min = n_models * epochs * 0.5
        r = QMessageBox.question(
            self, '确认',
            f'将训练 {n_models} 个模型，共 {epochs} epochs\n'
            f'预估耗时: 约 {est_min:.0f} 分钟\n\n是否开始?'
        )
        if r != QMessageBox.Yes:
            return

        self.pending_models = list(selected)
        self.completed_results = {}
        self.result_edit.setPlainText('训练中...')
        self.log_edit.clear()
        self._log(f'队列: {len(self.pending_models)} 个模型待训练')
        self._update_overall()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self._train_next()

    def _train_next(self):
        if not self.pending_models:
            self._on_all_done()
            return

        model_info = self.pending_models.pop(0)
        model_file = self._resolve_model_file(model_info['file'])
        model_name = model_info['name']

        self.lbl_current.setText(f'正在训练: {model_name}')
        self.progress_bar.setMaximum(self.spin_epochs.value())
        self.progress_bar.setValue(0)
        self._log(f'\n===== 开始训练 {model_name} =====')

        from modules.shared.training_worker import TrainingWorker
        w = TrainingWorker(
            model_file=model_file,
            data_yaml=self.data_yaml,
            epochs=self.spin_epochs.value(),
            batch=self.spin_batch.value(),
            imgsz=self.spin_imgsz.value(),
            project_dir=str(RESULTS_DIR),
            model_name=model_name,
        )
        w.log_signal.connect(self._log)
        w.progress_signal.connect(self._on_progress)
        w.finished_signal.connect(self._on_model_finished)
        w.error_signal.connect(self._on_model_error)
        self.workers.append(w)
        w.start()

    def _resolve_model_file(self, filename):
        local = MODELS_DIR / filename
        if local.exists():
            return str(local)
        return filename

    def _stop_training(self):
        for w in self.workers:
            if w.isRunning():
                w.stop()
        self.pending_models = []
        self._log('\n[用户中止] 正在停止训练...')
        self.btn_stop.setEnabled(False)

    def _on_progress(self, cur, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(cur)

    def _on_model_finished(self, name, metrics):
        self.completed_results[name] = metrics
        self._log(f'===== {name} 训练完成 =====\n')
        self._update_result_summary()
        self._update_overall()
        self._train_next()

    def _on_model_error(self, name, err):
        self._log(f'[错误] {name}: {err}')
        self.completed_results[name] = {'error': err}
        self._update_overall()
        self._train_next()

    def _on_all_done(self):
        self.lbl_current.setText('所有训练已完成')
        self._log('\n>>> 全部训练完成 <<<')
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._update_result_summary()
        QMessageBox.information(
            self, '完成',
            f'共完成 {len(self.completed_results)} 个模型\n\n'
            f'结果已保存至 results/ 目录\n可在"模型评估"Tab查看'
        )

    def _update_overall(self):
        done = len(self.completed_results)
        total = done + len(self.pending_models)
        for w in self.workers:
            if w.isRunning():
                total += 1
                break
        self.lbl_overall.setText(f'总进度: {done} / {total} 模型')

    def _update_result_summary(self):
        if not self.completed_results:
            return
        lines = ['模型          mAP50    mAP50-95  Precision  Recall']
        lines.append('-' * 55)
        for name, m in self.completed_results.items():
            if 'error' in m:
                lines.append(f'{name:12s}  [训练失败]')
            else:
                lines.append(
                    f"{name:12s}  {m.get('mAP50',0):.4f}   "
                    f"{m.get('mAP50-95',0):.4f}    "
                    f"{m.get('precision',0):.4f}     "
                    f"{m.get('recall',0):.4f}"
                )
        self.result_edit.setPlainText('\n'.join(lines))

    def _log(self, msg):
        self.log_edit.append(msg)
        sb = self.log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())
