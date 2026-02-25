# DESIGN.md - 技术设计

## 核心目标

1. **pjsk Live2D 模型** - 支持 Project SEKAI 的 Live2D 模型加载、渲染、切换
2. **AI 对话** - 接入大模型，让角色能自然对话

## 技术选型建议

### 方案 A：Electron（推荐零基础）
- **渲染层**：PixiJS + pixi-live2d-display
- **桌面层**：Electron
- **AI 层**：直接调用 OpenAI/火山引擎等 API
- **优点**：Web 技术，资料多，pjsk 模型本身就是 Web 格式

### 方案 B：C# (WPF)
- **渲染层**：Live2D Cubism SDK for Native
- **桌面层**：WPF / WinUI 3
- **优点**：原生 Windows 性能好
- **缺点**：上手 harder

## 模块划分

```
Live2DPet/
├── ModelManager/      # pjsk 模型管理
│   ├── 下载/预览
│   └── 本地库管理
├── Live2DRenderer/    # Live2D 渲染
│   ├── 模型加载
│   ├── 动作/表情控制
│   └── 鼠标交互
├── AICore/            # AI 核心
│   ├── LLM 对话
│   ├── TTS 语音
│   └── RAG 记忆
└── OpenClaw/          # OpenClaw 接入
```

## pjsk 模型

- 来源：https://sekai.best/l2d
- 格式：Live2D Cubism 3.0+
- 需要：模型解析、加载、渲染

## AI 对话流程

1. 用户输入（文字/语音）
2. LLM 生成回复
3. 情绪分析 → 映射到 Live2D 动作/表情
4. TTS 生成语音
5. Live2D 执行动作 + 播放语音
