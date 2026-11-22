# SPDX-License-Identifier: GPL-3.0-or-later
"""Every text file of the repository opens with its license line (owner, 22-11-2026), in the comment of its format:
"# SPDX-License-Identifier: GPL-3.0-or-later", "<!-- ... -->" in Markdown, SVG and XML, "// ..." in JavaScript.
An app under another license names that one (Persistent ACPI's MIT, PS Remote Play's AGPL): the check asks for the
line, not for one license. It may follow a #! line, an <?xml ...?> line, <!doctype html>, a .desktop file's
[Desktop Entry] or a front matter block. A file that would break with it, or that is another project's, is left out
below, with the reason."""

from __future__ import annotations

import fnmatch
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LINE = "SPDX-License-Identifier: GPL-3.0-or-later"     # the repository's license
TAG = "SPDX-License-Identifier:"
FIRST = ("#!", "<?xml", "<!doctype", "<!DOCTYPE", "[Desktop Entry]")   # lines that must stay first
LEFT_OUT = {
    "LICENSE": "the license text itself",
    "*/LICENSE": "the license text itself",
    "COPYING*": "another project's license text",
    "*/COPYING*": "another project's license text",
    "*-LICENSE.txt": "a font's own license text",
    "tools/licenses/*": "other projects' license texts",
    "VERSION": "one value that the tools read",
    "*/VERSION": "one value that the tools read",
    "SYSTEM": "one value that the tools read",
    "TAG_PREFIX": "one value that the tools read",
    "NEXUS_REF": "one value that the tools read",
    "*.stamp": "one value that the tools read",
    "CHANGELOG": "the release tools write each new entry at the top",
    "*/CHANGELOG": "the release tools write each new entry at the top",
    "*.json": "JSON has no comments",
    "*.lock": "Cargo writes it",
    "*.patch": "a patch must start with its own header",
    "*.asc": "another project's signing keys",
    "*/tests/fixtures/*": "recorded data, kept as it was read",
    "tools/text_check/styles/*": "Vale's style packages, another project's files",
    "*/mymc/*": "the ported mymc++ code, with its authors' own header",
    "apps/quickfix/quickfix/vrm/bc250_vrm_core.c": "bc250-vrm-dkms's file, checked by its checksum",
    "*/pcsx2_defaults.ini": "PCSX2's own file, as PCSX2 writes it",
    "*/native/ffmpeg/*": "FFmpeg's files",
    ".claude/workflows/*.js": "a workflow script must begin with its meta block",
}


def left_out(path: str) -> str:
    return next((why for pattern, why in LEFT_OUT.items() if fnmatch.fnmatch(path, pattern)), "")


def tracked() -> list[str]:
    """The repository's files, as git knows them; another checkout inside it is not among them."""
    done = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True)
    return [p for p in done.stdout.decode().split("\0") if p]


def text_of(path: Path) -> str | None:
    """The file as text, None for a picture or other binary file and an empty file."""
    data = path.read_bytes()
    if not data or b"\0" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def opens_with_line(text: str) -> bool:
    """A license line comes first, after a line that must stay first (FIRST), a front matter block and blank lines."""
    lines = text.splitlines()
    i = 0
    if lines and lines[0].startswith(FIRST):
        i = 1
    if i < len(lines) and lines[i].strip() == "---":
        end = next((j for j in range(i + 1, len(lines)) if lines[j].strip() == "---"), None)
        if end is not None:
            i = end + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    return i < len(lines) and TAG in lines[i]


@pytest.mark.skipif(not shutil.which("git") or not (ROOT / ".git").exists(), reason="needs git and a checkout")
def test_every_text_file_opens_with_its_license_line():
    missing = []
    for name in tracked():
        path = ROOT / name
        if left_out(name) or not path.is_file():
            continue
        text = text_of(path)
        if text is not None and not opens_with_line(text):
            missing.append(name)
    assert not missing, f"No {TAG} line at the top: {missing}"


def test_the_line_may_follow_a_shebang_or_front_matter():
    assert opens_with_line("#!/usr/bin/env bash\n# SPDX-License-Identifier: GPL-3.0-or-later\n")
    assert opens_with_line("---\ntemplate: home.html\n---\n\n<!-- SPDX-License-Identifier: GPL-3.0-or-later -->\n")
    assert not opens_with_line("import os\n# SPDX-License-Identifier: GPL-3.0-or-later\n")
    assert opens_with_line("[Desktop Entry]\n# SPDX-License-Identifier: GPL-3.0-or-later\nType=Application\n")
    assert opens_with_line("# SPDX-License-Identifier: MIT\n")                  # an app under its own license
    assert left_out("apps/gpu/CHANGELOG") and left_out("tools/text_check/styles/proselint/Very.yml")
    assert not left_out("apps/gpu/gpu_governor/main_window.py")
