# SPDX-License-Identifier: GPL-3.0-or-later
"""Where the speech engine lives and how it gets there. The engine needs onnxruntime, which has wheels for Python
3.10 to 3.13 only, so it cannot run in the checkout's dev venv: it gets a venv of its own beside its model files, in
~/.local/share/nexus-text-to-speech/ (venv/ and models/), outside the checkout. steps() are the commands that set it
up, run by the window one after the other: the venv (uv brings the right Python by itself; without uv a Python 3.10
to 3.13 on the PATH makes it), the packages of engine-requirements.txt, and the model files (engine.py fetch)."""

from __future__ import annotations

import shutil
from pathlib import Path

from bazzite_console_core.platform import data_home

from . import APP_ID, ROOT
from .engine import missing_files

ENGINE_DIR = data_home() / APP_ID
ENGINE = Path(__file__).with_name("engine.py")
REQUIREMENTS = ROOT / "engine-requirements.txt"
UV_PYTHON = "3.13"                      # the Python uv brings: the newest one onnxruntime has wheels for
PYTHONS = ("python3.13", "python3.12", "python3.11", "python3.10")
PACKAGES = ("kokoro_onnx", "soundfile")
NO_PYTHON = ("The speech engine needs uv, or a Python from 3.10 to 3.13. This machine has neither. Run brew install "
             "uv, then click Set up the speech engine again.")


class SetupError(Exception):
    """The engine cannot be set up on this machine as it is; the message says what to install."""


def python(root: Path = ENGINE_DIR) -> Path:
    return root / "venv" / "bin" / "python"


def models(root: Path = ENGINE_DIR) -> Path:
    return root / "models"


def installed(root: Path = ENGINE_DIR) -> bool:
    """The engine's Python, its packages and the model files are all there."""
    return (python(root).is_file()
            and all(any((root / "venv" / "lib").glob(f"python*/site-packages/{name}*")) for name in PACKAGES)
            and not missing_files(models(root)))


def serve_command(root: Path = ENGINE_DIR) -> list[str]:
    return [str(python(root)), str(ENGINE), "serve", "--models", str(models(root))]


def steps(root: Path = ENGINE_DIR, which=shutil.which) -> list[list[str]]:
    """The commands that set the engine up in *root*, in order. Running them again repairs an engine: the venv is
    made anew, the packages are brought up to date, and only a missing or damaged model file is downloaded."""
    venv, uv = str(root / "venv"), which("uv")
    if uv:
        make = [[uv, "venv", "--clear", "--python", UV_PYTHON, venv],
                [uv, "pip", "install", "--python", str(python(root)), "--upgrade", "-r", str(REQUIREMENTS)]]
    else:
        found = next((path for path in map(which, PYTHONS) if path), None)
        if not found:
            raise SetupError(NO_PYTHON)
        make = [[found, "-m", "venv", "--clear", venv],
                [str(python(root)), "-m", "pip", "install", "--upgrade", "-r", str(REQUIREMENTS)]]
    return [*make, [str(python(root)), str(ENGINE), "fetch", "--models", str(models(root))]]


__all__ = ["ENGINE", "ENGINE_DIR", "NO_PYTHON", "PACKAGES", "PYTHONS", "REQUIREMENTS", "SetupError", "UV_PYTHON",
           "installed", "models", "python", "serve_command", "steps"]
