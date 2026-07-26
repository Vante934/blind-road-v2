 视界 —— 盲道智能导航系统


> 为视障人群打造的实时环境感知与导航辅助系统


[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)](https://fastapi.tiangolo.com)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-ultralytics-purple)](https://ultralytics.com)
[![PWA](https://img.shields.io/badge/PWA-Ready-orange)](https://web.dev/progressive-web-apps/)


扫码体验


<img src="docs/qrcode.png" width="180">


手机微信/浏览器扫码 → 添加到桌面 → 即用即走


核心特性


| 特性 | 说明 |
|------|------|
|  实时连续检测 | WebSocket视频流，10FPS端到端推理 |
|  适盲语音优先 | 4级分级播报，支持语音指令交互 |
|  30类目标识别 | 盲道+障碍物+地面异常，双阈值策略 |
|  贝叶斯融合决策 | 视觉/音频/轨迹/距离四维度融合 |
|  PWA桌面安装 | 扫码即用，支持添加到手机桌面 |
|  WCAG AAA | 屏幕阅读器兼容，高对比度UI |

一键启动


### Docker（推荐）

```bash
git clone https://github.com/yourname/shijie-nav.git
cd shijie-nav
docker-compose up -d
# 访问 http://localhost:8000
```


### 本地开发

```bash
pip install -r requirements.txt
# VSCode: Ctrl+Shift+B 或 F5
# 命令行: uvicorn backend.main:app --reload
```


## 📊 技术指标


| 指标 | 数值 |
|------|------|
| 端到端延迟 | <200ms (CPU) |
| 检测帧率 | 10-15 FPS |
| 检测类别 | 30类 |
| 数据集规模 | 6600+张标注图片 |
| 模型大小 | ~6MB (YOLOv8n) |


 架构


```
手机PWA浏览器
  ├─ 摄像头采集(10FPS)
  ├─ WebSocket实时传输
  ├─ Canvas检测框渲染
  └─ Web Speech API语音播报
         ↕ WebSocket
FastAPI后端
  ├─ StreamSession（每连接独立）
  ├─ UnifiedDetector（YOLOv8+优化）
  ├─ IntegratedPipeline（5阶段流水线）
  ├─ BayesianFusionEngine（四维融合）
  └─ WarningEngine（4级预警防抖）
```
