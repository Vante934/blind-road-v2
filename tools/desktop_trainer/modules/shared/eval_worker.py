# ============================================================
# eval_worker.py - 模型评估线程
# ============================================================
import os
import time
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal


class EvalWorker(QThread):
    """依次评估多个模型"""

    log_signal      = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)
    one_done_signal = pyqtSignal(str, dict)
    all_done_signal = pyqtSignal(list)
    error_signal    = pyqtSignal(str, str)

    def __init__(self, model_specs, data_yaml, imgsz=640):
        super().__init__()
        self.model_specs = model_specs
        self.data_yaml   = data_yaml
        self.imgsz       = imgsz
        self._stop       = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            from ultralytics import YOLO
        except Exception as e:
            self.error_signal.emit('*', f'导入 ultralytics 失败: {e}')
            return

        results = []
        total = len(self.model_specs)

        for i, spec in enumerate(self.model_specs):
            if self._stop:
                self.log_signal.emit('评估已中止')
                break

            name = spec['name']
            path = spec['path']
            self.progress_signal.emit(i + 1, total)
            self.log_signal.emit(f'\n[{i+1}/{total}] 评估 {name} ...')

            try:
                size_mb = os.path.getsize(path) / (1024 * 1024)
                model = YOLO(path)

                t0 = time.time()
                r = model.val(
                    data=str(self.data_yaml),
                    imgsz=self.imgsz,
                    verbose=False,
                    plots=False,
                )
                elapsed = time.time() - t0

                rd = r.results_dict if hasattr(r, 'results_dict') else {}
                mAP50    = float(rd.get('metrics/mAP50(B)', 0))
                mAP50_95 = float(rd.get('metrics/mAP50-95(B)', 0))
                precision= float(rd.get('metrics/precision(B)', 0))
                recall   = float(rd.get('metrics/recall(B)', 0))
                f1 = 2 * precision * recall / max(precision + recall, 1e-6)

                speed_ms = 0.0
                if hasattr(r, 'speed') and isinstance(r.speed, dict):
                    speed_ms = float(r.speed.get('inference', 0))

                metrics = {
                    'name':      name,
                    'path':      path,
                    'mAP50':     mAP50,
                    'mAP50-95':  mAP50_95,
                    'precision': precision,
                    'recall':    recall,
                    'f1':        f1,
                    'size_mb':   size_mb,
                    'speed_ms':  speed_ms,
                    'eval_sec':  elapsed,
                }
                results.append(metrics)
                self.log_signal.emit(
                    f'  mAP50={mAP50:.4f}  mAP50-95={mAP50_95:.4f}  '
                    f'P={precision:.4f}  R={recall:.4f}  '
                    f'{size_mb:.1f}MB  {speed_ms:.1f}ms'
                )
                self.one_done_signal.emit(name, metrics)

            except Exception as e:
                import traceback
                self.log_signal.emit(f'  [失败] {e}')
                print(f'[{name}] 完整错误:\n{traceback.format_exc()}')
                self.error_signal.emit(name, str(e)[:300])

        self.all_done_signal.emit(results)
