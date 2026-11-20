"""Synthetic process metadata for the RAM command."""

import sys
from types import SimpleNamespace

import pytest

from catchme import run


@pytest.mark.parametrize(
    ("name", "args", "expected"),
    [
        ("catchme", ["/opt/bin/catchme", "web"], True),
        ("CatchMe.exe", [r"C:\Program Files\CatchMe\CatchMe.exe", "awake"], True),
        ("python3.11", ["/usr/bin/python3.11", "-m", "catchme", "web"], True),
        ("python.exe", [r"C:\Python\python.exe", r"C:\env with spaces\Scripts\catchme"], True),
        ("python", ["python", "-m", "pytest", "/tmp/catchme-tests/test_ui.py"], False),
        ("other-catchme", ["other-catchme", "web"], False),
        ("python", ["python", "/tmp/catchme-project/main.py"], False),
        ("python", [], False),
    ],
)
def test_cli_process_selection(name, args, expected):
    assert run._is_catchme_cli(name, args) is expected


def test_ram_ignores_unrelated_and_inaccessible_processes(monkeypatch, capsys):
    class ProcessError(Exception):
        pass

    def process(pid, name, args, memory):
        return SimpleNamespace(
            info={"pid": pid, "name": name, "cmdline": args, "memory_info": memory}
        )

    processes = [
        process(
            900001, "python", ["python", "-m", "catchme", "web"], SimpleNamespace(rss=20 * 1024**2)
        ),
        process(
            900002,
            "python",
            ["python", "-m", "pytest", "/tmp/catchme-tests"],
            SimpleNamespace(rss=64 * 1024**2),
        ),
        process(900003, "catchme", [], None),
        process(900004, "catchme.exe", ["catchme.exe", "awake"], SimpleNamespace(rss=5 * 1024**2)),
    ]
    fake = SimpleNamespace(
        process_iter=lambda fields: processes,
        NoSuchProcess=ProcessError,
        AccessDenied=ProcessError,
        ZombieProcess=ProcessError,
    )
    monkeypatch.setitem(sys.modules, "psutil", fake)
    run.cmd_ram()
    output = capsys.readouterr().out
    assert "25.0 MB" in output
    assert "pid 900001" in output and "pid 900004" in output
    assert "pid 900002" not in output and "pid 900003" not in output
