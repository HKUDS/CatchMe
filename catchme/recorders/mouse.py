"""Mouse-driven screenshot recorder via pynput.

On every click: capture the display, annotate with a crosshair + label,
save the annotated image, and emit with the blob path.

On scroll sessions: capture "scroll_start" on first scroll, then
"scroll_end" when the session times out (no scroll for N seconds).
"""

from __future__ import annotations

import json
import logging
import threading
import time

import mss
from PIL import Image, ImageDraw, ImageFont

from ..config import Config
from ..recorder import Emit

try:
    from pynput import mouse
except Exception:  # pragma: no cover - depends on the host, not on our code
    # pynput requires a display server (and a compiled evdev on Linux). Without
    # one it raises at import time, which would take `import catchme` down with
    # it. Degrade to a no-op recorder instead, mirroring the keyboard recorder's
    # stub on unsupported platforms.
    mouse = None  # type: ignore[assignment]

log = logging.getLogger(__name__)

_BUTTON_NAMES = (
    {
        mouse.Button.left: "left",
        mouse.Button.right: "right",
        mouse.Button.middle: "middle",
    }
    if mouse is not None
    else {}
)

_MONITOR_REFRESH = 30.0
_CROSSHAIR_COLOR = (255, 40, 40)
_CROSSHAIR_OUTLINE = (255, 255, 255)
_LABEL_BG = (220, 30, 30, 230)
_LABEL_FG = (255, 255, 255)


def _load_monitors() -> list[dict]:
    with mss.mss() as sct:
        return list(sct.monitors[1:])


def _resolve_display(x: int, y: int, monitors: list[dict]) -> tuple[int, int, int]:
    """(display_number, local_x, local_y) from global coords."""
    for i, m in enumerate(monitors, start=1):
        if m["left"] <= x < m["left"] + m["width"] and m["top"] <= y < m["top"] + m["height"]:
            return i, x - m["left"], y - m["top"]
    return 1, x, y


