# ============================================================
# training_worker.py - 训练线程
# ============================================================
import os
import sys
import io
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal


class TrainingWorker(QThread):
    """单个模型训练线程"""

    log_signal      = pyqtSignal(str)              # 日志文本
    progress_signal = pyqtSignal(int, int)         # (当前epoch, 总epoch)
    finished_signal = pyqtSignal(str, dict)        # (模型名, 结果)
    error_signal    = pyqtSignal(str, str)         # (模型名, 错误)

    def __init__(self, model_file, data_yaml, epochs, batch, imgsz,
                 project_dir, model_name):
        super().__init__()
        self.model_file  = model_file
        self.data_yaml   = data_yaml
        self.epochs      = epochs
        self.batch       = batch
        self.imgsz       = imgsz
        self.project_dir = project_dir
        self.model_name  = model_name
        self._should_stop = False

    def stop(self):
        self._should_stop = True

    def run(self):
        try:
            self.log_signal.emit(f'[{self.model_name}] 开始加载模型 {self.model_file}')

            from ultralytics import YOLO

            model = YOLO(self.model_file)
            self.log_signal.emit(f'[{self.model_name}] 模型加载成功，开始训练...')
            self.log_signal.emit(f'[{self.model_name}] 参数: epochs={self.epochs}, '
                                 f'batch={self.batch}, imgsz={self.imgsz}')

            def on_epoch_end(trainer):
                cur = trainer.epoch + 1
                self.progress_signal.emit(cur, self.epochs)
                metrics = trainer.metrics or {}
                m50 = metrics.get('metrics/mAP50(B)', 0)
                self.log_signal.emit(
                    f'[{self.model_name}] Epoch {cur}/{self.epochs}  mAP50={m50:.4f}'
                )
                if self._should_stop:
                    trainer.stop_training = True

            try:
                model.add_callback('on_fit_epoch_end', on_epoch_end)
            except Exception:
                pass

            results = model.train(
                data=str(self.data_yaml),
                epochs=self.epochs,
                imgsz=self.imgsz,
                batch=self.batch,
                project=str(self.project_dir),
                name=self.model_name,
                exist_ok=True,
                verbose=False,
                plots=True,
                save=True,
            )

            metrics_dict = {}
            try:
                r = results.results_dict if hasattr(results, 'results_dict') else {}
                metrics_dict = {
                    'mAP50':    float(r.get('metrics/mAP50(B)', 0)),
                    'mAP50-95': float(r.get('metrics/mAP50-95(B)', 0)),
                    'precision':float(r.get('metrics/precision(B)', 0)),
                    'recall':   float(r.get('metrics/recall(B)', 0)),
                }
            except Exception:
                pass

            self.log_signal.emit(f'[{self.model_name}] 训练完成! mAP50={metrics_dict.get("mAP50", 0):.4f}')
            self.finished_signal.emit(self.model_name, metrics_dict)

        except Exception as e:
            import traceback
            err = f'{e}\n{traceback.format_exc()}'
            self.error_signal.emit(self.model_name, err)
