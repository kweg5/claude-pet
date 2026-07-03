# 🐾 Claude Pet

Claude Code 桌面宠物 — 一个会根据 Claude Code 运行状态自动切换动画的像素风宠物。

## ✨ 功能

- 🎬 **状态联动** — 宠物动画自动反映 Claude Code 的工作状态
- 💬 **对话气泡** — 实时显示 Claude Code 正在做什么
- ❗ **权限提醒** — 需要确认操作时显示感叹号
- 🖱️ **点击跳转** — 点击气泡直接切到 Claude Code 窗口
- 🚀 **自动启动** — 打开终端时宠物自动出现

## 🎭 动画状态

| 状态 | 动画 | 触发场景 |
|------|------|----------|
| 空闲 | `idle` | 等待用户输入 |
| 执行中 | `running` | 运行 Bash/PowerShell 命令 |
| 读取中 | `review` | 读取文件、搜索 |
| 写入中 | `running` | 写入/编辑文件 |
| 等待确认 | `waiting` | 需要权限确认（显示 ❗） |
| 失败 | `failed` | 工具执行出错 |
| 完成 | `wave` | 会话结束 |

## 📦 安装

### 前置条件

- Python 3.8+
- Claude Code

### 自动安装（Windows）

```bash
git clone https://github.com/kweg5/claude-pet.git
cd claude-pet
install.bat
```

### 手动安装

```bash
git clone https://github.com/kweg5/claude-pet.git
cd claude-pet
pip install -r requirements.txt
```

然后将 `.claude/settings.json` 复制到你的 Claude Code 项目目录。

## 🚀 使用

### 启动宠物

```bash
pythonw claude_pet.py
```

### 自动启动

安装脚本会配置 PowerShell Profile，打开新终端时宠物自动启动。

### 与 Claude Code 联动

在你的 Claude Code 项目根目录放置 `.claude/settings.json`，宠物会根据 Claude Code 的状态自动切换动画和气泡。

## 🎨 自定义

### 修改精灵图

替换 `claude-pixel-spritesheet.webp`，保持相同的网格布局（8 列 × 9 行）：

| 行 | 动画 |
|----|------|
| 0 | idle |
| 1 | run_r |
| 2 | run_l |
| 3 | wave |
| 4 | jump |
| 5 | failed |
| 6 | waiting |
| 7 | running |
| 8 | review |

### 修改配置

在 `claude_pet.py` 顶部可以调整：

```python
SCALE = 0.5          # 精灵缩放比例
FPS = 8              # 动画帧率
WALK_SPEED = 2       # 移动速度
BUBBLE_HIDE_DELAY = 3000  # 气泡自动隐藏延迟（毫秒）
```

## 📁 项目结构

```
claude-pet/
├── claude_pet.py                    # 桌面宠物主程序
├── pet_state.py                     # Claude Code hook 脚本
├── claude-pixel-spritesheet.webp    # 精灵图
├── .claude/
│   └── settings.json                # Claude Code hook 配置
├── requirements.txt                 # Python 依赖
├── install.bat                      # Windows 安装脚本
└── README.md
```

## 🔧 工作原理

1. Claude Code 的 hook 系统在每次工具调用时触发 `pet_state.py`
2. `pet_state.py` 将当前状态写入 `.pet_state` 文件
3. `claude_pet.py` 每 500ms 读取状态文件，切换动画和气泡
4. 点击气泡时通过 Win32 API 查找并置顶 Claude Code 终端窗口

## 📄 License

MIT
