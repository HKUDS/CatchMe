"""CatchMe web viewer — serves the dashboard and all API endpoints."""

from __future__ import annotations

import json
import os

from flask import Flask, Response, jsonify, request, send_from_directory

from .config import Config
from .store import Event, Store

# ── Lazy singletons (no side effects on import) ──

_config: Config | None = None
_store: Store | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store(get_config().db_path)
    return _store


app = Flask(__name__, static_folder="static", static_url_path="")


def _query_events(
    kind: str | None = None,
    since: float | None = None,
    until: float | None = None,
    limit: int = 500,
) -> list[Event]:
    return get_store().query_raw(kind=kind, since=since, until=until, limit=limit)


def _bounded_limit(limit: int, maximum: int) -> int:
    """Keep API limits within their advertised bounds, including negative inputs."""
    return min(max(limit, 0), maximum)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "")
    if not q:
        return jsonify([])
    kind = request.args.get("kind")
    limit = request.args.get("limit", 100, type=int)
    events = get_store().search(q, kind=kind or None, limit=_bounded_limit(limit, 500))
    return jsonify([_serialize(e) for e in events])


# ── Events API ──


@app.route("/api/events")
def api_events():
    kind = request.args.get("kind")
    since = request.args.get("since", type=float)
    until = request.args.get("until", type=float)
    limit = request.args.get("limit", 200, type=int)
    events = _query_events(
        kind=kind or None, since=since, until=until, limit=_bounded_limit(limit, 2000)
    )
    return jsonify([_serialize(e) for e in events])


@app.route("/api/stats")
def api_stats():
    return jsonify(get_store().stats())


@app.route("/api/timeline")
def api_timeline():
    since = request.args.get("since", type=float)
    until = request.args.get("until", type=float)
    limit = request.args.get("limit", 2000, type=int)
    events = _query_events(since=since, until=until, limit=_bounded_limit(limit, 5000))
    grouped: dict[str, list] = {}
    for e in events:
        grouped.setdefault(e.kind, []).append(_serialize(e))
    return jsonify({"since": since, "until": until, "tracks": grouped})


@app.route("/api/filtered")
def api_filtered():
    from .pipelines.filter import build_filtered, load_filter_config

    since = request.args.get("since", type=float)
    until = request.args.get("until", type=float)
    return jsonify(build_filtered(get_store(), since=since, until=until, cfg=load_filter_config()))


@app.route("/api/tree")
def api_tree():
    import time as _t

    from .pipelines.tree import build_tree, load_tree, merge_summaries, save_tree

    since = request.args.get("since", type=float)
    until = request.args.get("until", type=float)
    mode = request.args.get("mode", "time")
    use_cache = request.args.get("cache", "0") == "1"

    if use_cache and since:
        date = _t.strftime("%Y-%m-%d", _t.localtime(since))
        cached = load_tree(date, mode)
        if cached:
            return jsonify(cached)

    old = None
    if since:
        date = _t.strftime("%Y-%m-%d", _t.localtime(since))
        old = load_tree(date, mode)

    store = get_store()
    result = build_tree(store, since=since, until=until, mode=mode)
    if result and result.get("tree") and since:
        if old and old.get("tree"):
            merge_summaries(old["tree"], result["tree"])
        save_tree(result)

    return jsonify(result)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    from .pipelines.retrieve import retrieve

    body = request.get_json(silent=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query required"}), 400

    def generate():
        for step in retrieve(query):
            yield f"data: {json.dumps(step, ensure_ascii=False)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/config/summarize")
def api_config_summarize_get():
    from .services import load_config

    cfg = load_config()
    return jsonify(cfg.get("summarize", {}))


@app.route("/api/config/summarize", methods=["POST"])
def api_config_summarize_set():
    from .services import _get_config_path, load_config, save_config

    body = request.get_json(silent=True) or {}
    cfg_path = _get_config_path()

    raw: dict = {}
    if cfg_path.exists():
        raw = json.loads(cfg_path.read_text("utf-8"))
    scfg = raw.setdefault("summarize", {})
    for key in (
        "language",
        "temperature",
        "max_tokens_l0",
        "max_tokens_l1",
        "max_tokens_l2",
        "max_tokens_l3",
    ):
        if key in body:
            scfg[key] = body[key]
    save_config(raw)
    load_config(reload=True)
    return jsonify(scfg)


@app.route("/api/config/llm")
def api_config_llm_get():
    from .services import load_config

    cfg = load_config()
    llm = dict(cfg.get("llm", {}))
    if llm.get("api_key"):
        llm["api_key"] = "****"
    return jsonify(llm)


