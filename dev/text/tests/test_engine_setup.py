# SPDX-License-Identifier: GPL-3.0-or-later
"""Where the engine lives and the commands that set it up: with uv, with a Python 3.10 to 3.13, with neither."""

from __future__ import annotations

import pytest

from textspeech import APP_ID, ROOT, engine, engine_setup


def test_the_engine_lives_in_the_data_folder_outside_the_checkout():
    assert engine_setup.ENGINE_DIR.name == APP_ID and ROOT not in engine_setup.ENGINE_DIR.parents
    assert engine_setup.ENGINE.is_file() and engine_setup.REQUIREMENTS.is_file()
    wanted = engine_setup.REQUIREMENTS.read_text(encoding="utf-8")
    assert "kokoro-onnx" in wanted and "soundfile" in wanted


def test_installed_needs_the_python_the_packages_and_the_model_files(tmp_path):
    assert not engine_setup.installed(tmp_path)
    python = engine_setup.python(tmp_path)
    python.parent.mkdir(parents=True)
    python.touch()
    site = tmp_path / "venv" / "lib" / "python3.13" / "site-packages"
    (site / "kokoro_onnx").mkdir(parents=True)
    assert not engine_setup.installed(tmp_path)
    (site / "soundfile.py").touch()
    assert not engine_setup.installed(tmp_path)                 # no model files yet
    engine_setup.models(tmp_path).mkdir()
    for name, (size, _digest) in engine.FILES.items():
        with open(engine_setup.models(tmp_path) / name, "wb") as handle:
            handle.truncate(size - 1)
    assert not engine_setup.installed(tmp_path)                 # a download that stopped half way
    for name, (size, _digest) in engine.FILES.items():
        with open(engine_setup.models(tmp_path) / name, "wb") as handle:
            handle.truncate(size)
    assert engine_setup.installed(tmp_path)
    assert engine_setup.serve_command(tmp_path) == [str(python), str(engine_setup.ENGINE), "serve", "--models",
                                                    str(tmp_path / "models")]


def test_uv_makes_the_venv_with_a_python_of_its_own(tmp_path):
    python, requirements = str(engine_setup.python(tmp_path)), str(engine_setup.REQUIREMENTS)
    steps = engine_setup.steps(tmp_path, which=lambda name: "/bin/uv" if name == "uv" else None)
    assert steps == [["/bin/uv", "venv", "--clear", "--python", "3.13", str(tmp_path / "venv")],
                     ["/bin/uv", "pip", "install", "--python", python, "--upgrade", "-r", requirements],
                     [python, str(engine_setup.ENGINE), "fetch", "--models", str(tmp_path / "models")]]


def test_without_uv_the_newest_fitting_python_makes_it(tmp_path):
    python, requirements = str(engine_setup.python(tmp_path)), str(engine_setup.REQUIREMENTS)
    here = {name: f"/usr/bin/{name}" for name in ("python3.12", "python3.10", "python3.15")}
    steps = engine_setup.steps(tmp_path, which=here.get)
    assert steps[:2] == [["/usr/bin/python3.12", "-m", "venv", "--clear", str(tmp_path / "venv")],
                         [python, "-m", "pip", "install", "--upgrade", "-r", requirements]]
    assert steps[2][2] == "fetch"


def test_with_neither_the_message_says_what_to_install(tmp_path):
    with pytest.raises(engine_setup.SetupError, match="brew install uv"):
        engine_setup.steps(tmp_path, which=lambda name: None)
