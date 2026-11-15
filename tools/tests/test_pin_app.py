# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("pin_app", TOOLS / "pin_app.py")
pin_app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pin_app
spec.loader.exec_module(pin_app)

SHA = "ab" * 32


def test_pin_changes_only_that_app():
    text = (TOOLS.parent / "portal" / "apps.toml").read_text(encoding="utf-8")
    block = text[text.index("[apps.fan]"):]
    old_tag, old_sha = (re.search(rf'^{f} = "(.*)"$', block, re.M)[1] for f in ("tag", "sha256"))
    new = pin_app.pin(text, "fan", "ps5-fan-v9.9.9", SHA)
    changed = [(a, b) for a, b in zip(text.splitlines(), new.splitlines()) if a != b]
    assert changed == [(f'tag = "{old_tag}"', 'tag = "ps5-fan-v9.9.9"'),
                       (f'sha256 = "{old_sha}"', f'sha256 = "{SHA}"')]
    assert len(new.splitlines()) == len(text.splitlines())


def test_pin_last_table_and_missing_app():
    text = '[apps.a]\ntag = "ps5-a-v1.0.0"\nsha256 = ""\n'
    assert 'tag = "ps5-a-v1.0.1"' in pin_app.pin(text, "a", "ps5-a-v1.0.1", SHA)
    with pytest.raises(SystemExit, match="no \\[apps.b\\]"):
        pin_app.pin(text, "b", "ps5-b-v1.0.0", SHA)


def test_pin_adds_the_sha256_line_a_new_app_lacks():
    """A new app is listed with its first tag and no sha256 line until that release exists (apps.toml allows it):
    the pin adds the line after the tag, in its place, and leaves the rest alone."""
    text = '[apps.a]\nname = "a"\ntag = "ps5-a-v0.1.0"\nrequired = false\n\n[apps.b]\ntag = "ps5-b-v1.0.0"\nsha256 = ""\n'
    new = pin_app.pin(text, "a", "ps5-a-v0.1.0", SHA)
    assert new == f'[apps.a]\nname = "a"\ntag = "ps5-a-v0.1.0"\nsha256 = "{SHA}"\nrequired = false\n\n[apps.b]\n' \
                  'tag = "ps5-b-v1.0.0"\nsha256 = ""\n'
    assert pin_app.pin(new, "a", "ps5-a-v0.1.1", "ef" * 32).count("sha256 =") == 2       # replaced, not added again
    with pytest.raises(SystemExit, match="no tag line"):
        pin_app.pin('[apps.a]\nname = "a"\n', "a", "ps5-a-v0.1.0", SHA)


def test_main_writes_the_manifest(tmp_path, monkeypatch, capsys):
    """A pin from the command line writes the tag and sha256 lines of portal/apps.toml."""
    text = '[apps.a]\ntag = "ps5-a-v1.0.0"\nsha256 = ""\n'
    suite = tmp_path / "suite/portal/apps.toml"
    suite.parent.mkdir(parents=True)
    suite.write_text(text)
    monkeypatch.setattr(pin_app, "SUITE", tmp_path / "suite")
    monkeypatch.setattr(pin_app, "MANIFEST", suite)
    assert pin_app.main(["ps5-a-v1.0.1", "--sha256", SHA]) == 0
    assert suite.read_bytes() == f'[apps.a]\ntag = "ps5-a-v1.0.1"\nsha256 = "{SHA}"\n'.encode()
    assert capsys.readouterr().out.splitlines() == [f"pinned ps5-a-v1.0.1 ({SHA[:16]}…) in portal/apps.toml"]
