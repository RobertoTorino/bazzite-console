# SPDX-License-Identifier: GPL-3.0-or-later
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QTabWidget, QWidget

from xenia_manager import action_tab


def test_action_keeps_the_current_page(qapp):
    tabs = QTabWidget()
    tabs.addTab(QWidget(), "Games")
    tabs.addTab(QWidget(), "Settings")
    calls = []
    tab = action_tab.ActionTab(tabs, "Start", "Launch in Steam", lambda: calls.append(True))
    tabs.setCurrentIndex(1)
    tabs.tabBarClicked.emit(tab.index)
    tabs.setCurrentIndex(tab.index)
    assert tabs.currentIndex() == 1 and calls == [True]
    tabs.setCurrentIndex(tab.index)
    assert tabs.currentIndex() == 1 and calls == [True, True]


def test_shortcut_number_uses_actual_stored_name_and_exe(monkeypatch, tmp_path):
    items = [{"exe": '"/path/run"', "appname": "Renamed", "id": 1}]
    monkeypatch.setattr(action_tab.steam, "shortcuts", lambda folder: items)
    assert action_tab.shortcut_number(tmp_path, lambda item: item["id"] == 1) == (
        action_tab.steam.appid('"/path/run"', "Renamed")
    )
    assert action_tab.shortcut_number(tmp_path, lambda item: False) is None


def test_real_tab_click_runs_once(qapp):
    tabs = QTabWidget()
    tabs.addTab(QWidget(), "Games")
    calls = []
    tab = action_tab.ActionTab(tabs, "Start", "Launch in Steam", lambda: calls.append(True))
    tabs.show()
    QTest.mouseClick(tabs.tabBar(), Qt.MouseButton.LeftButton, pos=tabs.tabBar().tabRect(tab.index).center())
    assert tabs.currentIndex() == 0 and calls == [True]
