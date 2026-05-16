# Hermes Desktop

Desktop GUI client for Hermes Agent - 一个基于 Electron + Vue 3 的桌面 AI 助手应用。

## ✨ 功能特性

- 🎨 **微信式聊天界面** - 用户消息右侧显示，AI 回复左侧显示，符合现代聊天习惯
- 💬 **会话管理** - 支持创建、切换、重命名和删除多个对话会话
- 📝 **AI 回复摘要** - 会话列表自动显示最后一条 AI 回复的摘要内容
- 💾 **持久化存储** - 所有会话和消息自动保存到 SQLite 数据库
- 🔄 **历史会话恢复** - 支持 `hermes --resume` 命令恢复会话上下文
- ⚡ **实时流式响应** - 基于 WebSocket 的实时通信，支持流式输出
- 🛠️ **工具调用支持** - 可视化展示 AI 的工具调用过程和结果

## 🏗️ 技术架构

### 前端
- **框架**: Electron 33.2.1
- **UI**: Vue 3.5.13 + TypeScript
- **状态管理**: Pinia 2.2.6
- **路由**: Vue Router 4.4.5
- **构建工具**: electron-vite 2.3.0

### 后端
- **框架**: FastAPI (Python)
- **通信**: WebSocket 实时流式通信
- **数据库**: SQLite
- **AI 集成**: Hermes Agent Python SDK

## 🚀 快速开始

### 环境要求

- Node.js >= 18
- Python >= 3.8
- pnpm

### 安装依赖

```bash
# 前端依赖
pnpm install

# 后端依赖 (在 WSL 或 Linux 环境中)
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 运行应用

#### 方式一：分别启动

**后端服务** (WSL/Linux):
```bash
cd /path/to/hermes-desktop/backend
source .venv/bin/activate
python main.py
```

**前端应用** (Windows):
```bash
pnpm dev
```

#### 方式二：一键启动
```bash
# 如果有启动脚本
./start.sh
```

## 📁 项目结构

```
hermes-desktop/
├── backend/                 # Python 后端服务
│   ├── main.py             # FastAPI 主程序
│   ├── config.py           # 配置文件
│   ├── services/           # 业务逻辑
│   │   ├── database.py     # SQLite 数据库操作
│   │   └── hermes_service.py  # Hermes Agent 集成
│   └── requirements.txt    # Python 依赖
├── src/
│   ├── main/               # Electron 主进程
│   ├── preload/            # 预加载脚本
│   └── renderer/           # Vue 渲染进程
│       └── src/
│           ├── views/      # 页面组件
│           ├── stores/     # Pinia 状态管理
│           └── router/     # 路由配置
├── package.json            # Node.js 依赖
└── electron.vite.config.ts # 构建配置
```

## 🔧 开发指南

### 可用脚本

```bash
pnpm dev          # 开发模式
pnpm build        # 构建生产版本
pnpm preview      # 预览构建结果
pnpm typecheck    # 类型检查
pnpm lint         # 代码规范检查
```

### 数据库

会话和消息数据默认保存在 `~/.hermes/hermes-desktop.db` (SQLite)。

### 环境变量

- `HERMES_VENV_DIR`: Hermes Agent 虚拟环境路径 (默认: `~/.hermes/hermes-agent/venv`)
- `HERMES_DB_PATH`: 数据库路径 (默认: `~/.hermes/hermes-desktop.db`)

## 📝 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📮 联系方式

- Gitee: https://gitee.com/octave-12/hermes-desktop
- 作者: octave-12

---

Made with ❤️ by octave-12