@app.route("/api/config/llm", methods=["POST"])
def api_config_llm_set():
    from .services import _get_config_path, load_config, save_config

    body = request.get_json(silent=True) or {}
    cfg_path = _get_config_path()

    raw: dict = {}
    if cfg_path.exists():
        raw = json.loads(cfg_path.read_text("utf-8"))
    lcfg = raw.setdefault("llm", {})
    for key in ("provider", "api_key", "api_url", "model", "max_calls", "max_images_per_cluster"):
        if key in body:
            if key == "api_key" and body[key] == "****":
                continue
            lcfg[key] = body[key]
    save_config(raw)
    load_config(reload=True)
    return jsonify({"ok": True})


@app.route("/api/llm/status")
def api_llm_status():
    from .services.llm import LLM

    remaining = LLM.budget_remaining()
    return jsonify(
        {
            "count": LLM.call_count(),
            "remaining": remaining,
            "exhausted": remaining == 0,
        }
    )


@app.route("/api/events/summaries")
def api_summary_events():
    """SSE endpoint that tails the summary notification file."""
    import time as _t

    from .summary_queue import get_notification_path

    path = get_notification_path()

    def stream():
        offset = 0
        try:
            if os.path.isfile(path):
                offset = os.path.getsize(path)
        except OSError:
            pass

        yield 'data: {"type":"connected"}\n\n'

        while True:
            _t.sleep(1.0)
            try:
                if not os.path.isfile(path):
                    continue
                size = os.path.getsize(path)
                if size <= offset:
                    if size < offset:
                        offset = 0
                    continue
                with open(path, encoding="utf-8") as f:
                    f.seek(offset)
                    new_data = f.read()
                    offset = f.tell()
                for line in new_data.strip().splitlines():
                    line = line.strip()
                    if line:
                        yield f"data: {line}\n\n"
            except GeneratorExit:
                return
            except OSError:
                continue

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/digest")
def api_digest():
    import time as _t

    from .pipelines.tree import load_tree

    date = request.args.get("date", _t.strftime("%Y-%m-%d"))
    mode = request.args.get("mode", "time")
    data = load_tree(date, mode)
    if not data or not data.get("tree"):
        return jsonify([])
    return jsonify(_flatten_summaries(data["tree"], depth=0))


def _flatten_summaries(node: dict, depth: int) -> list[dict]:
    result: list[dict] = []
    kind = node.get("kind", "")
    if kind != "day" and node.get("summary"):
        ctx = node.get("context", {})
        entry = {
            "kind": kind,
            "node_id": node.get("node_id", ""),
            "title": node.get("title", ""),
            "summary": node["summary"],
            "start": node.get("start", 0),
            "end": node.get("end", 0),
            "depth": depth,
            "app": ctx.get("app", ""),
            "location": ctx.get("full_location", ctx.get("location", "")),
        }
        if node.get("evidence"):
            entry["evidence"] = node["evidence"]
        result.append(entry)
    for ch in node.get("children", []):
        child_depth = depth if kind == "day" else depth + 1
        result.extend(_flatten_summaries(ch, child_depth))
    return result


def _merged_llm_usage(LLM):
    """Combine on-disk usage (written by awake) with in-process usage (web-triggered summarize)."""
    from .services.llm import load_usage_from_disk

    disk = load_usage_from_disk()
    disk_history = disk.get("history", [])

    mem_history = [{"ts": r[0], "prompt": r[1], "completion": r[2]} for r in LLM.token_history()]

    disk_ts = {r["ts"] for r in disk_history}
    extra = [r for r in mem_history if r["ts"] not in disk_ts]
    all_history = disk_history + extra
    all_history.sort(key=lambda r: r["ts"])

    total_p = sum(r["prompt"] for r in all_history)
    total_c = sum(r["completion"] for r in all_history)

    return {
        "call_count": len(all_history),
        "budget_remaining": LLM.budget_remaining(),
        "tokens": {"prompt": total_p, "completion": total_c, "total": total_p + total_c},
        "token_history": all_history,
    }


_MONITOR_HIST_MAX = 50000
_MONITOR_HIST_INTERVAL = 30


def _monitor_hist_path():
    return get_config().monitor_history_path


def _load_monitor_history() -> list[dict]:
    try:
        p = _monitor_hist_path()
        if p.is_file():
            return json.loads(p.read_text("utf-8"))
    except Exception:
        pass
    return []


def _compact_monitor_history(hist: list[dict]) -> list[dict]:
    """Downsample points older than 48h to ~5 min intervals, keep recent data intact."""
    if not hist:
        return hist
    now = hist[-1]["ts"]
    cutoff = now - 48 * 3600
    recent = [p for p in hist if p["ts"] >= cutoff]
    old = [p for p in hist if p["ts"] < cutoff]
    if not old:
        return recent
    compacted: list[dict] = []
    last_ts = 0.0
    for p in old:
        if p["ts"] - last_ts >= 300:
            compacted.append(p)
            last_ts = p["ts"]
    return compacted + recent


