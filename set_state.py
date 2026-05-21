"""桌宠状态/事件触发脚本——给 Claude Code hooks 调用

用法:
  python set_state.py thinking        # 直接设置状态
  python set_state.py trigger user_prompt_submit  # 发送触发事件
"""
import sys
import json
import urllib.request

STATES = [
    "idle", "thinking", "working", "done",
    "problem", "study", "tired", "cheer",
    "rest", "error", "loading", "bye"
]

EVENTS = [
    "user_prompt_submit",  # 用户发送消息 → 开始思考循环
    "pre_tool_use",        # 准备执行工具 → 工作中
    "post_tool_use",       # 工具执行完毕 → 短暂完成 → 继续思考
    "stop",                # 推理结束 → 判断最终状态
    "error",               # 出错了
]


def send(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass  # 静默失败，不打断 Claude Code


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python set_state.py <state>")
        print("      python set_state.py trigger <event>")
        print(f"状态: {STATES}")
        print(f"事件: {EVENTS}")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "trigger" and len(sys.argv) >= 3:
        event = sys.argv[2]
        if event in EVENTS:
            send("http://127.0.0.1:9527/trigger", {"event": event})
        else:
            print(f"未知事件: {event}")
            sys.exit(1)
    elif arg in STATES:
        send("http://127.0.0.1:9527/state", {"state": arg})
    else:
        # 兼容旧用法：直接当 trigger 事件处理
        if arg in EVENTS:
            send("http://127.0.0.1:9527/trigger", {"event": arg})
        else:
            print(f"未知状态或事件: {arg}")
            sys.exit(1)
