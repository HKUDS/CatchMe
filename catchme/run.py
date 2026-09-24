#!/usr/bin/env python3
"""CatchMe CLI — minimal, elegant terminal interface."""

from __future__ import annotations

import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# ── ANSI palette ──

RST = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
WHITE = "\033[97m"
GRAY = "\033[90m"
CYAN = "\033[38;5;74m"
GREEN = "\033[38;5;114m"
YELLOW = "\033[38;5;179m"
RED = "\033[38;5;167m"
PURPLE = "\033[38;5;141m"

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _p(msg: str) -> None:
    """Print and flush immediately."""
    print(msg, flush=True)


# ── init ──

_DEFAULT_MODELS: dict[str, str] = {
    "openrouter": "google/gemini-3-flash-preview",
    "requesty": "google/gemini-3-flash-preview",
    "aihubmix": "google/gemini-3-flash-preview",
    "siliconflow": "Qwen/Qwen3-8B",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "deepseek": "deepseek-chat",
    "gemini": "gemini-2.5-flash",
    "groq": "llama-3.3-70b-versatile",
    "mistral": "mistral-small-latest",
    "moonshot": "moonshot-v1-8k",
    "minimax": "MiniMax-Text-01",
    "zhipu": "glm-4-flash",
    "dashscope": "qwen-plus",
    "volcengine": "doubao-1.5-pro-32k",
    "volcengine_coding_plan": "doubao-1.5-pro-32k",
    "byteplus": "doubao-1.5-pro-32k",
    "byteplus_coding_plan": "doubao-1.5-pro-32k",
    "ollama": "llama3",
    "vllm": "llama3",
    "lmstudio": "llama3",
}

_LOCAL_PROVIDERS = {"ollama", "vllm", "lmstudio"}