def _append_monitor_snapshot(snap: dict) -> None:
    """Append a compact snapshot to the persistent history file."""
    hist = _load_monitor_history()
    if hist and snap["ts"] - hist[-1]["ts"] < _MONITOR_HIST_INTERVAL:
        return
    hist.append(snap)
    if len(hist) > _MONITOR_HIST_MAX:
        hist = _compact_monitor_history(hist)
        if len(hist) > _MONITOR_HIST_MAX:
            hist = hist[-_MONITOR_HIST_MAX:]
    try:
        p = _monitor_hist_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(hist, ensure_ascii=False) + "\n", "utf-8")
    except Exception:
        pass


@app.route("/api/monitor/history")
def api_monitor_history():
    return jsonify(_load_monitor_history())


@app.route("/api/monitor")
def api_monitor():
    import os as _os
    import resource
    import time as _t

    from .services.llm import LLM
    from .utils import dir_size_mb, file_size_mb

    cfg = get_config()
    store = get_store()

    db_mb = round(file_size_mb(str(cfg.db_path)), 2)
    blobs_dir = str(cfg.blob_dir)
    blobs_total = round(dir_size_mb(blobs_dir), 2)
    blobs_breakdown: dict[str, float] = {}
    if _os.path.isdir(blobs_dir):
        for entry in _os.listdir(blobs_dir):
            sub = _os.path.join(blobs_dir, entry)
            if _os.path.isdir(sub):
                blobs_breakdown[entry] = round(dir_size_mb(sub), 2)

    trees_dir = str(cfg.tree_dir)
    trees_mb = round(dir_size_mb(trees_dir), 2)

    import subprocess
    import sys

    def _catchme_processes():
        procs = []
        try:
            out = subprocess.check_output(["ps", "-eo", "pid,rss,comm"], text=True, timeout=3)
            for line in out.strip().split("\n")[1:]:
                parts = line.split(None, 2)
                if len(parts) < 3:
                    continue
                pid_s, rss_s, comm = parts
                if "catchme" in comm or "python" in comm.lower():
                    try:
                        cmdline = subprocess.check_output(
                            ["ps", "-p", pid_s, "-o", "args="], text=True, timeout=2
                        ).strip()
                    except Exception:
                        cmdline = comm
                    if "catchme" in cmdline:
                        label = (
                            "web"
                            if "web" in cmdline
                            else ("awake" if "awake" in cmdline else cmdline.split()[-1])
                        )
                        procs.append(
                            {
                                "pid": int(pid_s),
                                "label": label,
                                "rss_mb": round(int(rss_s) / 1024, 1),
                            }
                        )
        except Exception:
            pass
        return procs

    mem_procs = _catchme_processes()
    total_rss = round(sum(p["rss_mb"] for p in mem_procs), 1) if mem_procs else 0.0

    if not mem_procs:
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == "darwin":
            total_rss = round(rusage.ru_maxrss / (1024 * 1024), 1)
        else:
            total_rss = round(rusage.ru_maxrss / 1024, 1)
        mem_procs = [{"pid": _os.getpid(), "label": "web", "rss_mb": total_rss}]

    events_total = store.count()

    ts = _t.time()

    _append_monitor_snapshot(
        {
            "ts": ts,
            "disk_mb": round(db_mb + blobs_total + trees_mb, 2),
            "db_mb": db_mb,
            "blobs_mb": blobs_total,
            "trees_mb": trees_mb,
            "rss_mb": total_rss,
            "events_total": events_total,
        }
    )

    return jsonify(
        {
            "disk": {
                "db_size_mb": db_mb,
                "blobs_size_mb": blobs_total,
                "blobs_breakdown": blobs_breakdown,
                "trees_size_mb": trees_mb,
                "total_mb": round(db_mb + blobs_total + trees_mb, 2),
            },
            "memory": {
                "rss_mb": total_rss,
                "processes": mem_procs,
            },
            "events": {
                "total": events_total,
            },
            "llm": _merged_llm_usage(LLM),
            "ts": ts,
        }
    )


@app.route("/blobs/<path:filepath>")
def serve_blob(filepath: str):
    return send_from_directory(str(get_config().blob_dir), filepath)


def _serialize(e) -> dict:
    return {
        "id": e.id,
        "ts": e.timestamp,
        "kind": e.kind,
        "data": e.data,
        "blob": e.blob,
    }


def main():
    print("\n  CatchMe Viewer → http://localhost:8765\n")
    app.run(host="127.0.0.1", port=8765, debug=False)


if __name__ == "__main__":
    main()
