# SPDX-License-Identifier: GPL-3.0-or-later
"""The dashboard: the development apps of the checkout as tiles, the suite's tools after them, and what a click
does."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage

from bazzite_console_core import SUITE_MANUAL_URL
from nexus_dashboard import APP_NAME, CHECKOUT, LOGO_PATH, checkout, main_window
from nexus_dashboard.main_window import MainWindow


def test_the_icons_are_nexus_at_512_and_128_px():
    assert LOGO_PATH.name == "nexus-dashboard.webp"
    assert QImage(str(LOGO_PATH)).size().width() == 512
    assert QImage(str(LOGO_PATH.with_name("nexus-dashboard-128.png"))).size().width() == 128


def test_the_checkout_is_the_suite_with_its_development_apps():
    assert checkout.suite_name(CHECKOUT) == "Bazzite Console Suite"
    apps = checkout.dev_apps(CHECKOUT)
    assert [app.key for app in apps] == ["nrt", "demo", "deps", "flight", "garbage", "itests", "marketing",
                                          "studio", "sounds", "text"]   # the release tool, then by name
    assert [app.name for app in apps] == ["Nexus Release Tool", "Nexus Demo Recorder", "Nexus Deps",
                                          "Nexus Flight Recorder", "Nexus Garbage Remover", "Nexus Installer Tests",
                                          "Nexus Marketing for PS5", "Nexus Remix Studio", "Nexus Sound Lab",
                                          "Nexus TTS"]
    assert all(app.icon is not None and app.icon.is_file() for app in apps)
    assert all(app.script.is_file() for app in apps)
    assert apps[1].log.name == "demo.log"


def test_the_window_lists_the_apps_then_the_suites_tools(qapp):
    window = MainWindow()

    assert window.windowTitle() == APP_NAME
    names = [window.tiles.item(i).text() for i in range(window.tiles.count())]
    assert names == ["Nexus Release Tool", "Nexus Demo Recorder", "Nexus Deps", "Nexus Flight Recorder",
                     "Nexus Garbage Remover",
                     "Nexus Installer Tests", "Nexus Marketing for PS5", "Nexus Remix Studio", "Nexus Sound Lab",
                     "Nexus TTS", "Portal video tour", "Apps video tour", "Convert icons", "Close issues"]
    enabled = [bool(window.tiles.item(i).flags() & Qt.ItemFlag.ItemIsEnabled) for i in range(window.tiles.count())]
    assert enabled == [True] * 14
    window.close()


def test_a_click_on_an_app_starts_it_and_says_so(qapp, tmp_path):
    started = []
    window = MainWindow(starter=lambda app: started.append(app.key))
    tiles = {window.tiles.item(i).text(): window.tiles.item(i) for i in range(window.tiles.count())}

    window.click(tiles["Nexus Release Tool"].data(Qt.ItemDataRole.UserRole))
    window.click(tiles["Nexus Installer Tests"].data(Qt.ItemDataRole.UserRole))
    window.click(tiles["Nexus Demo Recorder"].data(Qt.ItemDataRole.UserRole))
    window.click(tiles["Nexus Deps"].data(Qt.ItemDataRole.UserRole))

    assert started == ["nrt", "itests", "demo", "deps"]
    assert "Nexus Release Tool" in window.output.toPlainText() and "started from" in window.output.toPlainText()

    def refuse(app):
        raise OSError("no bash")
    window.starter = refuse
    window.click(tiles["Nexus Release Tool"].data(Qt.ItemDataRole.UserRole))
    assert "could not start (no bash)" in window.output.toPlainText()
    window.close()


def test_a_click_on_a_tool_opens_its_dialog_on_the_suite(qapp, monkeypatch):
    opened = []
    for name in ("PortalTourDialog", "AppsTourDialog", "IconsDialog"):
        monkeypatch.setattr(main_window, name, lambda *args, _name=name: type(
            "Fake", (), {"exec": lambda self: opened.append((_name, args[:-1]))})())
    window = MainWindow()
    tiles = {window.tiles.item(i).text(): window.tiles.item(i) for i in range(window.tiles.count())}
    for name in ("Portal video tour", "Apps video tour", "Convert icons"):
        tile = tiles[name].data(Qt.ItemDataRole.UserRole)
        tile.off = ""                                    # whatever the system: the dialogs are what is tested
        window.click(tile)

    suite = CHECKOUT
    assert opened == [("PortalTourDialog", (suite, window.open_file)), ("AppsTourDialog", (suite, window.open_file)),
                      ("IconsDialog", (CHECKOUT,))]
    window.close()


def test_a_checkout_without_tools_or_apps(qapp, tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "dev").mkdir()
    window = MainWindow(tmp_path)
    assert window.apps == []
    assert [window.tiles.item(i).text() for i in range(window.tiles.count())] == ["Portal video tour",
                                                                                  "Apps video tour", "Convert icons",
                                                                                  "Close issues"]
    assert all(not window.tiles.item(i).flags() & Qt.ItemFlag.ItemIsEnabled for i in range(3))
    assert window.tiles.item(3).flags() & Qt.ItemFlag.ItemIsEnabled          # the repository's
    assert window.local_apps.count() == 0
    window.close()


def test_start_runs_the_apps_script_in_its_folder_with_a_log(tmp_path, monkeypatch):
    app = checkout.DevApp(tmp_path / "x", "nexus-x", "X", None)
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "run.sh").write_text("echo hello $1\n", encoding="utf-8")
    monkeypatch.setattr(checkout, "LOG_DIR", tmp_path / "logs")

    process = checkout.start(app, ("--fix",))
    process.wait(10)

    assert process.returncode == 0
    assert (tmp_path / "logs" / "x.log").read_text(encoding="utf-8") == "hello --fix\n"



def test_a_second_launch_opens_no_window(qapp, monkeypatch):
    """A double-click on the Desktop icon starts the app twice: the second launch hands over to the first."""
    import nexus_dashboard.__main__ as entry
    asked = []
    monkeypatch.setattr(entry, "create_app", lambda *a, **k: qapp)
    monkeypatch.setattr(entry.instance, "already_running", lambda app_id: asked.append(app_id) or True)
    monkeypatch.setattr("sys.argv", ["nexus_dashboard"])
    assert entry.main() == 0 and asked == [entry.APP_ID]


def test_a_click_on_the_header_icon_opens_the_suites_wiki(qapp, monkeypatch):
    opened = []
    monkeypatch.setattr(main_window, "open_url", opened.append)
    window = MainWindow()

    assert window.header.logo.cursor().shape() == Qt.CursorShape.PointingHandCursor
    window.header.logo.clicked.emit()

    assert opened == [SUITE_MANUAL_URL] and window.header.logo.toolTip() == "Open the Bazzite Console Suite's wiki"
    window.close()
