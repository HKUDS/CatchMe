"""Screen-capture-free discovery and collection commands."""

from __future__ import annotations

import argparse
import json
import time

from catchme.config import get_default_config

from .catalog import scan
from .collect import READERS, collect
from .store import ActivityStore


def main(args):
    parser = argparse.ArgumentParser(prog="catchme sources")
    parser.add_argument(
        "action",
        choices=["scan", "list", "enable", "disable", "collect", "watch"],
        nargs="?",
        default="list",
    )
    parser.add_argument("source", nargs="?")
    parser.add_argument("--interval", type=float, default=10)
    options = parser.parse_args(args)
    db = ActivityStore(get_default_config().root / "activity.db")
    if options.action == "scan":
        print(json.dumps(scan(db), indent=2))
    elif options.action == "list":
        for s in db.sources():
            print(f"{'ON ' if s['enabled'] else 'OFF'} {s['id']:<45} {s['status']}")
    elif options.action in ("enable", "disable"):
        sources = {s["id"]: s for s in db.sources()}
        if options.source not in sources:
            parser.error("Unknown source; run catchme sources scan/list first")
        s = sources[options.source]
        if options.action == "enable" and (
            s["reader"] not in READERS or s["status"] in ("missing", "unsupported")
        ):
            parser.error("No available reader for this source")
        with db.connect() as conn:
            conn.execute(
                "UPDATE sources SET enabled=? WHERE id=?",
                (options.action == "enable", options.source),
            )
        print(options.action + ": " + options.source)
    elif options.action == "collect":
        print(json.dumps(collect(db), indent=2))
    else:
        if not 1 <= options.interval <= 3600:
            parser.error("interval must be between 1 and 3600 seconds")
        print("Collecting enabled sources. Ctrl+C to stop.", flush=True)
        try:
            while True:
                print(json.dumps(collect(db)), flush=True)
                time.sleep(options.interval)
        except KeyboardInterrupt:
            pass
