# Hermes Desktop

Desktop GUI client for Hermes Agent — 基于 Electron + Vue 3 的桌面 AI 助手应用。

## ✨ 功能特性

### 核心聊天
- 🎨 **微信式聊天界面** — 用户消息右侧，AI 回复左侧，现代聊天习惯
- 💬 **多会话管理** — 创建、切换、重命名、删除对话会话
- 📝 **AI 回复摘要** — 会话列表自动显示最后一条 AI 回复摘要
- 🔀 **多会话并发** — 最多 10 个会话同时生成回复，互不阻塞
- 📋 **消息队列** — 单会话消息队列管理，支持查看和删除队列项

### 智能增强
- 🎤 **语音模式** — 唤醒词激活、浏览器语音识别、流式 TTS 朗读
- 🧠 **上下文管理** — 智能滑动窗口 + LLM 自动摘要，支持超长对话
- 🗃️ **记忆管理** — 项目记忆、用户记忆、Agent 人格管理
- 🔧 **模型切换** — 运行时切换 AI 模型，自动同步 provider 和 API 地址

### 微信集成
- 📱 **Gateway 同步** — 轮询 Hermes Gateway 微信消息，实时推送到客户端
- 📊 **Gateway 数据库浏览** — 可视化查看微信 sessions/messages 表
- 🔄 **会话合并** — 多个微信联系人消息按时间合并为统一会话

### 数据管理
- 💾 **数据库管理** — 可视化管理应用主数据库（会话、消息、配置表）
- 📚 **知识图谱浏览** — Dragonball 知识图谱 nodes/edges 分页查看
- 🧹 **数据库优化** — 自动增量 VACUUM，定期回收空闲页

### 系统
- ⚡ **实时流式响应** — WebSocket 实时通信，token 级流式输出
- 🛠️ **工具调用可视化** — 展示 AI 工具调用过程和结果
- 🚀 **静默启动** — 一键启动，无命令窗口干扰
- 🔁 **一键重启** — 设置面板内重启后端+前端（不影响 Gateway）
- 🛑 **优雅停止** — SIGTERM 停止服务，避免 SQLite WAL 损坏
- 🔒 **安全认证** — 自动生成 Auth Token，HTTP API 鉴权
- 📦 **便携打包** — electron-builder 生成独立 .exe，双击运行

## 📸 应用截图

![Hermes Desktop 界面](./docs/images/screenshot.png)

## 🏗️ 技术架构

### 前端
- **框架**: Electron 33.2.1
- **UI**: Vue 3.5.13 + TypeScript
- **状态管理**: Pinia 2.2.6
- **路由**: Vue Router 4.4.5
- **语音识别**: Web Speech API (SpeechRecognition)
- **TTS**: Edge TTS (edge-tts Python 包)
- **虚拟滚动**: vue-virtual-scroller 2.0
- **构建**: electron-vite 2.3.0 / Vite 6.0
- **打包**: electron-builder 26.8

### 后端
- **框架**: FastAPI (Python, 运行于 WSL)
- **通信**: WebSocket 实时流式 + REST API
- **数据库**: SQLite (Desktop DB + Gateway state.db + Dragonball DB)
- **AI 集成**: Hermes Agent Python SDK
- **TTS**: edge-tts 免费语音合成
- **上下文**: 滑动窗口 + LLM 摘要（100K token budget）

## 🚀 快速开始

### 环境要求

- Node.js >= 18
- Python >= 3.8
- pnpm
- WSL (Windows Subsystem for Linux)

### 一键启动（推荐）

直接双击 `start.bat`，脚本自动：
1. 备份 Gateway 数据库
2. 停止旧的后端和前端进程（**不影响** Hermes Gateway 和龙神服务）
3. 如 Gateway 未运行则启动
4. 隐藏启动 WSL 后端服务（FastAPI :8765）
5. 隐藏启动前端应用（Electron + Vite）
6. 启动窗口自动关闭

**最终效果**：只显示 Electron 客户端窗口，无命令窗口干扰。

### 手动启动

**后端服务** (WSL):
```bash
cd /mnt/d/soso/projects/hermes-desktop
bash start-backend.sh
```

**前端应用** (Windows):
```powershell
cd D:\soso\projects\hermes-desktop
pnpm dev
```

### 安装依赖（首次运行）

```bash
# 前端依赖 (Windows)
cd D:\soso\projects\hermes-desktop
pnpm install

# 后端依赖 (WSL)
cd /mnt/d/soso/projects/hermes-desktop/backend
.venv/bin/pip install -r requirements.txt
```

### 生产打包

```bash
# Windows (CMD)
cmd.exe /c "pnpm run package"

# 输出: release/HermesDesktop.exe (~78MB 便携版)
```

⚠️ 打包前关闭所有 Electron 进程：`taskkill /F /IM electron.exe`

## 📁 项目结构

