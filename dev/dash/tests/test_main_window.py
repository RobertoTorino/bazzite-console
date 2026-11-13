# SPDX-License-Identifier: GPL-3.0-or-later
"""The dashboard: the Nexus apps of the checkout as tiles, the suite's tools after them, the suite chosen in the
header, and what a click does."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QImage

from nexus_dashboard import APP_NAME, CHECKOUT, LOGO_PATH, checkout, main_window
from nexus_dashboard.main_window import SUITE_KEY, MainWindow


def test_the_dashboard_icons_are_present_at_512_and_128_px():
    assert LOGO_PATH.name == "nexus-dashboard.webp"
    assert QImage(str(LOGO_PATH)).size().width() == 512
    assert QImage(str(LOGO_PATH.with_name("nexus-dashboard-128.png"))).size().width() == 128


def test_the_checkout_has_only_bazzite_console_and_its_developer_apps():
    assert checkout.suites(CHECKOUT) == ["bazzite-console"]
    assert checkout.suite_name(CHECKOUT, "bazzite-console") == "Bazzite Console Suite"
    assert checkout.suite_system(CHECKOUT, "bazzite-console") == "bazzite"
    assert checkout.here(CHECKOUT, "bazzite-console", "linux")
    assert not checkout.here(CHECKOUT, "bazzite-console", "win32")
    apps = checkout.dev_apps(CHECKOUT)
    assert [app.key for app in apps] == ["nrt", "demo", "deps", "itests", "sounds"]   # the release tool, then by name
    assert [app.name for app in apps] == ["Nexus Release Tool", "Nexus Demo Recorder", "Nexus Deps",
                                          "Nexus Installer Tests", "Nexus Sound Lab"]
    assert all(app.icon is not None and app.icon.is_file() for app in apps)
    # Nexus Deps checks this Bazzite suite and has a Linux launcher only.
    assert all(app.script.is_file() for app in apps if not (checkout.WINDOWS and app.key == "deps"))
    assert apps[1].log.name == "demo.log"


def test_the_window_lists_the_apps_then_the_suites_tools(qapp):
    settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "test", "test")
    window = MainWindow(settings=settings, suite="bazzite-console")

    assert window.windowTitle() == APP_NAME
    names = [window.tiles.item(i).text() for i in range(window.tiles.count())]
    assert names == ["Nexus Release Tool", "Nexus Demo Recorder", "Nexus Deps", "Nexus Installer Tests",
                     "Nexus Sound Lab", "Portal video tour", "Apps video tour"]
    assert window.suite_box.currentText() == "Bazzite Console Suite" and settings.value(SUITE_KEY) is None
    enabled = [bool(window.tiles.item(i).flags() & Qt.ItemFlag.ItemIsEnabled) for i in range(window.tiles.count())]
    if sys.platform == "win32":
        assert enabled == [True, True, False, True, True, False, False]   # Nexus Deps: no run.ps1
    else:
        assert enabled == [True] * 7
    window.close()


def test_the_dashboard_keeps_the_suite_selection(qapp):
    settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "test", "test")
    settings.setValue(SUITE_KEY, "missing-suite")
    window = MainWindow(settings=settings)
    assert window.suite == "bazzite-console"
    window.close()


def test_nexus_deps_is_enabled_for_bazzite_console(qapp):
    settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "test", "test")
    window = MainWindow(settings=settings, suite="bazzite-console")
    tiles = {window.tiles.item(i).text(): window.tiles.item(i) for i in range(window.tiles.count())}
    assert bool(tiles["Nexus Deps"].flags() & Qt.ItemFlag.ItemIsEnabled) == (sys.platform != "win32")
    window.close()


def test_a_click_on_an_app_starts_it_with_the_suite_and_says_so(qapp, tmp_path):
    started = []
    window = MainWindow(settings=None, suite="bazzite-console", starter=lambda app, args: started.append((app.key, args)))
    tiles = {window.tiles.item(i).text(): window.tiles.item(i) for i in range(window.tiles.count())}

    window.click(tiles["Nexus Release Tool"].data(Qt.ItemDataRole.UserRole))
    window.click(tiles["Nexus Installer Tests"].data(Qt.ItemDataRole.UserRole))
    window.click(tiles["Nexus Demo Recorder"].data(Qt.ItemDataRole.UserRole))
    window.click(tiles["Nexus Deps"].data(Qt.ItemDataRole.UserRole))

    assert started == [("nrt", ()), ("itests", ("--suite", "bazzite-console")), ("demo", ()),
                       ("deps", ("--suite", "bazzite-console"))]
    assert "Nexus Release Tool" in window.output.toPlainText() and "started from" in window.output.toPlainText()

    def refuse(app, args):
        raise OSError("no bash")
    window.starter = refuse
    window.click(tiles["Nexus Release Tool"].data(Qt.ItemDataRole.UserRole))
    assert "could not start (no bash)" in window.output.toPlainText()
    window.close()


def test_a_click_on_a_tool_opens_its_dialog_on_the_suite(qapp, monkeypatch):
    opened = []
    for name in ("PortalTourDialog", "AppsTourDialog"):
        monkeypatch.setattr(main_window, name, lambda *args, _name=name: type(
            "Fake", (), {"exec": lambda self: opened.append((_name, args[:-1]))})())
    window = MainWindow(settings=None, suite="bazzite-console")
    tiles = {window.tiles.item(i).text(): window.tiles.item(i) for i in range(window.tiles.count())}
    for name in ("Portal video tour", "Apps video tour"):
        tile = tiles[name].data(Qt.ItemDataRole.UserRole)
        tile.off = ""                                    # whatever the system: the dialogs are what is tested
        window.click(tile)

    assert opened == [("PortalTourDialog", (CHECKOUT, window.open_file)),
                      ("AppsTourDialog", (CHECKOUT, window.open_file))]
    window.close()


def test_a_checkout_without_suites_or_apps(qapp, tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "dev").mkdir()
    window = MainWindow(tmp_path, settings=None)
    assert window.suite is None and window.apps == []
    assert [window.tiles.item(i).text() for i in range(window.tiles.count())] == ["Portal video tour",
                                                                                  "Apps video tour"]
    assert all(not window.tiles.item(i).flags() & Qt.ItemFlag.ItemIsEnabled for i in range(2))
    assert window.local_apps.count() == 0
    window.close()


def test_start_runs_the_apps_script_in_its_folder_with_a_log(tmp_path, monkeypatch):
    app = checkout.DevApp(tmp_path / "x", "nexus-x", "X", "0.1.0", None)
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "run.sh").write_text("echo hello $1\n", encoding="utf-8")
    monkeypatch.setattr(checkout, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(checkout, "WINDOWS", False)

    process = checkout.start(app, ("--suite", "s"))
    process.wait(10)

    assert process.returncode == 0
    assert (tmp_path / "logs" / "x.log").read_text(encoding="utf-8") == "hello --suite\n"



@pytest.mark.skipif(sys.platform != "win32", reason="run.ps1 runs with Windows PowerShell")
def test_start_runs_the_apps_powershell_script_on_windows(tmp_path, monkeypatch):
    """The script really runs: PowerShell started without a console (DETACHED_PROCESS) quit at once with code 0."""
    app = checkout.DevApp(tmp_path / "x", "nexus-x", "X", "0.1.0", None)
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "run.ps1").write_text("Write-Output \"hello $($args[0])\"\nexit 3\n", encoding="utf-8")
    monkeypatch.setattr(checkout, "LOG_DIR", tmp_path / "logs")

    process = checkout.start(app, ("--suite", "s"))
    process.wait(30)

    assert process.returncode == 3
    assert (tmp_path / "logs" / "x.log").read_text(encoding="utf-8").strip() == "hello --suite"

def test_a_second_launch_opens_no_window(qapp, monkeypatch):
    """A double-click on the Desktop icon starts the app twice: the second launch hands over to the first."""
    import nexus_dashboard.__main__ as entry
    asked = []
    monkeypatch.setattr(entry, "create_app", lambda *a, **k: qapp)
    monkeypatch.setattr(entry.instance, "already_running", lambda app_id: asked.append(app_id) or True)
    monkeypatch.setattr("sys.argv", ["nexus_dashboard"])
    assert entry.main() == 0 and asked == [entry.APP_ID]


def test_a_click_on_the_dashboard_icon_opens_suite_documentation(qapp, monkeypatch):
    opened = []
    monkeypatch.setattr(main_window, "open_url", opened.append)
    window = MainWindow(settings=None, suite="bazzite-console")

    assert window.header.logo.cursor().shape() == Qt.CursorShape.PointingHandCursor
    window.header.logo.clicked.emit()

    assert opened == ["https://robertotorino.github.io/bazzite-console/"]
    window.close()
