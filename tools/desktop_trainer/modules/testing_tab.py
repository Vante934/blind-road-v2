# ============================================================
# testing_tab.py - 模型评估 Tab
# ============================================================
import os
import csv
import yaml
import tempfile
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QGroupBox, QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QProgressBar, QFrame, QCheckBox, QScrollArea
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor, QFont

from config import (
    MODELS_DIR, RESULTS_DIR,
    BTN_PRIMARY, BTN_SUCCESS, BTN_DANGER, BTN_SECONDARY
)


class TestingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings('BlindRoadV2', 'DesktopTrainer')
        self.data_yaml = None
        self.model_specs = []       # [{'name', 'path', 'checked'}]
        self.results = []           # 评估结果
        self.worker = None

        self._init_ui()
        self._try_restore_dataset()
        self._scan_models()

    def _init_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        root.addWidget(self._build_left_panel(), 0)
        root.addWidget(self._build_right_panel(), 1)

    def _build_left_panel(self):
        outer = QWidget()
        outer.setFixedWidth(320)
        lay = QVBoxLayout(outer)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        # 数据集
        g_data = QGroupBox('验证数据集')
        d_lay = QVBoxLayout(g_data)
        self.btn_yaml = QPushButton('选择 dataset.yaml')
        self.btn_yaml.setStyleSheet(BTN_PRIMARY)
        self.btn_yaml.clicked.connect(self._choose_yaml)
        d_lay.addWidget(self.btn_yaml)

        self.lbl_yaml = QLabel('未选择数据集')
        self.lbl_yaml.setWordWrap(True)
        self.lbl_yaml.setStyleSheet('color: #888; font-size: 16px;')
        d_lay.addWidget(self.lbl_yaml)
        lay.addWidget(g_data)

        # 模型列表
        g_models = QGroupBox('可评估的模型')
        m_lay = QVBoxLayout(g_models)

        top_row = QHBoxLayout()
        self.btn_rescan = QPushButton('重新扫描')
        self.btn_rescan.setStyleSheet(BTN_SECONDARY)
        self.btn_rescan.clicked.connect(self._scan_models)
        top_row.addWidget(self.btn_rescan)

        self.btn_add = QPushButton('添加 .pt 文件')
        self.btn_add.setStyleSheet(BTN_SECONDARY)
        self.btn_add.clicked.connect(self._add_model)
        top_row.addWidget(self.btn_add)
        m_lay.addLayout(top_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('QScrollArea { border: 1px solid #D0E8F8; border-radius: 6px; background: white; }')
        scroll.setMinimumHeight(200)

        self.model_list_widget = QWidget()
        self.model_list_layout = QVBoxLayout(self.model_list_widget)
        self.model_list_layout.setSpacing(4)
        self.model_list_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.model_list_widget)
        m_lay.addWidget(scroll, 1)

        lay.addWidget(g_models, 1)

        # 操作
        g_op = QGroupBox('操作')
        op_lay = QVBoxLayout(g_op)
        self.btn_start = QPushButton('开始评估')
        self.btn_start.setStyleSheet(BTN_SUCCESS)
        self.btn_start.clicked.connect(self._start_eval)
        op_lay.addWidget(self.btn_start)

        self.btn_stop = QPushButton('停止')
        self.btn_stop.setStyleSheet(BTN_DANGER)
        self.btn_stop.clicked.connect(self._stop_eval)
        self.btn_stop.setEnabled(False)
        op_lay.addWidget(self.btn_stop)

        self.btn_export = QPushButton('导出报告 CSV')
        self.btn_export.setStyleSheet(BTN_SECONDARY)
        self.btn_export.clicked.connect(self._export_csv)
        op_lay.addWidget(self.btn_export)

        lay.addWidget(g_op)
        return outer

    def _build_right_panel(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # 进度
        prog_row = QHBoxLayout()
        self.lbl_progress = QLabel('等待评估...')
        self.lbl_progress.setStyleSheet('font-weight: 600;')
        prog_row.addWidget(self.lbl_progress)
        prog_row.addStretch()
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(300)
        prog_row.addWidget(self.progress_bar)
        lay.addLayout(prog_row)

        # 对比表格
        g_table = QGroupBox('评估结果对比')
        t_lay = QVBoxLayout(g_table)
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ['模型', 'mAP50', 'mAP50-95', 'Precision', 'Recall', '大小(MB)', '速度(ms)']
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet(
            'QTableWidget { background: white; gridline-color: #E0E8F0; font-size: 16px; }'
            'QHeaderView::section { background: #4A9BF5; color: white; padding: 6px; border: none; font-weight: 600; }'
            'QTableWidget::item { padding: 6px; }'
            'QTableWidget::item:selected { background: #DCF0FF; color: #333; }'
        )
        t_lay.addWidget(self.table)
        lay.addWidget(g_table, 2)

        # 推荐 + 日志（并排）
        bottom = QHBoxLayout()

        g_reco = QGroupBox('推荐')
        rc_lay = QVBoxLayout(g_reco)
        self.reco_text = QTextEdit()
        self.reco_text.setReadOnly(True)
        self.reco_text.setStyleSheet(
            'QTextEdit { font-family: Consolas, "Microsoft YaHei"; font-size: 16px; '
            'background: #FAFCFF; border: 1px solid #D0E8F8; '
            'border-radius: 6px; padding: 8px; }'
        )
        self.reco_text.setPlainText('评估完成后将显示推荐结果')
        rc_lay.addWidget(self.reco_text)
        bottom.addWidget(g_reco, 1)

        g_log = QGroupBox('日志')
        l_lay = QVBoxLayout(g_log)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setStyleSheet(
            'QTextEdit { font-family: Consolas, "Microsoft YaHei"; font-size: 16px; '
            'background: #1e1e2e; color: #d4d4d4; '
            'border-radius: 6px; padding: 8px; }'
        )
        l_lay.addWidget(self.log_edit)
        bottom.addWidget(g_log, 1)

        lay.addLayout(bottom, 1)

        return w

    # ---------- 数据集 ----------
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

    def _normalize_yaml(self, yaml_path):
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
        except Exception as e:
            self._log(f'[警告] yaml 解析失败: {e}，使用原文件')
            return yaml_path

        if not isinstance(cfg, dict):
            return yaml_path

        yaml_dir = Path(yaml_path).parent.resolve()
        base = cfg.get('path', '')
        if base:
            b = Path(base)
            if not b.is_absolute():
                b = (yaml_dir / base).resolve()
        else:
            b = yaml_dir

        cfg['path'] = str(b).replace('\\', '/')

        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False, encoding='utf-8'
        )
        yaml.safe_dump(cfg, tmp, allow_unicode=True, sort_keys=False)
        tmp.close()
        self._log(f'[规范化] 使用临时 yaml: {tmp.name}')
        self._log(f'[规范化] path 已改写为: {cfg["path"]}')
        return tmp.name

    # ---------- 模型管理 ----------
    def _scan_models(self):
        specs = []
        seen_paths = set()

        def add_spec(name, path, source):
            key = os.path.abspath(path).lower()
            if key in seen_paths:
                return
            seen_paths.add(key)
            specs.append({'name': name, 'path': path, 'source': source})

        project_root = Path(__file__).parent.parent.parent
        outer_root   = project_root.parent

        scan_locations = [
            (MODELS_DIR,               '*.pt',                  'trainer/models'),
            (RESULTS_DIR,              '*/weights/best.pt',     'trainer/results'),
            (RESULTS_DIR,              '*/weights/last.pt',     'trainer/results'),
            (project_root / 'models',  '*.pt',                  'v2/models'),
            (outer_root / 'models',    '*.pt',                  '项目/models'),
            (outer_root / 'models',    '*/*.pt',                '项目/models'),
            (outer_root / 'models',    '*/weights/best.pt',     '项目/models'),
            (outer_root / 'results',   '*/weights/best.pt',     '项目/results'),
        ]

        for base_dir, pattern, source in scan_locations:
            if not base_dir.exists():
                continue
            try:
                for pt_file in base_dir.glob(pattern):
                    if not pt_file.is_file():
                        continue
                    if 'weights' in pt_file.parts:
                        parent = pt_file.parent.parent.name
                        name = f'{parent}_{pt_file.stem}'
                    elif pt_file.parent.name in ('models', 'results'):
                        name = pt_file.stem
                    else:
                        name = f'{pt_file.parent.name}_{pt_file.stem}'
                    add_spec(name, str(pt_file), source)
            except Exception as e:
                print(f'扫描 {base_dir} 失败: {e}')

        self.model_specs = specs
        self._refresh_model_list()
        self._log(f'扫描到 {len(specs)} 个模型')
        if specs:
            self._log('扫描位置:')
            for s in specs:
                self._log(f'  [{s["source"]}] {s["name"]}  -->  {s["path"]}')

    def _add_model(self):
        last_dir = str(MODELS_DIR) if MODELS_DIR.exists() else str(Path.home())
        files, _ = QFileDialog.getOpenFileNames(
            self, '选择 .pt 模型文件', last_dir, 'PyTorch 模型 (*.pt);;所有文件 (*)'
        )
        if not files:
            return
        for f in files:
            name = Path(f).stem
            if not any(s['path'] == f for s in self.model_specs):
                self.model_specs.append({
                    'name': name,
                    'path': f,
                    'checked': True,
                })
        self._refresh_model_list()
        self._log(f'添加了 {len(files)} 个模型')

    def _refresh_model_list(self):
        while self.model_list_layout.count() > 0:
            item = self.model_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for spec in self.model_specs:
            row = QWidget()
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(4, 4, 4, 4)
            cb = QCheckBox(spec['name'])
            cb.setChecked(spec.get('checked', True))
            cb.setStyleSheet('QCheckBox { font-size: 16px; }')
            cb.stateChanged.connect(lambda state, s=spec: self._on_model_check(s, state))
            row_lay.addWidget(cb)
            row_lay.addStretch()
            self.model_list_layout.addWidget(row)

    def _on_model_check(self, spec, state):
        spec['checked'] = state == Qt.Checked

    # ---------- 评估 ----------
    def _start_eval(self):
        if not self.data_yaml:
            QMessageBox.warning(self, '提示', '请先选择 dataset.yaml')
            return

        selected = [s for s in self.model_specs if s.get('checked', True)]
        if not selected:
            QMessageBox.warning(self, '提示', '请至少选择一个模型')
            return

        self.table.setRowCount(0)
        self.reco_text.setPlainText('评估中...')
        self.log_edit.clear()
        self.results = []
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_export.setEnabled(False)

        self._log(f'开始评估 {len(selected)} 个模型')
        self.progress_bar.setMaximum(len(selected))
        self.progress_bar.setValue(0)

        normalized_yaml = self._normalize_yaml(self.data_yaml)

        from modules.shared.eval_worker import EvalWorker
        self.worker = EvalWorker(selected, normalized_yaml)
        self.worker.log_signal.connect(self._log)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.one_done_signal.connect(self._on_one_done)
        self.worker.all_done_signal.connect(self._on_all_done)
        self.worker.error_signal.connect(self._on_error)
        self.worker.start()

    def _stop_eval(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self._log('正在停止评估...')
        self.btn_stop.setEnabled(False)

    def _on_progress(self, cur, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(cur)
        self.lbl_progress.setText(f'评估中: {cur} / {total}')

    def _on_one_done(self, name, metrics):
        self.results.append(metrics)
        self._add_table_row(metrics)

    def _on_error(self, name, err):
        self._log(f'[错误] {name}: {err}')

    def _on_all_done(self, results):
        self.results = results
        self._update_recommendation()
        self.lbl_progress.setText(f'评估完成: {len(results)} 个模型')
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_export.setEnabled(len(results) > 0)
        self._log('===== 全部评估完成 =====')

    def _add_table_row(self, m):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(m.get('name', '')))
        self.table.setItem(row, 1, QTableWidgetItem(f"{m.get('mAP50', 0):.4f}"))
        self.table.setItem(row, 2, QTableWidgetItem(f"{m.get('mAP50-95', 0):.4f}"))
        self.table.setItem(row, 3, QTableWidgetItem(f"{m.get('precision', 0):.4f}"))
        self.table.setItem(row, 4, QTableWidgetItem(f"{m.get('recall', 0):.4f}"))
        self.table.setItem(row, 5, QTableWidgetItem(f"{m.get('size_mb', 0):.1f}"))
        self.table.setItem(row, 6, QTableWidgetItem(f"{m.get('speed_ms', 0):.1f}"))

        # 最佳 mAP50 高亮
        if m.get('mAP50', 0) >= 0.85:
            for c in range(7):
                self.table.item(row, c).setBackground(QColor('#E6F7E6'))

    def _update_recommendation(self):
        if not self.results:
            self.reco_text.setPlainText('尚无评估结果')
            return

        best = max(self.results, key=lambda x: x.get('mAP50', 0))
        fastest = min(self.results, key=lambda x: x.get('speed_ms', 1e9))
        smallest = min(self.results, key=lambda x: x.get('size_mb', 1e9))

        lines = [
            f'最佳精度: {best["name"]}',
            f'  mAP50={best.get("mAP50",0):.4f}  mAP50-95={best.get("mAP50-95",0):.4f}',
            f'  P={best.get("precision",0):.4f}  R={best.get("recall",0):.4f}  F1={best.get("f1",0):.4f}',
            '',
            f'最快推理: {fastest["name"]}',
            f'  速度={fastest.get("speed_ms",0):.1f}ms  mAP50={fastest.get("mAP50",0):.4f}',
            '',
            f'最小体积: {smallest["name"]}',
            f'  大小={smallest.get("size_mb",0):.1f}MB  mAP50={smallest.get("mAP50",0):.4f}',
        ]

        # 给出建议
        if best['name'] == fastest['name'] == smallest['name']:
            lines.append('')
            lines.append(f'推荐: {best["name"]} (性能、速度、体积均优)')
        else:
            lines.append('')
            lines.append('推荐:')
            lines.append(f'  精度优先: {best["name"]}')
            lines.append(f'  速度优先: {fastest["name"]}')
            lines.append(f'  体积优先: {smallest["name"]}')

        self.reco_text.setPlainText('\n'.join(lines))

    # ---------- 导出 ----------
    def _export_csv(self):
        if not self.results:
            QMessageBox.warning(self, '提示', '没有评估结果可导出')
            return

        default_name = f'eval_report_{len(self.results)}models.csv'
        f, _ = QFileDialog.getSaveFileName(
            self, '导出 CSV 报告', default_name, 'CSV 文件 (*.csv);;所有文件 (*)'
        )
        if not f:
            return

        try:
            with open(f, 'w', encoding='utf-8-sig', newline='') as fp:
                writer = csv.writer(fp)
                writer.writerow([
                    '模型', 'mAP50', 'mAP50-95', 'Precision', 'Recall',
                    'F1', '大小(MB)', '速度(ms)', '评估耗时(s)', '路径'
                ])
                for m in self.results:
                    writer.writerow([
                        m.get('name', ''),
                        f"{m.get('mAP50', 0):.4f}",
                        f"{m.get('mAP50-95', 0):.4f}",
                        f"{m.get('precision', 0):.4f}",
                        f"{m.get('recall', 0):.4f}",
                        f"{m.get('f1', 0):.4f}",
                        f"{m.get('size_mb', 0):.1f}",
                        f"{m.get('speed_ms', 0):.1f}",
                        f"{m.get('eval_sec', 0):.1f}",
                        m.get('path', ''),
                    ])
            self._log(f'报告已导出: {f}')
            QMessageBox.information(self, '成功', f'报告已导出:\n{f}')
        except Exception as e:
            QMessageBox.warning(self, '错误', f'导出失败:\n{e}')

    # ---------- 日志 ----------
    def _log(self, msg):
        self.log_edit.append(msg)
        sb = self.log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())