def _annotate(img: Image.Image, x: int, y: int, label: str) -> Image.Image:
    """Draw a bold crosshair at (x, y) with a large, high-contrast label.

    All sizes scale with image width so annotations stay visible
    on both 1080p and 4K/Retina screens.
    """
    w, h = img.size
    scale = max(w / 1920, 1.0)

    arm = int(80 * scale)
    line_w = max(int(5 * scale), 5)
    dot_r = max(int(12 * scale), 12)
    font_size = max(int(56 * scale), 56)
    pad = max(int(14 * scale), 14)
    gap = max(int(40 * scale), 40)
    outline_w = max(int(2 * scale), 2)

    rgba = img.convert("RGBA")
    overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for dx, dy in [(-outline_w, 0), (outline_w, 0), (0, -outline_w), (0, outline_w)]:
        draw.line(
            [(x - arm + dx, y + dy), (x + arm + dx, y + dy)],
            fill=_CROSSHAIR_OUTLINE,
            width=line_w + outline_w * 2,
        )
        draw.line(
            [(x + dx, y - arm + dy), (x + dx, y + arm + dy)],
            fill=_CROSSHAIR_OUTLINE,
            width=line_w + outline_w * 2,
        )
    draw.line([(x - arm, y), (x + arm, y)], fill=_CROSSHAIR_COLOR, width=line_w)
    draw.line([(x, y - arm), (x, y + arm)], fill=_CROSSHAIR_COLOR, width=line_w)

    draw.ellipse(
        [
            (x - dot_r - outline_w, y - dot_r - outline_w),
            (x + dot_r + outline_w, y + dot_r + outline_w),
        ],
        fill=_CROSSHAIR_OUTLINE,
    )
    draw.ellipse([(x - dot_r, y - dot_r), (x + dot_r, y + dot_r)], fill=_CROSSHAIR_COLOR)

    try:
        import sys as _sys

        if _sys.platform == "win32":
            font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", font_size)
        else:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except Exception:
        font = ImageFont.load_default(size=font_size)
    bbox = font.getbbox(label.upper())
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    lx = min(x + gap, w - tw - pad * 2 - 4)
    ly = max(y - th - pad * 2 - gap // 2, 4)
    rx, ry = lx + tw + pad * 2, ly + th + pad * 2
    draw.rounded_rectangle([(lx, ly), (rx, ry)], radius=max(int(8 * scale), 8), fill=_LABEL_BG)
    draw.text((lx + pad, ly + pad), label.upper(), fill=_LABEL_FG, font=font)

    return Image.alpha_composite(rgba, overlay).convert("RGB")


def _crop_detail(img: Image.Image, x: int, y: int, cw: int, ch: int) -> Image.Image:
    """Crop a pre-sized region centered on (x, y) with a dot marker."""
    w, h = img.size
    x0 = max(0, x - cw // 2)
    y0 = max(0, y - ch // 2)
    x1 = min(w, x0 + cw)
    y1 = min(h, y0 + ch)
    x0, y0 = max(0, x1 - cw), max(0, y1 - ch)

    crop = img.crop((x0, y0, x1, y1)).copy()
    cx, cy = x - x0, y - y0
    draw = ImageDraw.Draw(crop)
    r = max(cw // 40, 3)
    ow = max(r // 3, 1)
    draw.ellipse([(cx - r - ow, cy - r - ow), (cx + r + ow, cy + r + ow)], fill=_CROSSHAIR_OUTLINE)
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=_CROSSHAIR_COLOR)
    return crop


def _compute_crop_sizes(monitors: list[dict]) -> list[tuple[int, int]]:
    """Pre-compute detail crop (w, h) per monitor. Area = 1/64 of screen."""
    # 1/64 area → each dimension / sqrt(64) = / 8
    return [(max(m["width"] // 8, 64), max(m["height"] // 8, 64)) for m in monitors]


class MouseRecorder:
    kind = "mouse"
    needs_config = True

    def __init__(self, config: Config) -> None:
        self._blob_dir = config.blob_dir
        self._session_timeout = config.scroll_session_timeout
        self._listener: mouse.Listener | None = None
        self._monitors: list[dict] = []
        self._crop_sizes: list[tuple[int, int]] = []
        self._monitors_ts: float = 0
        self._lock = threading.Lock()
        self._scroll_timer: threading.Timer | None = None
        self._scroll_session_active = False
        self._last_scroll_data: dict | None = None
        self._emit: Emit | None = None

    def _refresh_monitors(self) -> None:
        try:
            self._monitors = _load_monitors()
        except Exception:
            if not self._monitors:
                self._monitors = [{"left": 0, "top": 0, "width": 9999, "height": 9999}]
        self._crop_sizes = _compute_crop_sizes(self._monitors)
        self._monitors_ts = time.monotonic()

    def _get_monitors(self) -> list[dict]:
        if time.monotonic() - self._monitors_ts > _MONITOR_REFRESH:
            self._refresh_monitors()
        return self._monitors

    def _capture(self, display: int) -> Image.Image | None:
        monitors = self._get_monitors()
        if display < 1 or display > len(monitors):
            return None
        mon = monitors[display - 1]
        try:
            with mss.mss() as sct:
                raw = sct.grab(mon)
                return Image.frombytes("RGB", (raw.width, raw.height), raw.rgb)
        except Exception:
            return None

    def _save_pair(
        self, raw_img: Image.Image, display: int, x: int, y: int, label: str, metadata: dict
    ) -> tuple[str, str]:
        """Save full + detail + metadata.json into a per-event folder."""
        day_dir = self._blob_dir / time.strftime("%Y-%m-%d")
        ts = time.time()
        event_dir = day_dir / f"{ts:.3f}_m{display}"
        event_dir.mkdir(parents=True, exist_ok=True)

        full = _annotate(raw_img, x, y, label)
        full_path = event_dir / "full.webp"
        full.save(full_path, "WEBP", quality=85)

        idx = max(display - 1, 0)
        cw, ch = (
            self._crop_sizes[idx]
            if idx < len(self._crop_sizes)
            else (max(raw_img.width // 8, 64), max(raw_img.height // 8, 64))
        )
        detail = _crop_detail(raw_img, x, y, cw, ch)
        detail_path = event_dir / "detail.webp"
        detail.save(detail_path, "WEBP", quality=90)

        meta = {"timestamp": ts, **metadata}
        with open(event_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)

        return str(full_path), str(detail_path)

    def _capture_and_save(
        self, display: int, x: int, y: int, label: str, metadata: dict
    ) -> tuple[str, str]:
        img = self._capture(display)
        if img is None:
            return "", ""
        return self._save_pair(img, display, x, y, label, metadata)

    # ── Scroll session ──

    def _end_scroll_session(self) -> None:
        """Called by Timer when scroll session times out."""
        with self._lock:
            if not self._scroll_session_active or not self._last_scroll_data:
                return
            self._scroll_session_active = False
            data = dict(self._last_scroll_data)
            data["action"] = "scroll_end"
            emit = self._emit

        if emit is None:
            return
        d, lx, ly = data["display"], data["x"], data["y"]
        blob, detail = self._capture_and_save(d, lx, ly, "scroll end", data)
        if detail:
            data["detail"] = detail
        emit(data, blob)

    # ── Lifecycle ──

    def start(self, emit: Emit) -> None:
        if mouse is None:
            log.warning("mouse recorder disabled: pynput unavailable (no display server?)")
            return
        self._emit = emit
        self._refresh_monitors()

        def on_click(x: int, y: int, button: mouse.Button, pressed: bool) -> None:
            if not pressed:
                return
            display, lx, ly = _resolve_display(round(x), round(y), self._get_monitors())
            btn = _BUTTON_NAMES.get(button, str(button))
            data = {"x": lx, "y": ly, "display": display, "button": btn, "action": "click"}
            blob, detail = self._capture_and_save(display, lx, ly, f"{btn} click", data)
            if detail:
                data["detail"] = detail
            emit(data, blob)

        def on_scroll(x: int, y: int, dx: int, dy: int) -> None:
            display, lx, ly = _resolve_display(round(x), round(y), self._get_monitors())
            data = {"x": lx, "y": ly, "display": display, "dx": dx, "dy": dy}

            with self._lock:
                is_new_session = not self._scroll_session_active
                self._scroll_session_active = True
                self._last_scroll_data = data

                if self._scroll_timer is not None:
                    self._scroll_timer.cancel()
                self._scroll_timer = threading.Timer(
                    self._session_timeout, self._end_scroll_session
                )
                self._scroll_timer.daemon = True
                self._scroll_timer.start()

            if is_new_session:
                scroll_data = {**data, "action": "scroll_start"}
                blob, detail = self._capture_and_save(display, lx, ly, "scroll start", scroll_data)
                if detail:
                    scroll_data["detail"] = detail
                emit(scroll_data, blob)

        self._listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
        self._listener.start()

    def stop(self) -> None:
        with self._lock:
            if self._scroll_timer is not None:
                self._scroll_timer.cancel()
                self._scroll_timer = None
        if self._listener:
            self._listener.stop()
