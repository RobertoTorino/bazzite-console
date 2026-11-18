# SPDX-License-Identifier: GPL-3.0-or-later
"""The saves shadPS4 keeps (saves.py) and the Memory cards tab over them (saves_page.py): what a save's param.sfo
says, the saves of every user, export to a .zip and back, a .zip that would write outside the save folder, delete,
and the tab's table, picture and buttons, with nothing changed while shadPS4 runs."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QMessageBox

from conftest import make_sfo

from shadps4_manager import saves
from shadps4_manager.saves_page import RUNNING, SavesPage


def _png(size: tuple[int, int], colour: str) -> bytes:
    from PyQt6.QtCore import QBuffer, QByteArray, QIODevice
    from PyQt6.QtGui import QColor, QImage
    image = QImage(*size, QImage.Format.Format_ARGB32)
    image.fill(QColor(colour))
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def make_home(home: Path) -> Path:
    """shadPS4's own folder with its first user's save folder."""
    (home / "home" / saves.FIRST_USER / "savedata").mkdir(parents=True)
    return home


def make_save(home: Path, title_id: str, name: str, title: str = "LUMINES REMASTERED", subtitle: str = "Play Data",
              detail: str = "Play Time: 00:58:30", picture: bool = True) -> Path:
    """A save as shadPS4 0.20 writes it: sce_sys/param.sfo and icon0.png, the data beside sce_sys."""
    folder = saves.save_folder(home) / title_id / name
    (folder / "sce_sys").mkdir(parents=True)
    (folder / "sce_sys" / "param.sfo").write_bytes(make_sfo({"DETAIL": detail, "MAINTITLE": title,
                                                             "SAVEDATA_DIRECTORY": name, "SUBTITLE": subtitle,
                                                             "TITLE_ID": title_id}))
    (folder / "data.bin").write_bytes(b"x" * 2048)
    if picture:
        (folder / "sce_sys" / "icon0.png").write_bytes(_png((228, 128), "#1565c0"))
    return folder


@pytest.fixture
def home(tmp_path):
    return make_home(tmp_path / "shadPS4")


def test_the_saves_are_read_from_their_folders(home):
    make_save(home, "CUSA11624", "autoSaveData", detail="Play\nTime: 00:58:30")
    make_save(home, "CUSA00002", "Slot1", "Alpha", "", "", picture=False)
    (saves.save_folder(home) / "CUSA00003" / "EMPTY").mkdir(parents=True)        # no files: not a save
    found = saves.find_saves(home)
    assert [s.name for s in found] == ["CUSA00002/Slot1", "CUSA11624/autoSaveData"]     # by code, then folder
    lumines = found[1]
    assert (lumines.title, lumines.subtitle, lumines.detail) == ("LUMINES REMASTERED", "Play Data",
                                                                  "Play Time: 00:58:30")
    assert lumines.title_id == "CUSA11624" and lumines.label == "LUMINES REMASTERED · Play Data"
    assert lumines.size > 2048 and found[0].label == "Alpha"
    assert saves.icon(lumines) and saves.icon(found[0]) is None
    assert saves.find_saves(home / "none") == []
    second = home / "home" / "1001" / "savedata" / "CUSA00009" / "Other"          # another user's: listed too
    second.mkdir(parents=True)
    (second / "data.bin").write_bytes(b"12")
    assert "CUSA00009/Other" in [s.name for s in saves.find_saves(home)]
    assert saves.save_folder(home).parent.name == saves.FIRST_USER                # where a save taken in goes
    assert saves.save_folder(home / "none") == home / "none" / "home" / "1000" / "savedata"
    assert [saves.size_text(n) for n in (812, 24 * 1024, 1500000)] == ["812 B", "24 KB", "1.4 MB"]


def test_export_and_import_again(home, tmp_path):
    make_save(home, "CUSA11624", "autoSaveData")
    make_save(home, "CUSA00002", "Slot1", "Alpha", "Slot 1")
    found = saves.find_saves(home)
    target = tmp_path / "out" / "saves.zip"
    target.parent.mkdir()
    assert saves.export_saves(found, target) == f"Exported 2 save(s) to {target}."
    with zipfile.ZipFile(target) as archive:
        names = archive.namelist()
    assert "CUSA11624/autoSaveData/sce_sys/param.sfo" in names and "CUSA00002/Slot1/data.bin" in names
    assert os.listdir(target.parent) == ["saves.zip"]                           # no work file left
    assert saves.zip_saves(target) == ["CUSA00002/Slot1", "CUSA11624/autoSaveData"]
    other = make_home(tmp_path / "other")
    old = make_save(other, "CUSA11624", "autoSaveData", detail="Play Time: 00:00:01")
    (old / "old.bin").write_bytes(b"old")
    message = saves.import_saves(other, target)
    assert message == "Imported 2 save(s) from saves.zip: CUSA00002/Slot1, CUSA11624/autoSaveData."
    again = saves.find_saves(other)
    assert [s.name for s in again] == ["CUSA00002/Slot1", "CUSA11624/autoSaveData"]
    assert again[1].detail == "Play Time: 00:58:30" and not (old / "old.bin").exists()   # in place of the old save
    assert sorted(os.listdir(saves.save_folder(other) / "CUSA11624")) == ["autoSaveData"]   # no work folder left


def test_what_is_no_save_is_refused(home, tmp_path):
    text = tmp_path / "notes.zip"
    text.write_text("not a zip")
    with pytest.raises(saves.SaveError, match="could not be read as a .zip"):
        saves.zip_saves(text)
    flat = tmp_path / "flat.zip"                        # a save's files without the game's code above them
    with zipfile.ZipFile(flat, "w") as archive:
        archive.writestr("Slot1/sce_sys/param.sfo", make_sfo({"MAINTITLE": "Game"}))
        archive.writestr("sce_sys/param.sfo", make_sfo({"MAINTITLE": "Game"}))
    with pytest.raises(saves.SaveError, match="holds no PS4 save"):
        saves.import_saves(home, flat)
    outside = tmp_path / "outside.zip"
    with zipfile.ZipFile(outside, "w") as archive:
        archive.writestr("CUSA00001/SAVE/sce_sys/param.sfo", make_sfo({"MAINTITLE": "Game"}))
        archive.writestr("CUSA00001/SAVE/../../../../escaped.txt", b"out")
    with pytest.raises(saves.SaveError, match="outside the save folder"):
        saves.import_saves(home, outside)
    assert saves.find_saves(home) == [] and not (tmp_path / "escaped.txt").exists()


def test_delete_takes_the_games_folder_with_its_last_save(home):
    make_save(home, "CUSA11624", "autoSaveData")
    make_save(home, "CUSA11624", "Slot2")
    keep = make_save(home, "CUSA00002", "Slot1", "Alpha")
    lumines = [s for s in saves.find_saves(home) if s.title_id == "CUSA11624"]
    assert saves.delete_saves(lumines[:1]) == "Deleted 1 save(s)."
    assert os.listdir(saves.save_folder(home) / "CUSA11624") == ["Slot2"]
    saves.delete_saves(lumines[1:])
    assert os.listdir(saves.save_folder(home)) == [keep.parent.name]


def test_the_tab_lists_the_saves_under_their_games(qapp, home):
    make_save(home, "CUSA11624", "autoSaveData")
    make_save(home, "CUSA00002", "Slot1", "Alpha", "", "", picture=False)
    page = SavesPage(home, lambda: {"CUSA11624": "Lumines Remastered"}, lambda: False)
    page.show()
    assert [page.table.horizontalHeaderItem(c).text() for c in range(5)] == ["Game", "Save", "Folder", "Size",
                                                                             "Saved"]
    assert [page.table.item(r, 0).text() for r in range(2)] == ["CUSA00002", "Lumines Remastered"]
    assert page.table.item(1, 1).text() == "LUMINES REMASTERED · Play Data"
    assert page.table.item(1, 2).text() == "CUSA11624/autoSaveData"
    assert page.space.text().startswith("2 save(s), ") and "savedata" in page.hint.text()
    assert not page.export_button.isEnabled() and not page.delete_button.isEnabled() and not page.side.isVisible()
    page.table.selectRow(1)
    assert page.export_button.isEnabled() and page.delete_button.isEnabled() and page.side.isVisible()
    assert not page.picture.pixmap().isNull()
    assert page.details.text() == "<b>LUMINES REMASTERED · Play Data</b><br>Play Time: 00:58:30"
    page.table.selectRow(0)
    assert page.picture.text() == "No picture" and page.details.text() == "<b>Alpha</b>"
    page.close()


def test_the_tab_exports_imports_and_deletes(qapp, home, tmp_path, monkeypatch):
    make_save(home, "CUSA11624", "autoSaveData")
    page = SavesPage(home, dict, lambda: False)
    page.table.selectRow(0)
    page.export_to(page.chosen(), tmp_path / "one")                             # .zip is added to the name
    assert (tmp_path / "one.zip").is_file() and page.status.text().startswith("Exported 1 save(s) to ")
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: (asked.append(a[2]),
                                                                  QMessageBox.StandardButton.No)[1])
    page.import_file(tmp_path / "one.zip")                                      # there already: it asks first
    assert "on the disk already" in asked[0] and page.status.text() == "Nothing was imported."
    page.on_delete()
    assert "export it first" in asked[1] and len(page.saves) == 1               # No: nothing deleted
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    page.table.selectRow(0)
    page.on_delete()
    assert page.saves == [] and page.status.text() == "Deleted 1 save(s)." and page.space.text() == "No saves yet"
    page.import_file(tmp_path / "one.zip")
    assert [s.name for s in page.saves] == ["CUSA11624/autoSaveData"] and page.table.rowCount() == 1
    page.import_file(tmp_path / "none.zip")
    assert "could not be read as a .zip" in page.status.text() and "c62828" in page.status.styleSheet()
    page.close()


def test_nothing_is_changed_while_shadps4_runs(qapp, home, tmp_path):
    make_save(home, "CUSA11624", "autoSaveData")
    page = SavesPage(home, dict, lambda: True)
    page.table.selectRow(0)
    page.export_to(page.chosen(), tmp_path / "one.zip")                         # reading is fine
    page.delete(page.chosen())
    assert page.status.text() == RUNNING and len(saves.find_saves(home)) == 1
    saves.delete_saves(saves.find_saves(home))
    page.import_file(tmp_path / "one.zip")
    assert page.status.text() == RUNNING and saves.find_saves(home) == []
    page.close()
