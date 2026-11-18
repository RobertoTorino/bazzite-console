# SPDX-License-Identifier: GPL-3.0-or-later
"""A log file per app (owner, 24-10-2026): ~/.local/share/<app id>/<app id>.log, one line per thing the app says or
does, with the time, and every uncaught error with its traceback. The file turns over at 1 MB, with three older
ones kept, so it never grows past a few MB; clear() empties it. An app calls setup() once at start and logger()
wherever it logs; what the file holds the app also shows in its window, so the log is what happened in words, not
a debug trace.

Personal data stays out of it as it stays out of everything else the suite writes: an app logs what it did, not
keys or account details."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .platform import data_home, private as private_text

MAX_BYTES = 1_000_000
KEPT = 3
FORMAT = "%(asctime)s %(levelname)s %(message)s"
DATE = "%d-%m-%Y %H:%M:%S"


def log_file(app_id: str) -> Path:
    """The app's log: ~/.local/share/<app id>/<app id>.log."""
    return data_home() / app_id / f"{app_id}.log"


def logger(app_id: str) -> logging.Logger:
    return logging.getLogger(app_id)


class _Private(logging.Formatter):
    """Every line with the user's home folder written as ~: no user name in a log (platform.private)."""

    def format(self, record: logging.LogRecord) -> str:
        return private_text(super().format(record))


def setup(app_id: str, path: Path | None = None, private: bool = False) -> Path:
    """The app's log, in *path* (its own file, log_file(app_id), when not given): every record of
    logger(app_id) goes there, and an uncaught exception is written before Python reports it. A second call changes
    nothing. Returns the file; when it cannot be made, the log goes to stderr and the file is still what is
    returned. *private*: the user's folders masked in every line (owner, 29-10-2026: no user name in a log)."""
    path = path or log_file(app_id)
    log = logger(app_id)
    if log.handlers:
        return path
    log.setLevel(logging.INFO)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(path, maxBytes=MAX_BYTES, backupCount=KEPT,
                                                       encoding="utf-8")
    except OSError:
        handler = logging.StreamHandler()
    handler.setFormatter((_Private if private else logging.Formatter)(FORMAT, DATE))
    log.addHandler(handler)
    previous = sys.excepthook

    def excepthook(kind, error, trace) -> None:
        log.critical("Uncaught error", exc_info=(kind, error, trace))
        previous(kind, error, trace)
    sys.excepthook = excepthook
    return path


def clear(app_id: str, path: Path | None = None) -> bool:
    """The app's log emptied (owner, 18-11-2026: Clear Logs): the file itself, *path* (log_file(app_id) when not
    given), and the older ones kept beside it. The file stays open and in use: the next line the app logs is its
    first. False when a file could not be emptied or removed."""
    path = path or log_file(app_id)
    done = True
    for handler in logger(app_id).handlers:
        if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == path.absolute():
            handler.acquire()
            try:
                if handler.stream is not None:      # opened to append: after this the next line is the first
                    handler.stream.truncate(0)
            except OSError:
                done = False
            finally:
                handler.release()
    try:
        if path.exists():
            path.write_text("", encoding="utf-8")
        for number in range(1, KEPT + 1):
            path.with_name(f"{path.name}.{number}").unlink(missing_ok=True)
    except OSError:
        done = False
    return done


def tail(path: Path, lines: int = 200) -> str:
    """The last *lines* of the log, "" when there is none yet."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(text.rstrip("\n").split("\n")[-lines:]) if text.strip() else ""
