# 视界 · 盲道智能导航 — 桌面训练工具

一款基于 PyQt5 + Ultralytics YOLO 的一体化模型训练工具，支持数据标注、多模型对比训练、模型评估三大功能。

## 功能特性

### 数据标注
- 支持文件夹选择 / 多文件选择 / 拖拽三种加载方式
- 6 类目标框标注（盲道、障碍物、行人、车辆、坑洼、台阶）
- 键盘快捷键（Z 撤销 / S 保存 / 方向键切图 / 1-6 选类别）
- 自动保存为 YOLO 格式 `.txt` 标签
- 记忆上次工作目录

### 模型训练
- 支持 4 个模型：YOLOv8n、YOLOv8s、YOLO11n、YOLO11s
- 多模型队列训练，一键跑完全部对比
- QThread 子线程执行，界面不卡死
- 实时日志 + 进度条 + 训练结果汇总
- 训练前自动校验数据集配置

### 模型评估
- 自动扫描项目内所有 `.pt` 模型
- 统一验证集评估多模型
- 输出对比表格：mAP50 / mAP50-95 / Precision / Recall / 大小 / 速度
- 综合评分推荐最优模型
- 导出 CSV 报告

## 快速开始

### 环境要求
- Python 3.8+
- Windows 10 / 11（其他系统需手动运行 `main.py`）
- 显卡建议：NVIDIA GPU + CUDA（无 GPU 也能运行，仅速度较慢）

### 安装

```bash
pip install -r requirements.txt
```

依赖：

```
PyQt5 >= 5.15
ultralytics >= 8.0
opencv-python
matplotlib
numpy
PyYAML
```

### 启动

Windows 用户：双击 `启动.bat`

其他系统：

```bash
python main.py
```

## 目录结构

```
desktop_trainer/
├── main.py                    # 程序入口
├── config.py                  # 全局配置（类别、颜色、样式）
├── requirements.txt           # 依赖
├── 启动.bat                    # Windows 一键启动
├── modules/
│   ├── annotation_tab.py      # 标注 Tab
│   ├── training_tab.py        # 训练 Tab
│   ├── testing_tab.py         # 评估 Tab
│   └── shared/
│       ├── canvas_widget.py       # 画布控件
│       ├── training_worker.py     # 训练线程
│       └── eval_worker.py         # 评估线程
├── models/                    # 放预训练模型 (.pt)
├── results/                   # 训练输出目录
└── datasets/                  # 数据集目录
```

## 数据集格式

标注 Tab 输出的标签为 YOLO 格式，需自行准备 `dataset.yaml`：

```yaml
path: F:/your/dataset/absolute/path    # 建议使用绝对路径
train: images
val: images
nc: 6
names: [blind_path, obstacle, person, vehicle, pothole, step]
```
