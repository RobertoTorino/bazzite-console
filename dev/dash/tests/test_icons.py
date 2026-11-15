# SPDX-License-Identifier: GPL-3.0-or-later
import subprocess
import sys
from pathlib import Path

import pytest

from nexus_dashboard import CHECKOUT, icons

SUITE = CHECKOUT


def _checkout(root: Path) -> Path:
    """A checkout with the suite's tool and two categories."""
    (root / "tools").mkdir(parents=True, exist_ok=True)
    (root / "tools" / "sync_icons.py").write_text("", encoding="utf-8")
    (root / "icons" / "leaf").mkdir(parents=True)
    (root / "icons" / "gear").mkdir()
    (root / "icons" / "categories.toml").write_text("", encoding="utf-8")
    return root


def test_a_suite_with_category_icons_is_told_apart(tmp_path):
    suite = _checkout(tmp_path / "suite")
    assert icons.has_category_icons(suite) and not icons.has_category_icons(tmp_path)
    assert icons.categories(suite) == ["gear", "leaf"]
    assert icons.has_category_icons(SUITE)
    assert icons.icon_path(SUITE, "gaming", 512).name == "gaming-512.webp"


def test_whole_set_runs_first_then_each_size_in_order(tmp_path):
    _checkout(tmp_path)
    tool = [sys.executable, str(tmp_path / "tools" / "sync_icons.py"), "--category", "leaf"]

    whole, small, medium = Path("/a.png"), Path("/s.png"), Path("/m.png")
    assert icons.convert_commands(tmp_path, "leaf", whole, {128: small, 512: medium}) == [
        tool + ["--from", str(whole)],
        tool + ["--from", str(medium), "--size", "512"],
        tool + ["--from", str(small), "--size", "128"],
    ]
    assert icons.convert_commands(tmp_path, "leaf", None, {}) == []


def test_icon_names_match_the_nexus_tool():
    sys.path.insert(0, str(CHECKOUT / "tools"))
    try:
        import sync_icons
    finally:
        sys.path.remove(str(CHECKOUT / "tools"))
    assert icons.SIZES == sync_icons.SIZES
    for size in icons.SIZES:
        assert icons.icon_path(SUITE, "leaf", size) == sync_icons.icon_path(SUITE / "icons" / "leaf", size)


def test_dialog_runs_the_conversions_and_shows_their_output(qapp, tmp_path, monkeypatch):
    root = _checkout(tmp_path)
    runs = []

    def run(command, **kwargs):
        runs.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="converted: leaf-512\n", stderr="")

    monkeypatch.setattr(icons.subprocess, "run", run)
    dialog = icons.IconsDialog(tmp_path)
    assert dialog.checkout_label.text() == str(root)
    assert not dialog.convert_button.isEnabled()
    dialog.category.setCurrentText("leaf")
    dialog.sizes[512].setText("/new.png")
    assert dialog.convert_button.isEnabled()

    assert dialog.convert()

    assert runs == [icons.convert_commands(tmp_path, "leaf", None, {512: Path("/new.png")})[0]]
    assert "converted: leaf-512" in dialog.output.toPlainText()
    assert dialog.sizes[512].text() == ""
    dialog.close()


def test_dialog_stops_at_the_first_failure(qapp, tmp_path, monkeypatch):
    root = _checkout(tmp_path)
    runs = []

    def run(command, **kwargs):
        runs.append(command)
        return subprocess.CompletedProcess(command, 1, stdout="",
                                           stderr="/a.png: 512 x 256 px, an icon must be square\n")

    monkeypatch.setattr(icons.subprocess, "run", run)
    dialog = icons.IconsDialog(tmp_path)
    dialog.whole.setText("/a.png")
    dialog.sizes[128].setText("/b.png")

    assert not dialog.convert()

    assert len(runs) == 1
    assert "must be square" in dialog.output.toPlainText()
    assert "stopped with status 1" in dialog.output.toPlainText()
    assert dialog.whole.text() == "/a.png"
    dialog.close()


def test_dialog_on_a_suite_without_category_icons_is_greyed_out(qapp, tmp_path):
    (tmp_path / "icons").mkdir(parents=True)
    dialog = icons.IconsDialog(tmp_path)
    assert dialog.category.count() == 0 and dialog.checkout is None
    assert not dialog.convert_button.isEnabled()
    assert "no category icons" in dialog.output.toPlainText()
    dialog.close()


def test_dialog_converts_real_images_in_a_copy_of_the_icons(qapp, tmp_path):
    """The whole way, with the suite's own tool on a copy of its icons and the apps' copies."""
    import shutil

    root = tmp_path / "suite"                                  # a suite laid out as the real one
    shutil.copytree(SUITE / "icons", root / "icons")
    (root / "portal").mkdir()
    (root / "portal" / "apps.toml").write_text("", encoding="utf-8")
    (root / "tools").mkdir()
    shutil.copy(CHECKOUT / "tools" / "sync_icons.py", root / "tools")
    for copy in [p for p in (SUITE / "apps").glob("*/images/*") if p.suffix in (".png", ".webp")] + \
            list((SUITE / "portal" / "images" / "apps").glob("*.webp")):
        target = root / copy.relative_to(SUITE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(copy, target)
    from PIL import Image
    Image.new("RGBA", (300, 300), "blue").save(tmp_path / "blue.png")
    dialog = icons.IconsDialog(root)
    dialog.category.setCurrentText("gaming")
    dialog.sizes[256].setText(str(tmp_path / "blue.png"))

    assert dialog.convert(), dialog.output.toPlainText()

    with Image.open(root / "icons" / "gaming" / "gaming-256.webp") as image:
        assert image.size == (256, 256) and image.format == "WEBP"
    assert (root / "portal" / "images" / "apps" / "rpcs3.webp").read_bytes() == \
        (root / "icons" / "gaming" / "gaming-256.webp").read_bytes()
    assert (root / "icons" / "gaming" / "gaming-512.webp").read_bytes() == \
        (SUITE / "icons" / "gaming" / "gaming-512.webp").read_bytes()
    dialog.close()
