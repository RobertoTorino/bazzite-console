# SPDX-License-Identifier: GPL-3.0-or-later
"""What a run of tools/text_check.py found, read from the tool itself: every problem from its --json file, and the
order of the files and their words from the table it prints (worst first: the problems to fix per 1000 words). The
checks are the tool's. Nothing here checks a text. And the LanguageTool server of the tool's --server, as podman
sees it, with the tool's own names and functions."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

CHECKS = ("rules", "LanguageTool", "Vale")
# The tool's table: to fix, per 1000, advice, words, then the file
_ROW = re.compile(r"^\s*(\d+)\s+\d+(?:\.\d+)?\s+(\d+)\s+(\d+)\s{2}(\S.*)$")
_CHECKING = re.compile(r"^Checking (\d+) files, (\d+) words\.\.\.$", re.M)
_SUMMARY = re.compile(r"^\d+ problems in \d+ of \d+ files.*$", re.M)


@dataclass(frozen=True)
class Problem:
    """One problem, as the tool's --json writes it."""

    path: str
    line: int
    check: str                          # rules, LanguageTool or Vale
    kind: str                           # Vale's style hints are "advice"
    message: str
    text: str
    suggestion: str = ""


@dataclass
class FileResult:
    path: str
    words: int = 0                      # 0: the table did not say
    problems: list[Problem] = field(default_factory=list)

    @property
    def to_fix(self) -> int:
        return sum(p.kind != "advice" for p in self.problems)

    @property
    def advice(self) -> int:
        return len(self.problems) - self.to_fix

    def count(self, check: str) -> int:
        return sum(p.check == check for p in self.problems)

    @property
    def per_1000(self) -> float | None:
        """The problems to fix per 1000 words, as the tool works it out; None without the words."""
        return 1000 * self.to_fix / self.words if self.words else None


def read_problems(text: str) -> list[Problem]:
    """The problems of a --json file; ValueError when it holds no list of problems."""
    names = Problem.__dataclass_fields__
    found = json.loads(text)
    if not isinstance(found, list) or not all(isinstance(item, dict) for item in found):
        raise ValueError("no list of problems")
    return [Problem(**{k: v for k, v in item.items() if k in names}) for item in found]


def read_order(output: str) -> list[tuple[str, int]]:
    """(file, words) for each row of the tool's table, in its order."""
    return [(m.group(4), int(m.group(3))) for m in map(_ROW.match, output.splitlines()) if m]


def checked(output: str) -> tuple[int, int] | None:
    """The files and words the tool read, from its first line; None when it did not get that far."""
    found = _CHECKING.search(output)
    return (int(found.group(1)), int(found.group(2))) if found else None


def summary(output: str) -> str:
    """The tool's own summary line: "12 problems in 3 of 40 files, 9000 words (1.3 per 1000 words)."."""
    found = _SUMMARY.search(output)
    return found.group(0).strip() if found else ""


def results(output: str, problems: list[Problem]) -> list[FileResult]:
    """The files with problems, worst first, in the tool's order. A file the table left out comes last."""
    by_file: dict[str, FileResult] = {}
    for path, words in read_order(output):
        by_file[path] = FileResult(path, words)
    for problem in problems:
        by_file.setdefault(problem.path, FileResult(problem.path)).problems.append(problem)
    for result in by_file.values():
        result.problems.sort(key=lambda p: (p.line, p.check))
    order = [path for path, _ in read_order(output)]
    listed = [by_file[path] for path in order if by_file[path].problems]
    rest = sorted((r for path, r in by_file.items() if path not in order and r.problems),
                  key=lambda r: (-r.to_fix, r.path))
    return listed + rest


def last_lines(output: str, count: int = 3) -> str:
    """The end of the output, where the tool says why it stopped."""
    return "\n".join([line.strip() for line in output.splitlines() if line.strip()][-count:])


# The server.

@dataclass(frozen=True)
class Server:
    podman: bool                        # podman is on the machine
    image: bool                         # LanguageTool is downloaded: the tool's image exists
    url: str | None                     # the shared server's address while it runs


def load_tool(path: Path):
    """tools/text_check.py as a module, for its names (the image, the server) and its podman calls."""
    spec = importlib.util.spec_from_file_location("text_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def probe(path: Path) -> Server:
    """The server as the tool sees it: podman, the tool's image and its shared server. It takes a moment, so the
    window runs it off its thread."""
    if shutil.which("podman") is None:
        return Server(False, False, None)
    tool = load_tool(path)
    image = tool.podman("image", "exists", tool.IMAGE, capture_output=True).returncode == 0
    return Server(True, image, tool.shared_server())
