"""Opt-in, app-scoped macOS observations. No screenshots, raw key logging, or LLM calls."""

from __future__ import annotations

import hashlib
import json
import queue
import sys
import threading
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

from .apps import FULL_APPS, match_app, monitoring_settings
from .collect import redact

MAX_NODES = 400
MAX_TEXT = 16000


def full_enabled(settings, app_id):
    item = settings.get(app_id, {})
    return bool(item.get("enabled") and item.get("mode") == "full" and item.get("consented"))


def document_path(value):
    if not isinstance(value, str):
        return ""
    if value.startswith("file://"):
        parsed = urlparse(value)
        if parsed.netloc not in ("", "localhost"):
            return ""
        value = unquote(parsed.path)
    return value if value.startswith("/") else ""


def wechat_document(path, roots):
    if not path:
        return False
    # Lexical paths alone must not attribute a symlink into another app's data to WeChat.
    resolved = Path(path).resolve()
    return any(resolved.is_relative_to(Path(root).resolve()) for root in roots)


def snapshot_events(snapshot, previous, settings, roots):
    """Produce evidence with honest semantics; UI text is never guessed to be a sent message."""
    app = match_app(snapshot.get("app"), {"bundle_id": snapshot.get("bundle_id")})
    now = snapshot["ts"]
    identity = (snapshot.get("pid"), snapshot.get("window", ""), snapshot.get("document", ""))
    before_identity = previous.get("identity")
    events = []
    if settings.get("wechat", {}).get("enabled"):
        path = document_path(snapshot.get("document"))
        if wechat_document(path, roots) and identity != before_identity:
            events.append(
                (
                    "wechat",
                    "document_opened",
                    Path(path).name,
                    {
                        "file": path,
                        "viewing_app": snapshot.get("app"),
                        "evidence": "foreground_AXDocument",
                        "meaning": "微信目录中的文件出现在前台应用的文档窗口。",
                    },
                )
            )
    previous["identity"] = identity
    if not app or not full_enabled(settings, app["id"]) or snapshot.get("secure"):
        previous.pop("full", None)
        return events
    key = (app["id"], identity, settings[app["id"]]["consented"])
    old = previous.get("full", {})
    same = old.get("key") == key
    context = {
        "window": snapshot.get("window", ""),
        "file": document_path(snapshot.get("document")),
        "evidence": "accessibility",
        "captured_at": now,
    }
    if not same:
        events.append((app["id"], "window_context", context["window"] or app["name"], context))
    text = snapshot.get("text", "")[:MAX_TEXT]
    if text and (not same or text != old.get("text")):
        events.append(
            (
                app["id"],
                "visible_content",
                context["window"] or "可见内容发生变化",
                {
                    **context,
                    "text": text,
                    "truncated": snapshot.get("truncated", False),
                    "meaning": "当时可读取的窗口文本；可能包含收发消息，但未推断发送人或收发方向。",
                },
            )
        )
    field = snapshot.get("field", "")
    draft = snapshot.get("draft")
    if draft is not None and same and field == old.get("field") and draft != old.get("draft"):
        events.append(
            (
                app["id"],
                "input_changed",
                "输入框内容变化",
                {
                    **context,
                    "text": draft[:MAX_TEXT],
                    "field": field,
                    "meaning": "输入框快照，包含输入、粘贴或编辑；不代表已经发送。",
                },
            )
        )
    previous["full"] = {"key": key, "text": text, "draft": draft, "field": field}
    return events


