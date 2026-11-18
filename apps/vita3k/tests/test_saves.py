# SPDX-License-Identifier: GPL-3.0-or-later
"""The saves Vita3K keeps (saves.py) and the Memory cards tab over them (saves_page.py): the saves of every user,
each named after its game's code, export to a .zip and back, a .zip that would write outside the save folder,
delete, and the tab's table and buttons, with nothing changed while Vita3K runs. And the play time Vita3K counts
(userdata.play_times)."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QMessageBox

from vita3k_manager import saves, userdata
from vita3k_manager.saves_page import RUNNING, SavesPage


def make_storage(vita_fs: Path) -> Path:
    """Vita3K's storage with its first user's save folder."""
    (vita_fs / "ux0" / "user" / saves.FIRST_USER / "savedata").mkdir(parents=True)
    return vita_fs


def make_save(vita_fs: Path, name: str, size: int = 2048) -> Path:
    """A save as a game makes it in Vita3K: the game's own files in a folder named after its code."""
    folder = saves.save_folder(vita_fs) / name
    (folder / "data").mkdir(parents=True)
    (folder / "data" / "save.bin").write_bytes(b"x" * size)
    return folder


@pytest.fixture
def storage(tmp_path):
    return make_storage(tmp_path / "storage")


def test_the_saves_are_read_from_their_folders(storage):
    make_save(storage, "PCSB00002")
    make_save(storage, "PCSA00001", 4096)
    (saves.save_folder(storage) / "PCSE00003").mkdir()                          # no files: not a save
    found = saves.find_saves(storage)
    assert [s.name for s in found] == ["PCSA00001", "PCSB00002"]                # by the game's code
    assert found[0].size == 4096 and found[0].label == "PCSA00001" and saves.icon(found[0]) is None
    assert saves.find_saves(storage / "none") == []
    second = storage / "ux0" / "user" / "01" / "savedata" / "PCSF00009"        # another user's: listed too
    second.mkdir(parents=True)
    (second / "save.bin").write_bytes(b"12")
    assert "PCSF00009" in [s.name for s in saves.find_saves(storage)]
    assert saves.save_folder(storage).parent.name == saves.FIRST_USER            # where a save taken in goes
    assert saves.save_folder(storage / "none") == storage / "none" / "ux0" / "user" / "00" / "savedata"


def test_export_and_import_again(storage, tmp_path):
    make_save(storage, "PCSB00002")
    make_save(storage, "PCSA00001")
    target = tmp_path / "out" / "saves.zip"
    target.parent.mkdir()
    assert saves.export_saves(saves.find_saves(storage), target) == f"Exported 2 save(s) to {target}."
    with zipfile.ZipFile(target) as archive:
        assert "PCSB00002/data/save.bin" in archive.namelist() and "PCSA00001/data/save.bin" in archive.namelist()
    assert os.listdir(target.parent) == ["saves.zip"]                           # no work file left
    assert saves.zip_saves(target) == ["PCSA00001", "PCSB00002"]
    other = make_storage(tmp_path / "other")
    old = make_save(other, "PCSB00002")
    (old / "old.bin").write_bytes(b"old")
    assert saves.import_saves(other, target) == "Imported 2 save(s) from saves.zip: PCSA00001, PCSB00002."
    assert [s.name for s in saves.find_saves(other)] == ["PCSA00001", "PCSB00002"]
    assert not (old / "old.bin").exists()                                       # in place of the save that was there
    assert sorted(os.listdir(saves.save_folder(other))) == ["PCSA00001", "PCSB00002"]


def test_what_is_no_save_is_refused(storage, tmp_path):
    text = tmp_path / "notes.zip"
    text.write_text("not a zip")
    with pytest.raises(saves.SaveError, match="could not be read as a .zip"):
        saves.zip_saves(text)
    other = tmp_path / "pictures.zip"
    with zipfile.ZipFile(other, "w") as archive:
        archive.writestr("holiday/photo.png", b"png")
        archive.writestr("save.bin", b"at the top")
    with pytest.raises(saves.SaveError, match="holds no PS Vita save"):
        saves.import_saves(storage, other)
    outside = tmp_path / "outside.zip"
    with zipfile.ZipFile(outside, "w") as archive:
        archive.writestr("PCSB00002/save.bin", b"in")
        archive.writestr("PCSB00002/../../../escaped.txt", b"out")
    with pytest.raises(saves.SaveError, match="outside the save folder"):
        saves.import_saves(storage, outside)
    assert saves.find_saves(storage) == [] and not (tmp_path / "escaped.txt").exists()


