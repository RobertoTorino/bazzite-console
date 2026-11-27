#!/usr/bin/python3 -I
# SPDX-License-Identifier: GPL-3.0-or-later
"""What the app asks for as root (through pkexec, with the system Python, standard library only):

    helper.py install <recorder.py> <sensors.py>   copy both to /usr/local/lib/nexus-flight-recorder, write the
                                                   unit, start the recorder and turn it on at boot
    helper.py start | stop                         the recorder now
    helper.py boot-on | boot-off                   whether it starts with the board
    helper.py remove                               stop it and remove the unit and the copies; the recordings stay

It prints one JSON object: {"ok": true} or {"ok": false, "error": "..."}. NEXUS_SYSTEM_ROOT is another root, only
for testing."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

UNIT = "nexus-flight-recorder.service"
LIB = "usr/local/lib/nexus-flight-recorder"
UNIT_TEXT = """# SPDX-License-Identifier: GPL-3.0-or-later
# Written by Nexus Flight Recorder; its Remove takes it away.
[Unit]
Description=Nexus Flight Recorder: the sensors, memory and load, one line per second
After=local-fs.target

[Service]
Type=simple
ExecStart=/{lib}/recorder.py
Restart=on-failure
RestartSec=5
Nice=10
CPUQuota=20%

[Install]
WantedBy=multi-user.target
"""


def run(argv: list[str]) -> None:
    done = subprocess.run(argv, capture_output=True, text=True)
    if done.returncode != 0:
        raise OSError((done.stderr or done.stdout).strip() or f"{' '.join(argv)} failed")


def install(root: Path, recorder: Path, sensors: Path, run=run) -> None:
    lib = root / LIB
    lib.mkdir(mode=0o755, parents=True, exist_ok=True)
    for source, name, mode in ((recorder, "recorder.py", 0o755), (sensors, "sensors.py", 0o644)):
        shutil.copyfile(source, lib / name)
        os.chmod(lib / name, mode)
    unit = root / "etc/systemd/system" / UNIT
    unit.parent.mkdir(parents=True, exist_ok=True)
    unit.write_text(UNIT_TEXT.format(lib=LIB))
    os.chmod(unit, 0o644)
    if shutil.which("restorecon"):
        run(["restorecon", "-R", str(lib), str(unit)])
    run(["systemctl", "daemon-reload"])
    run(["systemctl", "enable", UNIT])
    run(["systemctl", "restart", UNIT])         # this copy of the recorder, after an update too


def remove(root: Path, run=run) -> None:
    run(["systemctl", "disable", "--now", UNIT])
    (root / "etc/systemd/system" / UNIT).unlink(missing_ok=True)
    shutil.rmtree(root / LIB, ignore_errors=True)
    run(["systemctl", "daemon-reload"])


def main(argv: list[str]) -> int:
    root = Path(os.environ.get("NEXUS_SYSTEM_ROOT", "/"))
    simple = {"start": ["start", UNIT], "stop": ["stop", UNIT], "boot-on": ["enable", UNIT],
              "boot-off": ["disable", UNIT]}
    try:
        if len(argv) == 3 and argv[0] == "install":
            install(root, Path(argv[1]), Path(argv[2]))
        elif argv == ["remove"]:
            remove(root)
        elif len(argv) == 1 and argv[0] in simple:
            run(["systemctl", *simple[argv[0]]])
        else:
            print(json.dumps({"ok": False, "error": "usage: install <recorder.py> <sensors.py> | start | stop | "
                                                    "boot-on | boot-off | remove"}))
            return 2
    except OSError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps({"ok": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