def _input(prompt: str) -> str:
    """Read a line from stdin with prompt, stripping whitespace."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        _p(f"\n  {DIM}cancelled.{RST}\n")
        sys.exit(0)


def cmd_init() -> None:
    """Interactive configuration wizard — set up LLM provider and API key."""
    from catchme.config import get_default_config
    from catchme.services.providers import PROVIDERS

    cfg_obj = get_default_config()
    config_path = cfg_obj.config_path

    _p("")
    _p(f"  {PURPLE}{BOLD}CatchMe{RST}  {DIM}·{RST}  {CYAN}init{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p(f"  {DIM}config →{RST} {config_path}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p("")

    # ── existing config ──
    existing: dict = {}
    if config_path.exists():
        import json

        try:
            existing = json.loads(config_path.read_text("utf-8"))
        except Exception:
            pass
        if existing.get("llm", {}).get("api_key"):
            _p(f"  {YELLOW}config already exists.{RST}")
            ans = _input("  overwrite? [y/N] ")
            if ans.lower() not in ("y", "yes"):
                _p(f"  {DIM}keeping current config.{RST}\n")
                return

    # ── provider selection ──
    _p(f"  {BOLD}Select LLM provider:{RST}\n")
    groups = [
        (
            "Gateways",
            [p for p in PROVIDERS if p[0] in ("openrouter", "requesty", "aihubmix", "siliconflow")],
        ),
        (
            "Cloud",
            [
                p
                for p in PROVIDERS
                if p[0]
                not in (
                    "openrouter",
                    "requesty",
                    "aihubmix",
                    "siliconflow",
                    "ollama",
                    "vllm",
                    "lmstudio",
                )
            ],
        ),
        ("Local", [p for p in PROVIDERS if p[0] in ("ollama", "vllm", "lmstudio")]),
    ]

    flat: list[tuple[str, str, str, str]] = []
    for group_name, members in groups:
        _p(f"  {DIM}── {group_name} ──{RST}")
        for prov in members:
            idx = len(flat) + 1
            _p(f"    {WHITE}{idx:>2}{RST}  {prov[1]}")
            flat.append(prov)
    _p("")

    while True:
        choice = _input(f"  enter number [1-{len(flat)}]: ")
        try:
            n = int(choice)
            if 1 <= n <= len(flat):
                break
        except ValueError:
            pass
        _p(f"  {RED}invalid choice{RST}")

    provider_name, provider_display, api_url, key_url = flat[n - 1]
    _p(f"  {GREEN}✓{RST} {provider_display}\n")

    # ── API key ──
    api_key = ""
    if provider_name not in _LOCAL_PROVIDERS:
        if key_url:
            _p(f"  {DIM}get your key →{RST} {CYAN}{key_url}{RST}")
        api_key = _input("  API key: ")
        if not api_key:
            _p(f"  {YELLOW}⚠ no API key — you can add it later in config.json{RST}")
        _p("")

    # ── model ──
    default_model = _DEFAULT_MODELS.get(provider_name, "")
    model_prompt = f"  model [{default_model}]: " if default_model else "  model: "
    model = _input(model_prompt) or default_model
    _p(f"  {GREEN}✓{RST} {model}\n")

    # ── summary language ──
    lang = _input(f"  summary language [{DIM}en{RST}]: ") or "en"

    # ── write config ──
    import json

    _EXAMPLE = Path(__file__).resolve().parent / "services" / "config.example.json"
    config: dict = json.loads(_EXAMPLE.read_text("utf-8"))

    config["llm"]["provider"] = provider_name
    config["llm"]["api_url"] = api_url
    config["llm"]["model"] = model
    config["llm"]["api_key"] = api_key if api_key else ""
    config["summarize"]["language"] = lang

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=4, ensure_ascii=False) + "\n", "utf-8")

    _p("")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p(f"  {GREEN}✓ config saved{RST}")
    _p(f"  {DIM}path →{RST}  {CYAN}{config_path}{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p(f"  {DIM}next:{RST}  catchme awake")
    _p("")


# ── awake (backend: recorders only) ──

_SHOW_KINDS = {"window", "idle", "clipboard", "notification"}
_APP_ICONS = {
    "safari": "🧭",
    "chrome": "🌐",
    "firefox": "🦊",
    "arc": "🌈",
    "cursor": "⌨",
    "code": "⌨",
    "xcode": "🔨",
    "terminal": "▶",
    "iterm": "▶",
    "warp": "▶",
    "wezterm": "▶",
    "slack": "💬",
    "discord": "💬",
    "telegram": "💬",
    "微信": "💬",
    "企业微信": "💼",
    "飞书": "💼",
    "钉钉": "💼",
    "finder": "📁",
    "访达": "📁",
    "notes": "📝",
    "notion": "📝",
    "obsidian": "📝",
    "music": "🎵",
    "spotify": "🎵",
    "mail": "✉️",
    "outlook": "✉️",
    "preview": "📄",
    "figma": "🎨",
    "sketch": "🎨",
}
_last_window: str = ""


def _app_icon(app: str) -> str:
    low = app.lower()
    for key, icon in _APP_ICONS.items():
        if key in low:
            return icon
    return "◇"


def _log_event(e) -> None:
    """Print only significant events with clean formatting."""
    global _last_window

    if e.kind not in _SHOW_KINDS:
        return

    ts = datetime.fromtimestamp(e.timestamp).strftime("%H:%M:%S")
    d = e.data

    if e.kind == "window":
        app = d.get("app", "?")
        title = d.get("title", "")
        sig = f"{app}|{title}"
        if sig == _last_window:
            return
        _last_window = sig
        icon = _app_icon(app)
        title_short = title[:65] + "…" if len(title) > 65 else title
        _p(f"  {GRAY}{ts}{RST}  {icon}  {WHITE}{app}{RST} {DIM}— {title_short}{RST}")

    elif e.kind == "idle":
        status = d.get("status", "?")
        if status == "idle":
            dur = d.get("seconds", d.get("duration", 0))
            if dur > 10:
                mins = int(dur // 60)
                secs = int(dur % 60)
                dur_s = f"{mins}m{secs:02d}s" if mins else f"{secs}s"
                _p(f"  {GRAY}{ts}{RST}  💤 {YELLOW}idle {dur_s}{RST}")
        elif status == "active":
            _p(f"  {GRAY}{ts}{RST}  ⚡ {GREEN}active{RST}")

    elif e.kind == "clipboard":
        content = d.get("content", "")[:50]
        if content:
            _p(
                f"  {GRAY}{ts}{RST}  📋 {DIM}{content}{'…' if len(d.get('content', '')) > 50 else ''}{RST}"
            )

    elif e.kind == "notification":
        name = d.get("name", "?")
        _p(f"  {GRAY}{ts}{RST}  🔔 {DIM}{name}{RST}")


def cmd_awake() -> None:
    """Start recorders (backend). Ctrl+C to stop."""
    import logging

    logging.basicConfig(level=logging.WARNING, format="  %(levelname)s  %(message)s")
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    from catchme import CatchMe

    mem = CatchMe()
    data_path = str(mem.config.root)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    _p("")
    _p(f"  {PURPLE}{BOLD}CatchMe{RST}  {DIM}·{RST}  {GREEN}▶ awake{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p(f"  {DIM}data{RST}   {DIM}{data_path}{RST}")
    _p(f"  {DIM}time{RST}   {DIM}{now}{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p(f"  {DIM}Ctrl+C to stop{RST}")
    _p("")

    mem.on_event = _log_event
    mem.start()
    start_time = time.time()

    stop = threading.Event()

    def _handle_signal(sig, frame):
        stop.set()

    signal.signal(signal.SIGINT, _handle_signal)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, _handle_signal)
    else:
        try:
            signal.signal(signal.SIGBREAK, _handle_signal)
        except (AttributeError, OSError):
            pass

    try:
        stop.wait()
    except KeyboardInterrupt:
        pass

    try:
        count = mem.store.count()
    except Exception:
        count = 0

    def _force_exit():
        time.sleep(5)
        import os

        os._exit(0)

    watchdog = threading.Thread(target=_force_exit, daemon=True)
    watchdog.start()

    sys.stdout.write(f"\n  {DIM}flushing…{RST}")
    sys.stdout.flush()
    mem.stop()
    sys.stdout.write(f"\r  {DIM}flushing… done.{RST}\n")
    sys.stdout.flush()

    elapsed = time.time() - start_time
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)
    dur_s = f"{mins}m{secs:02d}s" if mins else f"{secs}s"
    _p("")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p(f"  {PURPLE}{BOLD}CatchMe{RST}  {DIM}·{RST}  {RED}■ stopped{RST}")
    _p(f"  {DIM}duration{RST}  {dur_s}  {DIM}·{RST}  {DIM}events{RST}  {count}")
    _p(f"  {DIM}data →{RST}  {CYAN}{data_path}{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p("")


# ── web (frontend server) ──


def cmd_web(port: int | None = None, host: str | None = None) -> None:
    """Start the web viewer (frontend). Ctrl+C to stop."""
    import logging

    logging.basicConfig(level=logging.WARNING, format="  %(levelname)s  %(message)s")

    from catchme.services import load_config

    cfg = load_config()
    web_cfg = cfg.get("web", {})
    final_host = host or web_cfg.get("host", "127.0.0.1")
    final_port = port or web_cfg.get("port", 8765)

    try:
        import flask  # noqa: F401
    except ImportError:
        _p(f"  {RED}flask not installed.{RST} Run {CYAN}catchme init{RST} first.")
        sys.exit(1)

    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex((final_host, final_port)) == 0:
            _p(f"\n  {RED}port {final_port} is already in use.{RST}")
            _p(f"  {DIM}try:{RST}  catchme web -p {final_port + 1}")
            if sys.platform == "win32":
                _p(
                    f"  {DIM} or:{RST}  netstat -ano | findstr :{final_port}  {DIM}to find the process{RST}\n"
                )
            else:
                _p(f"  {DIM} or:{RST}  lsof -i :{final_port}  {DIM}to find the process{RST}\n")
            sys.exit(1)

    _p("")
    _p(f"  {PURPLE}{BOLD}CatchMe{RST}  {DIM}·{RST}  {CYAN}▶ web{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p(f"  {DIM}url{RST}    {CYAN}http://{final_host}:{final_port}{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p(f"  {DIM}Ctrl+C to stop{RST}")
    _p("")

    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    from catchme.web import app

    app.run(host=final_host, port=final_port, debug=False, use_reloader=False)


# ── ask (CLI retrieval) ──


def cmd_ask(query: str) -> None:
    """Run a retrieval query and stream results to terminal."""
    import logging

    logging.basicConfig(level=logging.WARNING, format="  %(levelname)s  %(message)s")

    from catchme.pipelines.retrieve import retrieve

    _p("")
    _p(f"  {PURPLE}{BOLD}CatchMe{RST}  {DIM}·{RST}  {CYAN}ask{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p(f"  {DIM}query{RST}  {WHITE}{query}{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p("")

    for step in retrieve(query):
        stype = step.get("type", "")

        if stype == "time_filter":
            dates = step.get("dates") or []
            hours = []
            if step.get("start_hour") is not None:
                hours.append(f"from {step['start_hour']}:00")
            if step.get("end_hour") is not None:
                hours.append(f"to {step['end_hour']}:00")
            scope = ", ".join(dates) if dates else "all dates"
            if hours:
                scope += f"  ({' '.join(hours)})"
            _p(f"  {GRAY}scope{RST}  {scope}")

        elif stype == "browse":
            level = step.get("level", "node")
            selected = step.get("selected", [])
            names = [s.get("title", s.get("node_id", "?")) for s in selected]
            if names:
                _p(f"  {GRAY}browse{RST} {DIM}[{level}]{RST}  {YELLOW}{'  '.join(names)}{RST}")
            else:
                _p(f"  {GRAY}browse{RST} {DIM}[{level}]{RST}  {DIM}none selected{RST}")

        elif stype == "read":
            for node in step.get("nodes", []):
                mark = f"{GREEN}+{RST}" if node.get("useful") else f"{DIM}-{RST}"
                title = node.get("title", node.get("node_id", ""))
                _p(f"  {GRAY}read{RST}   {mark} {title}")

        elif stype == "inspect":
            mark = f"{GREEN}+{RST}" if step.get("useful") else f"{DIM}-{RST}"
            title = step.get("title", "screenshot")
            _p(f"  {GRAY}inspect{RST} {mark} {title}")

        elif stype == "answer":
            _p(f"  {DIM}{'─' * 42}{RST}")
            _p("")
            _p(step.get("content", ""))
            _p("")

        elif stype == "error":
            _p(f"  {RED}error:{RST} {step.get('message', 'unknown error')}")


# ── mcp (MCP stdio server) ──


def cmd_mcp() -> None:
    """Start CatchMe as an MCP stdio server for Claude Desktop, Cursor, Hermes, etc."""
    import logging

    logging.basicConfig(level=logging.WARNING, format="  %(levelname)s  %(message)s")

    try:
        from catchme.mcp_server import serve
    except ImportError as exc:
        _p(f"  {RED}MCP server error:{RST} {exc}")
        _p(f"  {DIM}Install the MCP extra:{RST}  {CYAN}pip install 'catchme[mcp]'{RST}")
        sys.exit(1)

    serve()


# ── cost ──


def cmd_cost() -> None:
    """Show LLM token usage: last 10 min, today, and all-time."""
    from catchme.services.llm import load_usage_from_disk

    data = load_usage_from_disk()
    history = data.get("history", [])

    now = time.time()
    ten_min_ago = now - 600
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

    p_10m, c_10m = 0, 0
    p_day, c_day = 0, 0
    p_all, c_all = 0, 0
    for r in history:
        ts, p, c = r["ts"], r["prompt"], r["completion"]
        p_all += p
        c_all += c
        if ts >= today_start:
            p_day += p
            c_day += c
        if ts >= ten_min_ago:
            p_10m += p
            c_10m += c

    def _fmt(prompt: int, comp: int) -> str:
        total = prompt + comp
        if total == 0:
            return f"{DIM}0{RST}"
        return f"{WHITE}{total:,}{RST}  {DIM}({prompt:,} in / {comp:,} out){RST}"

    _p("")
    _p(f"  {PURPLE}{BOLD}CatchMe{RST}  {DIM}·{RST}  {CYAN}cost{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p(f"  {GRAY}last 10 min{RST}  {_fmt(p_10m, c_10m)}")
    _p(f"  {GRAY}today      {RST}  {_fmt(p_day, c_day)}")
    _p(f"  {GRAY}all time   {RST}  {_fmt(p_all, c_all)}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p("")


# ── disk ──


def cmd_disk() -> None:
    """Show disk usage and event count."""
    import os as _os

    from catchme.config import Config
    from catchme.utils import dir_size_mb, file_size_mb

    cfg = Config()

    db_mb = file_size_mb(str(cfg.db_path))
    blobs_mb = dir_size_mb(str(cfg.blob_dir))
    trees_dir = str(cfg.root / "trees")
    trees_mb = dir_size_mb(trees_dir)
    total_mb = db_mb + blobs_mb + trees_mb

    blobs_breakdown: dict[str, float] = {}
    blobs_dir = str(cfg.blob_dir)
    if _os.path.isdir(blobs_dir):
        for entry in sorted(_os.listdir(blobs_dir)):
            sub = _os.path.join(blobs_dir, entry)
            if _os.path.isdir(sub):
                blobs_breakdown[entry] = dir_size_mb(sub)

    events_total = 0
    try:
        from catchme.store import Store

        store = Store(cfg.db_path)
        events_total = store.count()
        store.close()
    except Exception:
        pass

    _p("")
    _p(f"  {PURPLE}{BOLD}CatchMe{RST}  {DIM}·{RST}  {CYAN}disk{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p(f"  {GRAY}Total        {RST}  {WHITE}{BOLD}{total_mb:,.1f} MB{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p(f"  {GRAY}Database     {RST}  {WHITE}{db_mb:,.1f} MB{RST}")
    _p(f"  {GRAY}Blobs        {RST}  {WHITE}{blobs_mb:,.1f} MB{RST}")
    _p(f"  {GRAY}Trees        {RST}  {WHITE}{trees_mb:,.2f} MB{RST}")
    if blobs_breakdown:
        _p(f"  {DIM}{'─' * 42}{RST}")
        for date, mb in blobs_breakdown.items():
            _p(f"    {GRAY}{date}{RST}  {DIM}{mb:,.1f} MB{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p(f"  {GRAY}Events       {RST}  {WHITE}{events_total:,}{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p("")


# ── ram ──


def cmd_ram() -> None:
    """Show RAM usage of catchme processes."""
    import os as _os

    my_pid = _os.getpid()
    procs: list[dict] = []
    try:
        import psutil

        for proc in psutil.process_iter(["pid", "name", "cmdline", "memory_info"]):
            try:
                info = proc.info
                if info["pid"] == my_pid:
                    continue
                cmdline = " ".join(info["cmdline"] or [])
                name = info["name"] or ""
                if "catchme" not in cmdline and "catchme" not in name:
                    continue
                label = (
                    "web"
                    if "web" in cmdline
                    else (
                        "awake" if "awake" in cmdline else cmdline.split()[-1] if cmdline else name
                    )
                )
                rss_mb = round(info["memory_info"].rss / (1024 * 1024), 1)
                procs.append({"pid": info["pid"], "label": label, "rss_mb": rss_mb})
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass

    total_rss = sum(p["rss_mb"] for p in procs) if procs else 0.0

    _p("")
    _p(f"  {PURPLE}{BOLD}CatchMe{RST}  {DIM}·{RST}  {CYAN}ram{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    if procs:
        _p(f"  {GRAY}Total        {RST}  {WHITE}{BOLD}{total_rss:.1f} MB{RST}")
        _p(f"  {DIM}{'─' * 42}{RST}")
        for p in procs:
            _p(
                f"  {GRAY}{p['label']:<12}{RST}  {WHITE}{p['rss_mb']:.1f} MB{RST}  {DIM}pid {p['pid']}{RST}"
            )
    else:
        _p(f"  {DIM}no catchme processes running{RST}")
    _p(f"  {DIM}{'─' * 42}{RST}")
    _p("")


# ── help ──


def _print_help() -> None:
    _p(f"""
  {PURPLE}{BOLD}CatchMe{RST}  {DIM}— personal digital footprint recorder{RST}

  {BOLD}Commands{RST}
    catchme init               Set up LLM provider & API key
    catchme awake              Start recording (backend)
    catchme web                Start web viewer (frontend)
    catchme web -p 9000        Start web viewer on custom port
    catchme ask -- <question>  Ask about your activity history
    catchme mcp                Start MCP stdio server (Claude Desktop, Cursor, …)
    catchme cost               Show LLM token usage
    catchme disk               Show disk usage and event count
    catchme ram                Show RAM usage of catchme processes
    catchme help               Show this message

  {BOLD}Shortcuts{RST}
    Ctrl+C                     Graceful shutdown

  {BOLD}Config{RST}
    Web port is read from {DIM}catchme/services/config.json → web.port{RST}
    Override with {CYAN}--port{RST} / {CYAN}-p{RST} flag.

  {BOLD}MCP Setup (Claude Desktop){RST}
    Add to claude_desktop_config.json:
    {{"mcpServers": {{"catchme": {{"command": "catchme", "args": ["mcp"]}}}}}}
