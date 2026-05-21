# 桌宠 - 陪你写代码的桌面小伙伴

一只会在你写代码时陪你、根据 Claude Code 状态自动切换表情的桌面宠物。

## 功能

- **12 种状态动画**：空闲、思考中、工作中、完成啦、遇到问题、学习中、有点累了、加油、休息一下、出错了、加载中、拜拜
- **Claude Code 联动**：通过 HTTP API 同步 Claude Code 的推理状态，自动切换宠物动画
- **双版本**：Electron（推荐）和 PyQt5
- **透明窗口、置顶、可拖拽**，不遮挡写代码

## 快速开始

### Electron 版（推荐）

```bash
npm install
npm start
```

### Python 版

```bash
pip install pyqt5
python pet.py
```

或双击 `start.bat`

## Claude Code 联动

项目已配置 `.claude/settings.local.json`，Claude Code 会在以下时机自动通知桌宠：

| 时机 | 桌宠状态 |
|------|----------|
| 收到消息 | 进入思考循环 |
| 执行工具 | 工作中 |
| 工具完成 | 短暂"完成"后继续思考 |
| 推理结束 | 根据时长自动判断：完成/累了/休息 |
| 出错 | 出错了 |

### HTTP API

桌宠在 `127.0.0.1:9527` 提供 HTTP 接口：

```bash
# 获取当前状态
curl http://127.0.0.1:9527/state

# 设置状态
curl -X POST http://127.0.0.1:9527/state -H "Content-Type: application/json" -d '{"state":"thinking"}'

# 发送事件
curl -X POST http://127.0.0.1:9527/trigger -H "Content-Type: application/json" -d '{"event":"user_prompt_submit"}'
```

用 `set_state.py` 或 `send-state.ps1` 也可以直接切换状态：

```bash
python set_state.py thinking
powershell -File send-state.ps1 working
```

## 项目结构

```
├── main.js              # Electron 主进程
├── renderer.js          # Electron 渲染进程
├── pet.html             # 宠物 UI + CSS 动画
├── pet.py               # PyQt5 版本
├── set_state.py         # 状态切换脚本
├── send-state.ps1       # PowerShell 状态切换脚本
├── start.bat            # Windows 一键启动
├── sprites/             # 12 张精灵图 (PNG)
├── .vscode/tasks.json   # VS Code 打开时自动启动
└── .claude/             # Claude Code hooks 配置
```
