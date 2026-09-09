<div align="center">

# 👁️ 视界 · 盲道智能导航系统

> 为视障人群打造的实时环境感知与导航辅助系统

**🐍 Python 3.11** &nbsp;|&nbsp; **⚡ FastAPI** &nbsp;|&nbsp; **🎯 YOLOv8** &nbsp;|&nbsp; **📱 PWA Ready** &nbsp;|&nbsp; **📄 MIT License**

[快速开始](#-快速开始) · [文档](#-项目架构) · [报告问题](https://github.com/Vante934/blind-road-v2/issues)

</div>

---

## 📖 项目简介

**视界** 是一款专为视障人群设计的智能导航辅助系统。通过手机摄像头实时采集环境图像，结合深度学习目标检测技术，能够精准识别盲道、障碍物及地面异常，并通过分级语音播报为用户提供即时的环境感知与导航指引。

系统采用 PWA 技术架构，用户只需扫码即可使用，无需安装 APP，真正实现"即用即走"。

---

## ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🎥 **实时连续检测** | WebSocket 视频流传输，端到端推理可达 10FPS |
| 🔊 **适盲语音优先** | 4 级分级播报机制，支持语音指令交互 |
| 🎯 **30 类目标识别** | 盲道、障碍物、地面异常全覆盖，双阈值检测策略 |
| 🧠 **贝叶斯融合决策** | 视觉/音频/轨迹/距离四维度智能融合 |
| 📱 **PWA 桌面安装** | 扫码即用，支持添加到手机桌面，离线可用 |
| ♿ **WCAG AAA 标准** | 屏幕阅读器兼容，高对比度无障碍 UI |

---

## 📊 技术指标

| 指标 | 数值 |
|------|------|
| 端到端延迟 | < 200ms (CPU) |
| 检测帧率 | 10 - 15 FPS |
| 检测类别 | 30 类 |
| 数据集规模 | 6,600+ 张标注图片 |
| 模型大小 | ~ 6MB (YOLOv8n) |
| 支持平台 | iOS / Android / 桌面浏览器 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    手机 PWA 浏览器                       │
│  ┌─────────────┬──────────────┬─────────────────────┐   │
│  │ 摄像头采集   │ WebSocket 传输 │ Canvas 检测框渲染    │   │
│  │  (10FPS)    │   (实时)      │                     │   │
│  └─────────────┴──────────────┴─────────────────────┘   │
│  ┌───────────────────────────────────────────────────┐   │
│  │         Web Speech API 语音播报                    │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────┘
                           │ WebSocket
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI 后端                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │           StreamSession (每连接独立)               │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │         UnifiedDetector (YOLOv8 + 优化)           │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │      IntegratedPipeline (5 阶段流水线)             │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │     BayesianFusionEngine (四维融合决策)            │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │       WarningEngine (4 级预警防抖)                 │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### Docker 部署（推荐）

```bash
# 克隆项目
git clone https://github.com/Vante934/blind-road-v2.git
cd blind-road-v2

# 启动服务
docker-compose up -d

# 访问 http://localhost:8000
```

### 本地开发

```bash
# 克隆项目
git clone https://github.com/Vante934/blind-road-v2.git
cd blind-road-v2

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
# VSCode: Ctrl+Shift+B 或 F5
# 命令行:
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问 `http://localhost:8000` 即可使用。

---

## 📁 项目结构

```
blind-road-v2/
├── backend/              # 后端服务
│   ├── main.py          # FastAPI 入口
│   ├── detector/        # 目标检测模块
│   ├── navigation/      # 导航决策模块
│   └── voice/           # 语音播报模块
├── frontend/            # 前端 PWA 应用
│   ├── src/
│   └── public/
├── models/              # AI 模型
│   └── best.pt          # YOLOv8 权重文件
├── tools/               # 工具脚本
├── docs/                # 文档资源
├── requirements.txt     # Python 依赖
├── docker-compose.yml   # Docker 编排
├── Dockerfile           # Docker 镜像
├── Makefile             # 构建脚本
└── README.md            # 项目说明
```

---

## 🛠️ 技术栈

**后端：**
- 🐍 Python 3.11
- ⚡ FastAPI - Web 框架
- 🔌 WebSocket - 实时通信
- 🎯 Ultralytics YOLOv8 - 目标检测
- 🖼️ OpenCV - 图像处理

**前端：**
- 🌐 HTML5 / CSS3 / JavaScript
- 🔊 Web Speech API - 语音合成
- 🎨 Canvas API - 实时渲染
- 📱 Service Worker - PWA 离线支持

**部署：**
- 🐳 Docker / Docker Compose
- ☁️ Railway / 云服务器部署

---

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 🙏 致谢

感谢所有为视障群体出行便利做出贡献的开发者和研究者。

---

<div align="center">

**如果这个项目对你有帮助，欢迎给个 ⭐ Star 支持一下！**

Made with ❤️ for accessibility

</div>
