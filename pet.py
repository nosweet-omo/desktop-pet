"""
桌宠 - 陪你写代码的桌面小伙伴
基于 PyQt5，支持透明窗口、12种状态、HTTP API 联动 Claude Code
智能状态机：思考循环 → 时长追踪 → 累/休息判断
"""
import sys
import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMenu, QSystemTrayIcon, QWidget
)
from PyQt5.QtCore import (
    Qt, QPoint, QTimer, pyqtSignal, QObject
)
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QMouseEvent

# ── 项目目录 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
SPRITES_DIR = BASE_DIR / "sprites"

# ── 状态定义 ──────────────────────────────────────────────
STATES = [
    "idle", "thinking", "working", "done",
    "problem", "study", "tired", "cheer",
    "rest", "error", "loading", "bye"
]

STATE_LABELS = {
    "idle": "空闲/待机",
    "thinking": "思考中",
    "working": "工作中",
    "done": "完成啦",
    "problem": "遇到问题",
    "study": "学习中",
    "tired": "有点累了",
    "cheer": "加油",
    "rest": "休息一下",
    "error": "出错了",
    "loading": "加载中",
    "bye": "拜拜",
}

# 自动回到 idle 的延迟（毫秒）
AUTO_IDLE_DELAYS = {
    "done": 5000,
    "cheer": 4000,
    "problem": 8000,
    "error": 6000,
    "tired": 8000,
    "rest": 10000,
    "bye": 1500,
}

# 时长阈值（秒）
DURATION_TIRED = 300   # 5 分钟 → 有点累了
DURATION_REST = 900     # 15 分钟 → 休息一下

# 思考循环的状态序列
THINK_CYCLE = ["thinking", "study", "loading", "working"]
THINK_INTERVAL = 2000  # 每 2 秒切换


# ── 线程安全的共享状态 ────────────────────────────────────
_state_lock = threading.Lock()
_shared_state = "idle"


def get_shared_state():
    with _state_lock:
        return _shared_state


def set_shared_state(state):
    global _shared_state
    with _state_lock:
        _shared_state = state


# ── 信号发射器 ────────────────────────────────────────────
class StateSignals(QObject):
    state_changed = pyqtSignal(str)
    trigger_event = pyqtSignal(str)


signals = StateSignals()


# ── HTTP 状态服务 ─────────────────────────────────────────
class StateHandler(BaseHTTPRequestHandler):
    """本地 HTTP API: GET/POST /state, POST /trigger"""

    def log_message(self, format, *args):
        pass

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/state":
            current = get_shared_state()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors_headers()
            self.end_headers()
            resp = {"state": current, "label": STATE_LABELS.get(current, current)}
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                "pet": "桌宠",
                "states": STATES,
                "current": get_shared_state(),
            }, ensure_ascii=False).encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self._send_cors_headers()
            self.end_headers()
            return

        if self.path == "/state":
            state = data.get("state", "")
            if state in STATES:
                set_shared_state(state)
                signals.state_changed.emit(state)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(
                    {"success": True, "state": state}, ensure_ascii=False
                ).encode())
            else:
                self.send_response(400)
                self._send_cors_headers()
                self.end_headers()

        elif self.path == "/trigger":
            event = data.get("event", "")
            if event:
                signals.trigger_event.emit(event)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(
                {"success": True, "event": event}, ensure_ascii=False
            ).encode())


def start_http_server():
    """在后台线程启动 HTTP 状态服务"""
    server = HTTPServer(("127.0.0.1", 9527), StateHandler)
    print(f"  状态服务已启动: http://127.0.0.1:9527")
    server.serve_forever()


