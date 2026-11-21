# SPDX-License-Identifier: GPL-3.0-or-later
"""The quickfixes' windows, offscreen, on folders of their own: what each shows, what its buttons offer (what is on
already cannot be turned on again) and what it asks system.py to do as root."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QMessageBox

from quickfix import runner, state, system, windows

from test_state import put


@pytest.fixture
def root(tmp_path):
    return tmp_path / "root"


@pytest.fixture
def asked():
    """The commands the windows run as root; each answers as a successful pkexec would."""
    calls: list[list[str]] = []

    def run_root(argv):
        calls.append(argv[3:])                  # after pkexec, python, -I: system.py and its arguments
        return runner.Result(0, "")
    run_root.calls = calls
    return run_root


def change(asked) -> list[list[str]]:
    return [argv[1:] for argv in asked.calls]


def test_quickfix_lists_and_installs(qapp, tmp_path, monkeypatch):
    script = put(tmp_path, f"opt/{state.INSTALLER}", "#!/bin/sh\n")
    home = tmp_path / "home"
    tool = put(home, ".local/bin/vkpeak", "#!/bin/sh\n")
    os.chmod(tool, 0o755)
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(state, "BREW_BIN", tmp_path / "brew")
    launched = []
    window = windows.ToolsWindow(launch=launched.append, board_test=tmp_path / "opt", home=home)
    assert window.found_box.value.text() == f"1/{sum(len(g.tools) for g in state.GROUPS) + len(state.BUILT_IN)}"
    assert window.rows["vkpeak"].toolTip() == str(tool)
    assert window.buttons["--bins"].isEnabled()                         # memtest_vulkan is still missing
    assert window.buttons["--bins"].text() == "Binaries" and window.buttons["--bins"].caption.text() == "Install"
    assert window.header.title_row.indexOf(window.refresh_button) > 0   # the symbol, not a pill
    assert window.grid.getItemPosition(window.grid.indexOf(window.buttons["--bins"]))[1] == 0
    assert window.grid.getItemPosition(window.grid.indexOf(window.rows["vkpeak"]))[1] == 1      # beside its pill
    assert window.width() == 900                                        # the exception: its own width
    assert not window.built_in.isEnabled()                              # with Bazzite: nothing to install
    pills = [window.found_box, window.all_button, *window.buttons.values(), window.built_in]
    assert len({pill.minimumWidth() for pill in pills}) == 1            # all as wide as the widest
    window.buttons["--speedtest"].click()
    window.all_button.click()
    assert launched == [f"{script} --speedtest", f"{script} --all"]
    monkeypatch.setattr(state, "installer", lambda board_test=None, checkout=None: None)
    missing = windows.ToolsWindow(launch=launched.append, board_test=tmp_path / "none", home=home)
    assert missing.state.text() == "Board Test not found" and not missing.all_button.isEnabled()


def test_a_switch_is_one_row_of_even_places_with_the_refresh_symbol_in_the_title_row(qapp, tmp_path):
    """Three boxes, Turn on and Turn off fill the row under the title; Refresh is the symbol at the right end of the
    title row, not a pill. With a fourth box the two pills go on a row under the boxes."""
    quickfix = windows.BY_KEY["mapcount"]
    window = windows.SwitchWindow(quickfix, "", ("One", "Two", "Three"), root=tmp_path, home=tmp_path)
    header = window.header
    row = [header.second_row.itemAt(i).widget() for i in range(header.second_row.count())]
    assert row == [*window.boxes.values(), window.on_button, window.off_button, None]       # None: the stretch
    assert header.right.count() == 2 and len({widget.minimumWidth() for widget in row[:5]}) == 1
    assert header.title_row.itemAt(header.title_row.count() - 1).widget() is window.refresh_button
    assert window.width() == window.card_width(window.on_button.minimumWidth())             # no blank on the right
    four = windows.SwitchWindow(quickfix, "", ("One", "Two", "Three", "Four"), root=tmp_path, home=tmp_path)
    assert four.header.right.count() == 3 and four.header.right.itemAt(2).layout().itemAt(0).widget() is four.on_button


def test_mangohud_config_made_and_logging_set(qapp, tmp_path):
    home = tmp_path / "home"
    window = windows.MangoHudWindow(home=home)
    assert window.file_box.value.text() == "New" and window.log_box.value.text() == "Off"
    assert not window.save_button.isEnabled() and window.log_button.isEnabled()
    assert window.revert_button.caption.text() == "Revert changes" and window.clean_button.text() == "Delete logs"
    window.editor.setPlainText("fps\n")
    window.log_button.click()
    assert window.log_box.value.text() == "On" and window.save_button.isEnabled()
    assert not window.log_button.isEnabled()                            # set already
    window.save_button.click()
    conf = home / state.MANGOHUD_CONF
    assert conf.read_text().startswith("fps\n") and f"output_folder={home / 'mangohud-logs'}" in conf.read_text()
    assert (home / "mangohud-logs").is_dir() and window.file_box.value.text() == "There"
    assert window.state.text() == "Saved" and not window.save_button.isEnabled()


def test_mangohud_deletes_only_old_logs(qapp, tmp_path, monkeypatch):
    home = tmp_path / "home"
    old, new = put(home, "mangohud-logs/old.csv"), put(home, "mangohud-logs/new.csv")
    os.utime(old, (1, 1))
    window = windows.MangoHudWindow(home=home)
    assert window.logs_box.value.text() == "2" and window.clean_button.isEnabled()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    window.clean_button.click()
    assert not old.exists() and new.exists() and not window.clean_button.isEnabled()


def test_game_memory_map(qapp, root, asked):
    put(root, "proc/sys/vm/max_map_count", "65530\n")
    window = windows.MapCountWindow(root=root, run_root=asked)
    assert window.state.text() == "Off" and window.on_button.isEnabled()
    window.on_button.click()
    assert change(asked) == [["mapcount", "on"]]
    put(root, "proc/sys/vm/max_map_count", f"{system.MAPCOUNT}\n")
    window.refresh()
    assert window.boxes["Set by"].value.text() == "The system" and not window.on_button.isEnabled()
    assert not window.off_button.isEnabled()                            # the system's: not the quickfix's to undo


def test_persistent_journal_asks_before_it_removes(qapp, root, asked, monkeypatch):
    window = windows.JournalWindow(root=root, run_root=asked)
    assert window.boxes["Journal"].value.text() == "In memory" and window.on_button.isEnabled()
    put(root, f"var/{system.JOURNAL_DIR}/{system.JOURNAL_MARK}")
    window.refresh()
    assert window.boxes["Made by"].value.text() == "This quickfix" and window.off_button.isEnabled()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    window.off_button.click()
    assert change(asked) == []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    window.off_button.click()
    assert change(asked) == [["journal", "off"]]


# A PS5's own cmdline.txt, and a fallback line with a made-up UUID.
LINE = ("root=LABEL=bazzite rw rootwait console=ttyTitania0 console=tty0 video=DP-1:1920x1080@60 mitigations=off "
        "idle=halt preempt=full hdmi.hdcp_mode=2 hdmi.frl_4k120=0\n")
USB = ("root=UUID=00000000-1111-2222-3333-444444444444 rw rootwait console=ttyTitania0 console=tty0 "
       "nvme.max_host_mem_size_mb=0 nvme_core.default_ps_max_latency_us=0\n")


@pytest.fixture
def saving(monkeypatch):
    """What Save asks system.py to write as root: the text of its --text file and the --file it names."""
    calls: list[str] = []

    def run_root(argv):
        if "save" in argv:
            calls.append(Path(argv[argv.index("--text") + 1]).read_text())
            run_root.files.append(argv[argv.index("--file") + 1])
        return runner.Result(0, "")
    run_root.calls = calls
    run_root.files = []
    return run_root


def answer(monkeypatch, button):
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: (asked.append(a[2]), button)[1])
    return asked


def rows(window) -> list[tuple[str, str]]:
    return [(window.table.item(r, 0).text(), window.table.item(r, 1).text()) for r in range(window.table.rowCount())]


def edit(window, row, text) -> None:
    window.table.item(row, windows.ARGUMENT).setText(text)          # as a double click and typing do


def test_boot_command_line_shows_every_argument_with_what_it_does(qapp, root, saving):
    put(root, f"boot/{system.CMDLINE}", LINE)
    window = windows.CmdlineWindow(root=root, run_root=saving)
    shown = rows(window)
    assert [arg for arg, _ in shown] == LINE.split()
    assert all(meaning for _, meaning in shown)                     # every argument of the PS5 line is known
    assert "serial port" in dict(shown)["console=ttyTitania0"] and "screen" in dict(shown)["console=tty0"]
    assert "black picture" in dict(shown)["hdmi.hdcp_mode=2"]
    assert window.state.text() == "Saved" and window.args_box.value.text() == "11"
    assert not window.save_button.isEnabled() and window.line.text() == LINE.strip()
    assert window.file_list.count() == 1 and not window.file_list.isEnabled()
    window.settings_button.click()
    assert "ttm.pages_limit" in window.settings_dialog.findChild(windows.QTextBrowser).toPlainText()
    window.settings_dialog.close()
    assert window.settings_dialog.windowTitle().startswith("Settings")
    assert "<b>The boot partition.</b>" in window.info.text_                      # one info symbol, with both texts
    assert windows.BOOT_PARTITION_URL in window.info.text_                        # the wiki's chapter
    assert not hasattr(window, "partition_info")
    row = [window.header.second_row.itemAt(i).widget() for i in range(5)]         # one row of five even places
    assert row == [window.file_box, window.args_box, window.backups_box, window.read_button, window.save_button]
    assert len({place.minimumWidth() for place in row}) == 1 and window.header.right.count() == 2
    assert window.width() >= window.centralWidget().sizeHint().width()            # the pills under the table fit
    assert window.file_list.minimumWidth() == 280                                 # every file name in full
    captions = {pill.text(): pill.caption.text() for pill in (
        window.read_button, window.save_button, window.add_button, window.remove_button, window.revert_button,
        window.settings_button)}
    assert captions == {"Read": "With password", "Save": "Your changes", "Add": "New row", "Remove": "Selected row",
                        "Revert": "Revert changes", "Settings": "Explain"}
    assert windows.BOOT_PARTITION_URL.endswith("/bazzite-console/boot-partition/")


def test_boot_command_line_edits_adds_moves_and_removes_rows(qapp, root, saving, monkeypatch):
    put(root, f"boot/{system.CMDLINE}", LINE)
    window = windows.CmdlineWindow(root=root, run_root=saving)
    edit(window, 6, "mitigations=auto")
    assert "default" in rows(window)[6][1] and window.state.text() == "Edited, not saved"
    window.table.selectRow(10)
    window.add_row("amd_iommu=off")
    assert rows(window)[11][0] == "amd_iommu=off" and "unstable" in rows(window)[11][1]
    window.up_button.click()
    assert rows(window)[10][0] == "amd_iommu=off" and window.table.currentRow() == 10
    window.table.selectRow(11)
    window.add_row("")
    edit(window, 12, "my.option=1")
    assert rows(window)[12][1] == "Not in the list of known arguments."
    window.table.selectRow(8)                                       # preempt=full
    window.remove_button.click()
    assert "preempt=full" not in window.line.text()
    assert not window.file_list.isEnabled()                         # Save or Revert first
    asked = answer(monkeypatch, QMessageBox.StandardButton.Yes)
    window.save_button.click()
    assert "boot settings of PS5 Linux" in asked[0] and "cmdline.txt?" in asked[0]
    assert saving.calls == [
        "root=LABEL=bazzite rw rootwait console=ttyTitania0 console=tty0 video=DP-1:1920x1080@60 mitigations=auto "
        "idle=halt hdmi.hdcp_mode=2 amd_iommu=off hdmi.frl_4k120=0 my.option=1\n"]
    assert saving.files == ["cmdline.txt"] and "systemctl reboot" in window.note.text()


def test_boot_command_line_opens_the_fallback_lines(qapp, root, saving, monkeypatch):
    put(root, f"boot/{system.CMDLINE}", LINE)
    put(root, "boot/efi/cmdline.txt.usb", USB)
    window = windows.CmdlineWindow(root=root, run_root=saving)
    assert [window.file_list.itemText(i) for i in range(window.file_list.count())] == ["cmdline.txt",
                                                                                         "cmdline.txt.usb"]
    window.file_list.setCurrentText("cmdline.txt.usb")
    assert window.line.text() == USB.strip() and window.args_box.value.text() == "7"
    assert "drop off the bus" in rows(window)[6][1]
    window.table.selectRow(6)
    window.remove_button.click()
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
    window.save_button.click()
    assert saving.files == ["cmdline.txt.usb"] and "copied over" in window.note.text()


def test_boot_command_line_no_drops_the_edits_cancel_keeps_them(qapp, root, saving, monkeypatch):
    put(root, f"boot/{system.CMDLINE}", LINE)
    window = windows.CmdlineWindow(root=root, run_root=saving)
    edit(window, 2, "")
    answer(monkeypatch, QMessageBox.StandardButton.Cancel)
    window.save_button.click()
    assert "rootwait" not in window.line.text() and saving.calls == []
    answer(monkeypatch, QMessageBox.StandardButton.No)
    window.save_button.click()
    assert window.line.text() == LINE.strip() and saving.calls == [] and window.state.text() == "Saved"


def test_boot_command_line_will_not_save_a_line_that_would_not_boot(qapp, root, saving):
    put(root, f"boot/{system.CMDLINE}", LINE)
    window = windows.CmdlineWindow(root=root, run_root=saving)
    window.table.selectRow(0)
    window.remove_button.click()
    assert not window.save_button.isEnabled() and window.state.text() == "Not valid"
    assert "root=" in window.note.text()


def test_boot_command_line_a_failed_save_keeps_the_edits(qapp, root, monkeypatch):
    put(root, f"boot/{system.CMDLINE}", LINE)
    window = windows.CmdlineWindow(root=root, run_root=lambda argv: runner.Result(126, ""))
    window.add_row("amd_iommu=off")
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: shown.append(a[2]))
    window.save_button.click()
    assert shown and "canceled" in shown[0] and window.line.text().endswith("amd_iommu=off")


def test_boot_command_line_reads_a_locked_file_with_the_password(qapp, root, monkeypatch):
    monkeypatch.setattr(state, "cmdline", lambda r, name: state.Cmdline(r / "boot" / system.CMDLINE, None, 0))
    asked = []
    window = windows.CmdlineWindow(root=root, run_root=lambda argv: (asked.append(argv[4:]), runner.Result(0, LINE))[1])
    assert window.file_box.value.text() == "Locked" and window.read_button.isEnabled()
    assert window.state.text() == "Not readable"
    window.read_button.click()
    assert asked == [["cmdline", "show", "--file", "cmdline.txt"]]
    assert window.line.text() == LINE.strip() and window.state.text() == "Saved"


def test_a_canceled_password_says_so(qapp, root, monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: shown.append(a[2]))
    window = windows.MapCountWindow(root=root, run_root=lambda argv: runner.Result(126, ""))
    window.on_button.click()
    assert shown and "canceled" in shown[0]


def test_every_window_says_what_it_does(qapp, root, tmp_path):
    for key, make in windows.WINDOWS.items():
        window = make(root=root, home=tmp_path / "home")
        assert window.windowTitle() == window.quickfix.name and window.info.text_
        assert ("Changes the board" in window.info.text_) == window.quickfix.changes_board, key
        window.close()


def test_the_system_part_runs_from_the_app(tmp_path):
    assert Path(system.__file__).name == "system.py"
    argv = system.command(["journal", "on"])
    assert argv[3] == str(Path(system.__file__).resolve())