def save_events(store, events, ts, settings):
    """Recheck consent in the write transaction; a paused or downgraded app cannot persist queued content."""
    total = 0
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        current = monitoring_settings(db)
        for app_id, kind, title, payload in events:
            config = current[app_id]
            if not config["enabled"]:
                continue
            if kind != "document_opened" and (
                not full_enabled(current, app_id)
                or config["consented"] != settings.get(app_id, {}).get("consented")
            ):
                continue
            safe = redact(payload)
            encoded = json.dumps(safe, ensure_ascii=False)
            external = hashlib.sha256(f"{ts}:{kind}:{encoded}".encode()).hexdigest()
            from .apps import definition

            app = definition(app_id)
            total += db.execute(
                "INSERT OR IGNORE INTO activity(source,external_id,ts,observed,app,category,kind,title,payload) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    "live." + app_id,
                    external,
                    ts,
                    time.time(),
                    app["name"],
                    app["category"],
                    kind,
                    redact(title),
                    encoded,
                ),
            ).rowcount
    return total


class MacObserver:
    def __init__(self):
        self.actions = queue.Queue(maxsize=256)
        self.loop = None
        self.tap = None
        self.stopping = False
        self.input_status = "not_started"
        self._thread = None
        self._last_scroll = 0
        self.allowed_pid = None

    @staticmethod
    def permissions():
        if sys.platform != "darwin":
            return {"accessibility": False, "platform": "unsupported"}
        try:
            from ApplicationServices import AXIsProcessTrusted

            return {"accessibility": bool(AXIsProcessTrusted()), "platform": "macos"}
        except ImportError:
            return {"accessibility": False, "platform": "missing_dependencies"}

    def poll(self, settings):
        from AppKit import NSWorkspace
        from ApplicationServices import (
            AXUIElementCopyAttributeValue,
            AXUIElementCreateApplication,
            AXUIElementSetMessagingTimeout,
        )
        from CoreFoundation import CFHash

        self.allowed_pid = None
        front = NSWorkspace.sharedWorkspace().frontmostApplication()
        if front is None:
            return {}
        pid, name, bundle = (
            int(front.processIdentifier()),
            str(front.localizedName()),
            str(front.bundleIdentifier() or ""),
        )
        app = match_app(name, {"bundle_id": bundle})
        full = app is not None and full_enabled(settings, app["id"])
        # Only inspect document metadata outside a full-mode app when tracing enabled WeChat files.
        if not full and not settings.get("wechat", {}).get("enabled"):
            return {"ts": time.time(), "pid": pid, "app": name, "bundle_id": bundle}
        if not self.permissions()["accessibility"]:
            return {}
        root = AXUIElementCreateApplication(pid)
        AXUIElementSetMessagingTimeout(root, 0.15)

        def attr(element, key):
            if element is None:
                return None
            err, value = AXUIElementCopyAttributeValue(element, key, None)
            return value if not err else None

        window = attr(root, "AXFocusedWindow")
        snap = {
            "ts": time.time(),
            "pid": pid,
            "app": name,
            "bundle_id": bundle,
            "document": attr(window, "AXDocument") or "",
        }
        if not full:
            return snap
        focused = attr(root, "AXFocusedUIElement")
        role = attr(focused, "AXRole")
        subrole = attr(focused, "AXSubrole")
        secure = subrole == "AXSecureTextField" or bool(attr(focused, "AXProtectedContent"))
        snap["secure"] = secure
        if secure:
            return snap
        self.allowed_pid = pid
        snap["window"] = str(attr(window, "AXTitle") or "")[:500]
        if role in ("AXTextField", "AXTextArea", "AXComboBox"):
            draft = attr(focused, "AXValue")
            marked = attr(focused, "AXMarkedTextRange")
            if isinstance(draft, str) and marked is None and "\u200b" not in draft:
                snap["draft"] = draft[:MAX_TEXT]
                snap["field"] = str(CFHash(focused))
        nodes, lines, seen, count, size = [window] if window else [], [], set(), 0, 0
        deadline = time.monotonic() + 0.65
        while nodes and count < MAX_NODES and size < MAX_TEXT and time.monotonic() < deadline:
            node = nodes.pop()
            identity = CFHash(node)
            if identity in seen:
                continue
            seen.add(identity)
            count += 1
            if attr(node, "AXSubrole") == "AXSecureTextField" or attr(node, "AXProtectedContent"):
                continue
            node_role = attr(node, "AXRole")
            # Input is handled separately and only on changes; never mix drafts with chat history.
            if node_role in ("AXTextField", "AXTextArea", "AXComboBox"):
                continue
            for key in ("AXValue", "AXTitle", "AXDescription"):
                value = attr(node, key)
                if isinstance(value, str) and value.strip():
                    value = value.strip()[:2000]
                    if not lines or lines[-1] != value:
                        lines.append(value)
                        size += len(value)
            children = attr(node, "AXChildren") or []
            nodes.extend(reversed(list(children)[: MAX_NODES - count]))
        snap["text"] = "\n".join(lines)[:MAX_TEXT]
        snap["truncated"] = bool(nodes) or size > MAX_TEXT
        # The user may have switched apps during traversal. Discard mismatched snapshots.
        current = NSWorkspace.sharedWorkspace().frontmostApplication()
        return snap if current and int(current.processIdentifier()) == pid else {}

    def start_actions(self):
        if self._thread and self._thread.is_alive():
            return
        self.stopping = False
        self._thread = threading.Thread(target=self._run_actions, daemon=True, name="app-actions")
        self._thread.start()

    def _run_actions(self):
        import Quartz as Q

        kinds = {
            Q.kCGEventLeftMouseDown: "点击",
            Q.kCGEventRightMouseDown: "右键点击",
            Q.kCGEventScrollWheel: "滚动",
            Q.kCGEventKeyDown: "按键",
        }
        shortcuts = {
            0: "A",
            1: "S",
            6: "Z",
            7: "X",
            8: "C",
            9: "V",
            12: "Q",
            13: "W",
            31: "O",
            45: "N",
        }
        specials = {
            36: "Enter",
            48: "Tab",
            53: "Escape",
            51: "Backspace",
            123: "Left",
            124: "Right",
            125: "Down",
            126: "Up",
        }

        def callback(proxy, kind, event, context):
            if self.stopping or kind not in kinds:
                return event
            try:
                # No AX calls, text extraction, or database work on macOS's input-delivery thread.
                pid = int(Q.CGEventGetIntegerValueField(event, Q.kCGEventTargetUnixProcessID))
                if not pid or pid != self.allowed_pid:
                    return event
                action = kinds[kind]
                if kind == Q.kCGEventKeyDown:
                    code = int(Q.CGEventGetIntegerValueField(event, Q.kCGKeyboardEventKeycode))
                    flags = Q.CGEventGetFlags(event)
                    mods = [
                        label
                        for mask, label in (
                            (Q.kCGEventFlagMaskCommand, "⌘"),
                            (Q.kCGEventFlagMaskControl, "Ctrl"),
                            (Q.kCGEventFlagMaskAlternate, "⌥"),
                        )
                        if flags & mask
                    ]
                    key = shortcuts.get(code) if mods else specials.get(code)
                    if not key:
                        return event
                    action = "+".join([*mods, key])
                if kind == Q.kCGEventScrollWheel:
                    if time.monotonic() - self._last_scroll < 1:
                        return event
                    self._last_scroll = time.monotonic()
                self.actions.put_nowait({"pid": pid, "ts": time.time(), "action": action})
            except queue.Full:
                pass
            return event

        self._callback = callback
        try:
            mask = sum(1 << kind for kind in kinds)
            self.tap = Q.CGEventTapCreate(
                Q.kCGAnnotatedSessionEventTap,
                Q.kCGHeadInsertEventTap,
                Q.kCGEventTapOptionListenOnly,
                mask,
                callback,
                None,
            )
            if self.tap is None:
                self.input_status = "permission_required"
                return
            src = Q.CFMachPortCreateRunLoopSource(None, self.tap, 0)
            self.loop = Q.CFRunLoopGetCurrent()
            Q.CFRunLoopAddSource(self.loop, src, Q.kCFRunLoopDefaultMode)
            self.input_status = "listening"
            Q.CGEventTapEnable(self.tap, True)
            if not self.stopping:
                Q.CFRunLoopRun()
        except Exception:
            self.input_status = "unavailable"
        finally:
            if self.tap:
                Q.CFMachPortInvalidate(self.tap)
            self.tap = None
            self.loop = None

    def stop_actions(self):
        self.stopping = True
        self.allowed_pid = None
        if self.loop:
            import Quartz as Q

            Q.CFRunLoopStop(self.loop)
        if self._thread:
            self._thread.join(timeout=0.5)
        while not self.actions.empty():
            try:
                self.actions.get_nowait()
            except queue.Empty:
                break
        self.input_status = "not_started"


