from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


_DESCENDANT = """
import os
import signal
import sys
import time
from pathlib import Path

signal.signal(signal.SIGTERM, signal.SIG_IGN)
Path(sys.argv[1]).write_text(str(os.getpid()), encoding="utf-8")
while True:
    time.sleep(0.01)
"""


def _spawn_descendant(recipe_path: Path) -> None:
    pid_path = recipe_path.with_suffix(".descendant.pid")
    subprocess.Popen(
        [sys.executable, "-c", _DESCENDANT, str(pid_path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=False,
    )
    deadline = time.monotonic() + 2.0
    while not pid_path.is_file():
        if time.monotonic() >= deadline:
            raise RuntimeError("descendant did not become ready")
        time.sleep(0.01)


_, marker, recipe_argument, response_argument = sys.argv
if marker != "--worker":
    raise RuntimeError("expected --worker")
recipe_path = Path(recipe_argument)
response_path = Path(response_argument)
_spawn_descendant(recipe_path)

if recipe_path.name == "timeout.recipe":
    while True:
        time.sleep(0.01)
if recipe_path.name == "worker-error.recipe":
    print("descendant worker stdout", flush=True)
    print("descendant worker stderr", file=sys.stderr, flush=True)
    raise SystemExit(7)
if recipe_path.name == "missing-response.recipe":
    raise SystemExit(0)
if recipe_path.name == "invalid-response.recipe":
    response_path.write_text("{invalid", encoding="utf-8")
else:
    response_path.write_text(recipe_path.read_text(encoding="utf-8"), encoding="utf-8")
