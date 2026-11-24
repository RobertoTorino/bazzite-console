# SPDX-License-Identifier: GPL-3.0-or-later
"""ps5-cores-bisect.sh starts stress-ng with its own temp folder: stress-ng 0.22 refuses to start in a folder it
can't write, such as the root-owned app folder the window starts in."""

from __future__ import annotations

import re
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "ps5-cores-bisect.sh"


def test_stress_ng_writes_its_temp_files_in_the_logs_folder():
    text = SCRIPT.read_text()
    starts = re.findall(r'"\$STRESS_BIN" (?:[^\n]|\\\n)*', text)
    assert starts, "the stress-ng start line is gone"
    assert all('--temp-path "$LOGS"' in start for start in starts)
    assert re.search(r'^LOGS="\$STATE_DIR/logs"$', text, re.M)