def test_the_tab_lists_exports_imports_and_deletes(qapp, storage, tmp_path, monkeypatch):
    make_save(storage, "PCSB00002")
    make_save(storage, "PCSA00001")
    page = SavesPage(lambda: storage, lambda: {"PCSB00002": "Two"}, lambda: False)
    page.show()
    assert [page.table.horizontalHeaderItem(c).text() for c in range(5)] == ["Game", "Save", "Folder", "Size",
                                                                             "Saved"]
    assert [page.table.item(r, 0).text() for r in range(2)] == ["PCSA00001", "Two"]     # the title, else the code
    assert page.table.item(1, 1).text() == "—" and page.table.item(1, 2).text() == "PCSB00002"
    assert page.space.text().startswith("2 save(s), ") and "savedata" in page.hint.text()
    assert not page.export_button.isEnabled() and not page.delete_button.isEnabled() and not page.status.isVisible()
    page.table.selectRow(1)
    assert page.export_button.isEnabled() and page.details.text() == "<b>Two</b>"
    assert page.picture.text() == "No picture"
    page.export_to(page.chosen(), tmp_path / "two")                             # .zip is added to the name
    assert (tmp_path / "two.zip").is_file() and page.status.text().startswith("Exported 1 save(s) to ")
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: (asked.append(a[2]),
                                                                  QMessageBox.StandardButton.No)[1])
    page.import_file(tmp_path / "two.zip")                                      # there already: it asks first
    assert "on the disk already" in asked[0] and page.status.text() == "Nothing was imported."
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    page.table.selectRow(1)
    page.on_delete()
    assert [s.name for s in page.saves] == ["PCSA00001"] and page.status.text() == "Deleted 1 save(s)."
    page.import_file(tmp_path / "two.zip")
    assert [s.name for s in page.saves] == ["PCSA00001", "PCSB00002"]
    page.close()


def test_nothing_is_changed_while_vita3k_runs(qapp, storage, tmp_path):
    make_save(storage, "PCSB00002")
    page = SavesPage(lambda: storage, dict, lambda: True)
    page.table.selectRow(0)
    page.export_to(page.chosen(), tmp_path / "one.zip")                         # reading is fine
    page.delete(page.chosen())
    assert page.status.text() == RUNNING and len(saves.find_saves(storage)) == 1
    saves.delete_saves(saves.find_saves(storage))
    page.import_file(tmp_path / "one.zip")
    assert page.status.text() == RUNNING and saves.find_saves(storage) == []
    page.close()


def test_the_play_time_vita3k_counts(storage):
    assert userdata.play_times(storage) == {}                                   # no time.xml yet
    time_xml = storage / "ux0" / "user" / "time.xml"
    time_xml.write_text('<?xml version="1.0" encoding="utf-8"?>\n<time>\n\t<user id="00">\n'
                        '\t\t<app last-time-used="1795000000" time-used="5400">PCSB00002</app>\n'
                        '\t\t<app last-time-used="1794000000" time-used="65">PCSA00001</app>\n\t</user>\n'
                        '\t<user id="01">\n\t\t<app last-time-used="1796000000" time-used="600">PCSB00002</app>\n'
                        '\t\t<app last-time-used="soon" time-used="1">BROKEN</app>\n\t</user>\n</time>\n')
    assert userdata.play_times(storage) == {"PCSB00002": (6000, 1796000000), "PCSA00001": (65, 1794000000)}
    assert [userdata.played(n) for n in (6000, 65, 40)] == ["1 h 40 min", "1 min 5 s", "40 s"]
    time_xml.write_text("<time><user")
    assert userdata.play_times(storage) == {}                                   # broken: none