""")


# ── entry point ──


def main() -> None:
    """CLI entry point. Routes subcommands."""
    args = sys.argv[1:]

    if not args:
        _print_help()
        return

    cmd = args[0]

    if cmd == "init":
        cmd_init()

    elif cmd == "awake":
        cmd_awake()

    elif cmd == "web":
        port = None
        host = None
        for i, a in enumerate(args):
            if a in ("--port", "-p") and i + 1 < len(args):
                port = int(args[i + 1])
            elif a in ("--host",) and i + 1 < len(args):
                host = args[i + 1]
        cmd_web(port=port, host=host)

    elif cmd == "ask":
        rest = args[1:]
        if rest and rest[0] == "--":
            rest = rest[1:]
        if not rest:
            _p(f"  {RED}query required.{RST}  Usage: catchme ask -- <question>")
            sys.exit(1)
        cmd_ask(query=" ".join(rest))

    elif cmd == "mcp":
        cmd_mcp()

    elif cmd == "cost":
        cmd_cost()

    elif cmd == "disk":
        cmd_disk()

    elif cmd == "ram":
        cmd_ram()

    elif cmd in ("-h", "--help", "help"):
        _print_help()

    else:
        _p(f"  {RED}unknown command:{RST} {cmd}")
        _p(f"  {DIM}try: catchme help{RST}")
        sys.exit(1)


if __name__ == "__main__":
    main()