# ── 宠物窗口（智能状态机）────────────────────────────────
class PetWindow(QWidget):
    """透明、无边框、置顶的宠物窗口 + 智能状态机"""

    def __init__(self):
        super().__init__()
        self.current_state = "loading"
        self.auto_idle_timer = None
        self.think_cycle_timer = None
        self.think_cycle_idx = 0
        self.session_start_time = None   # 对话开始时间
        self.session_has_error = False   # 对话中是否有错误
        self.drag_pos = QPoint()

        self._setup_ui()
        self._setup_signals()
        # 启动动画
        QTimer.singleShot(1200, lambda: self.set_state("idle"))

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(313, 418)
        self.current_pixmap = None
        self._update_sprite("loading")
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - 340, screen.height() - 480)

    def _setup_signals(self):
        signals.state_changed.connect(self.set_state)
        signals.trigger_event.connect(self._handle_trigger)

    def paintEvent(self, event):
        if self.current_pixmap and not self.current_pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            pw = self.current_pixmap.width()
            ph = self.current_pixmap.height()
            x = (self.width() - pw) // 2
            y = (self.height() - ph) // 2
            painter.drawPixmap(x, y, self.current_pixmap)
            painter.end()

    def _update_sprite(self, state):
        path = SPRITES_DIR / f"{state}.png"
        if path.exists():
            self.current_pixmap = QPixmap(str(path))
            self.update()

    # ── 核心状态机逻辑 ──────────────────────────────────

    def set_state(self, state):
        """直接设置状态（供手动切换和直接 API 调用）"""
        if state == self.current_state:
            return

        prev = self.current_state
        self.current_state = state
        set_shared_state(state)
        self._update_sprite(state)
        self._play_transition()

        # 管理自动 idle
        self._cancel_auto_idle()
        delay = AUTO_IDLE_DELAYS.get(state)
        if delay:
            self.auto_idle_timer = QTimer(self)
            self.auto_idle_timer.setSingleShot(True)
            self.auto_idle_timer.timeout.connect(lambda: self.set_state("idle"))
            self.auto_idle_timer.start(delay)

        if hasattr(self, "tray") and self.tray:
            self._update_tray_menu()

        print(f"  状态: {STATE_LABELS.get(prev, prev)} → {STATE_LABELS.get(state, state)}")

    def _handle_trigger(self, event):
        """处理来自 Claude Code 的事件触发"""
        print(f"  事件: {event}")

        if event == "user_prompt_submit":
            # 用户发送消息 → 开始思考
            self.session_start_time = time.time()
            self.session_has_error = False
            self._start_think_cycle()

        elif event == "pre_tool_use":
            # 准备执行工具 → 工作中
            self._stop_think_cycle()
            self.set_state("working")

        elif event == "post_tool_use":
            # 工具执行完毕 → 短暂完成 → 继续思考
            self._stop_think_cycle()
            self.set_state("done")
            # 短暂显示 "完成" 后继续思考循环
            QTimer.singleShot(800, lambda: self._start_think_cycle())

        elif event == "stop":
            # 推理结束 → 判断最终状态
            self._stop_think_cycle()
            self._finish_session()

        elif event == "error":
            # 工具执行出错
            self.session_has_error = True
            self._stop_think_cycle()
            self.set_state("error")

    def _start_think_cycle(self):
        """启动思考循环：thinking → study → loading → working 轮播"""
        if self.think_cycle_timer is not None:
            self.think_cycle_timer.stop()

        self.think_cycle_idx = 0
        # 先立即切换到 thinking
        self.set_state("thinking")
        # 然后启动定时器轮播
        self.think_cycle_timer = QTimer(self)
        self.think_cycle_timer.timeout.connect(self._think_cycle_tick)
        self.think_cycle_timer.start(THINK_INTERVAL)

    def _think_cycle_tick(self):
        """思考循环的每一步"""
        self.think_cycle_idx = (self.think_cycle_idx + 1) % len(THINK_CYCLE)
        state = THINK_CYCLE[self.think_cycle_idx]
        # 不触发完整的 set_state（避免打断 auto-idle 等），直接更新精灵
        self.current_state = state
        set_shared_state(state)
        self._update_sprite(state)

    def _stop_think_cycle(self):
        """停止思考循环"""
        if self.think_cycle_timer is not None:
            self.think_cycle_timer.stop()
            self.think_cycle_timer = None

    def _finish_session(self):
        """推理结束，根据时长和错误情况决定最终状态"""
        if self.session_has_error:
            self.set_state("problem")
            return

        if self.session_start_time:
            elapsed = time.time() - self.session_start_time
            print(f"  本次对话耗时: {elapsed:.0f} 秒")
            if elapsed > DURATION_REST:
                self.set_state("rest")
            elif elapsed > DURATION_TIRED:
                self.set_state("tired")
            else:
                self.set_state("done")
        else:
            self.set_state("done")

        self.session_start_time = None

    def _cancel_auto_idle(self):
        if self.auto_idle_timer is not None:
            self.auto_idle_timer.stop()
            self.auto_idle_timer = None

    def _play_transition(self):
        self.setWindowOpacity(0.7)
        QTimer.singleShot(80, lambda: self.setWindowOpacity(1.0))

    # ── 拖拽 ────────────────────────────────────────────
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and not self.drag_pos.isNull():
            self.move(event.globalPos() - self.drag_pos)

    # ── 右键菜单 ────────────────────────────────────────
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(30, 30, 30, 230);
                border: 1px solid rgba(255,255,255,40);
                border-radius: 8px;
                padding: 4px 0;
                color: #e0e0e0;
                font-family: "Microsoft YaHei";
                font-size: 13px;
            }
            QMenu::item { padding: 6px 20px; }
            QMenu::item:selected {
                background: rgba(255,255,255,30);
                border-radius: 4px;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255,255,255,30);
                margin: 2px 8px;
            }
        """)

        current_label = menu.addAction(f"当前: {STATE_LABELS.get(self.current_state, self.current_state)}")
        current_label.setEnabled(False)
        menu.addSeparator()

        for s in STATES:
            action = menu.addAction(STATE_LABELS.get(s, s))
            action.setCheckable(True)
            action.setChecked(s == self.current_state)
            action.triggered.connect(lambda checked, st=s: self._manual_override(st))

        menu.addSeparator()
        quit_action = menu.addAction("退出桌宠  ✕")
        quit_action.triggered.connect(QApplication.quit)
        menu.exec_(event.globalPos())

    def _manual_override(self, state):
        """手动切换状态：停止所有自动逻辑"""
        self._stop_think_cycle()
        self._cancel_auto_idle()
        self.session_start_time = None
        self.set_state(state)

    # ── 托盘 ────────────────────────────────────────────
    def setup_tray(self):
        icon_path = SPRITES_DIR / "idle.png"
        tray_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(tray_icon)
        self.tray.setToolTip("桌宠 - 陪你写代码")
        self._update_tray_menu()
        self.tray.show()

    def _update_tray_menu(self):
        if not hasattr(self, "tray") or not self.tray:
            return
        menu = QMenu()
        current = menu.addAction(f"当前: {STATE_LABELS.get(self.current_state, self.current_state)}")
        current.setEnabled(False)
        menu.addSeparator()
        for s in STATES:
            action = menu.addAction(STATE_LABELS.get(s, s))
            action.triggered.connect(lambda checked, st=s: self._manual_override(st))
        menu.addSeparator()
        quit_action = menu.addAction("退出桌宠")
        quit_action.triggered.connect(QApplication.quit)
        self.tray.setContextMenu(menu)


# ── 主入口 ────────────────────────────────────────────────
def main():
    from PyQt5.QtNetwork import QLocalSocket

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 单实例检查
    socket = QLocalSocket()
    socket.connectToServer("desktop-pet-instance")
    if socket.waitForConnected(500):
        socket.write(b'{"event":"user_prompt_submit"}')
        socket.flush()
        socket.close()
        print("桌宠已在运行中")
        sys.exit(0)
    socket.close()

    # HTTP 服务
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    # 窗口
    pet = PetWindow()
    pet.show()
    pet.setup_tray()

    print("=" * 40)
    print("  桌宠已就位！")
    print("  HTTP API: http://127.0.0.1:9527")
    print("  右键点击宠物切换状态 | 拖拽移动")
    print("=" * 40)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