```
hermes-desktop/
├── backend/                     # Python 后端 (FastAPI)
│   ├── main.py                 # 主入口：WebSocket + REST API
│   ├── config.py               # HOST/PORT 配置
│   ├── requirements.txt        # Python 依赖
│   └── services/               # 业务服务
│       ├── hermes_service.py    # Hermes Agent 对话集成
│       ├── database.py          # SQLite 数据库操作
│       ├── context_manager.py   # 上下文智能管理（滑动窗口+LLM摘要）
│       ├── gateway_sync.py      # Gateway state.db 轮询同步
│       ├── tts_service.py       # Edge TTS 语音合成
│       ├── model_config.py      # 模型配置管理
│       ├── memory_manager.py    # Agent 记忆管理
│       ├── env_manager.py       # 环境变量管理
│       ├── auth.py              # Token 认证
│       └── wechat_gateway.py    # 微信 Gateway REST API
├── src/
│   ├── main/
│   │   └── index.ts            # Electron 主进程：窗口管理、IPC、重启
│   ├── preload/
│   │   └── index.ts            # 预加载脚本：安全 API 桥接
│   └── renderer/
│       ├── index.html           # 入口 HTML
│       └── src/
│           ├── App.vue          # 根组件
│           ├── views/
│           │   └── ChatView.vue # 主聊天界面
│           ├── components/
│           │   ├── SettingsModal.vue       # 设置面板
│           │   ├── MemoryManager.vue       # 记忆管理器
│           │   ├── WeChatManager.vue       # 微信管理
│           │   ├── VoiceMessagePlayer.vue  # 语音消息播放器
│           │   ├── ConfirmDialog.vue       # 确认对话框
│           │   └── Toast.vue              # Toast 通知
│           ├── composables/
│           │   ├── useVoiceMode.ts # 语音模式状态机
│           │   ├── useConfirm.ts   # 确认对话框
│           │   └── useToast.ts     # Toast 通知
│           ├── stores/
│           │   ├── chat.ts     # 聊天状态 + WebSocket 客户端
│           │   └── settings.ts # 设置状态
│           └── data/
│               ├── pinyin-data.ts  # 拼音映射数据
│               └── pinyin-map.ts   # 拼音模糊匹配引擎
├── scripts/                    # 启停脚本
│   ├── start.bat               # Windows 一键启动
│   ├── stop.bat                # Windows 停止
│   ├── start-backend.sh        # WSL 后端启动
│   └── stop.sh                 # WSL 停止（仅后端+前端，不影响 Gateway）
├── docs/
│   ├── images/
│   │   └── screenshot.png      # 截图
│   └── wiki/                   # Wiki 文档（submodule）
├── package.json                # Node.js 依赖与脚本
├── pnpm-lock.yaml             # pnpm 锁文件
├── electron.vite.config.ts    # electron-vite 构建配置
└── tsconfig*.json             # TypeScript 配置
```

## 🎤 语音模式

Hermes Desktop 支持唤醒词激活的语音对话：

1. **唤醒词检测** — 浏览器 SpeechRecognition 监听，支持拼音模糊匹配
2. **流式录音** — 唤醒后自动录音，发送至 AI 获得回复
3. **流式 TTS** — AI 回复按句子分割，逐句转为语音播放
4. **连续对话** — AI 通过 `[CONTINUE]`/`[DONE]` 标记决定是否继续

**唤醒词**：默认 "小马"（可在设置中自定义）

**TTS 语音**：
| 语音 ID | 描述 |
|----------|------|
| `zh-CN-XiaoxiaoNeural` | 中文女声（默认） |
| `zh-CN-YunxiNeural` | 中文男声 |
| `zh-CN-YunyangNeural` | 中文男声（新闻风格） |
| `en-US-JennyNeural` | 英文女声 |
| `ja-JP-NanamiNeural` | 日文女声 |

## 🔧 开发指南

### 可用脚本

```bash
pnpm dev          # 开发模式（Vite HMR，仅前端）
pnpm build        # 生产构建
pnpm package      # 构建 + 打包 .exe
pnpm typecheck    # TypeScript 类型检查
pnpm lint         # 代码规范检查
```

### WSL 跨文件系统注意事项

- 从 WSL 构建前端需使用 `cmd.exe /c "pnpm ..."`，因为 Node.js 是 Windows 程序
- `node_modules` 在 NTFS 挂载路径可能出现 esbuild 二进制版本不匹配，运行 `pnpm install` 修复
- WSL2 网络：推荐 `.wslconfig` 设置 `networkingMode=mirrored` 使 `localhost` 互通

### WebSocket 事件参考

| 事件 | 方向 | 用途 |
|------|------|------|
| `send_message` | 前端→后端 | 用户发送消息 |
| `chat_stream` | 后端→前端 | AI 流式回复 |
| `token` | 后端→前端 | 单个 token |
| `new_message` | 后端→前端 | Gateway 同步的新消息 |
| `session-summary` | 后端→前端 | LLM 自动摘要通知 |

## ❓ 常见问题

### 后端无法启动

检查端口 8765：
```bash
wsl -e bash -c "ss -tlnp | grep 8765"
```

清理旧进程：
```bash
wsl -e bash -c "pkill -f 'python.*hermes-desktop.*main.py'"
```

或直接运行 `start.bat` 自动处理。

### 前端无法连接

1. 确认后端已启动（`start.bat` 或手动启动）
2. 检查连接状态指示器
3. 刷新页面 (F5)

### 多实例

应用强制单例运行。再次运行 `start.bat` 会自动清理并重启。

### WSL2 localhost 不通（打包版 .exe）

创建 `C:\Users\<用户名>\.wslconfig`：
```ini
[wsl2]
networkingMode=mirrored
```

然后 `wsl --shutdown` 重启 WSL。

### 语音模式不工作

- 需要 HTTPS 或 localhost 才能使用浏览器 SpeechRecognition
- 确认后端已启动（TTS 需要后端 edge-tts 服务）
- 检查浏览器控制台是否有 SpeechRecognition 权限错误

## 📄 License

MIT