class LiveMonitor:
    def __init__(self, store, observer=None):
        self.store = store
        self.observer = observer or MacObserver()
        self.previous = {}
        self.stop_event = threading.Event()
        self.status = {"running": False, "last_sample": None, "error": None}
        self.thread = None

    def tick(self):
        with self.store.connect() as db:
            settings = monitoring_settings(db)
            roots = []
            row = db.execute("SELECT paths FROM sources WHERE id='wechat.files'").fetchone()
            if row:
                roots = json.loads(row[0])
        active = any(full_enabled(settings, app_id) for app_id in FULL_APPS)
        permissions = self.observer.permissions()
        self.status.update(permissions)
        if permissions["platform"] != "macos":
            return
        if active and permissions["accessibility"]:
            self.observer.start_actions()
        else:
            self.observer.stop_actions()
        snap = self.observer.poll(settings)
        if not snap:
            self.previous.clear()
            return
        events = snapshot_events(snap, self.previous, settings, roots)
        app = match_app(snap.get("app"), {"bundle_id": snap.get("bundle_id")})
        while not self.observer.actions.empty():
            action = self.observer.actions.get_nowait()
            if (
                app
                and full_enabled(settings, app["id"])
                and not snap.get("secure")
                and action["pid"] == snap.get("pid")
                and 0 <= snap["ts"] - action["ts"] < 3
                and action["ts"] >= settings[app["id"]]["consented"]
            ):
                events.append(
                    (
                        app["id"],
                        "app_action",
                        action["action"],
                        {
                            "action": action["action"],
                            "window": snap.get("window", ""),
                            "action_at": action["ts"],
                            "meaning": "观察到的按键或鼠标操作；Enter 不等于消息发送成功。",
                        },
                    )
                )
        self.status["foreground_app"] = app["id"] if app else None
        self.status["readable_text"] = bool(snap.get("text"))
        save_events(self.store, events, snap["ts"], settings)
        self.status.update(last_sample=snap["ts"], error=None, input=self.observer.input_status)

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self.run, daemon=True, name="app-monitor")
        self.thread.start()

    def run(self):
        import fcntl

        with self.store.path.with_suffix(".live.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self.status["error"] = "another_process"
                return
            self.status["running"] = True
            collector = threading.Thread(
                target=self.collect_loop, daemon=True, name="app-source-refresh"
            )
            collector.start()
            try:
                while not self.stop_event.is_set():
                    try:
                        self.tick()
                    except Exception:
                        # Do not send captured content or native exception data into logs/UI.
                        self.status["error"] = "capture_unavailable"
                    self.stop_event.wait(1)
            finally:
                self.observer.stop_actions()
                self.status["running"] = False

    def collect_loop(self):
        from .collect import collect

        while not self.stop_event.is_set():
            try:
                result = collect(self.store)
                self.status["collection_error"] = bool(result.get("errors"))
                self.status["last_collection"] = time.time()
            except Exception:
                self.status["collection_error"] = True
            self.stop_event.wait(15)

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)


_monitors = {}


def start_monitor(store):
    key = str(store.path.resolve())
    if key not in _monitors:
        _monitors[key] = LiveMonitor(store)
        _monitors[key].start()
    return _monitors[key]


def monitor_status(store):
    monitor = _monitors.get(str(store.path.resolve()))
    return {**MacObserver.permissions(), **(monitor.status if monitor else {"running": False})}
