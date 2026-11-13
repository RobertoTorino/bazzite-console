# SPDX-License-Identifier: GPL-3.0-or-later
"""A tab-shaped action that leaves the current page open."""

from PyQt6.QtWidgets import QTabWidget, QWidget

from bazzite_console_core import steam


def shortcut_number(folder, matches):
    for item in steam.shortcuts(folder):
        if matches(item):
            return steam.appid(str(steam.field(item, "Exe")), str(steam.field(item, "AppName")))
    return None


class ActionTab:
    def __init__(self, tabs: QTabWidget, label: str, tooltip: str, action):
        self.tabs = tabs
        self.action = action
        self.previous = tabs.currentIndex()
        self.clicked = False
        self.index = tabs.addTab(QWidget(), label)
        tabs.setTabToolTip(self.index, tooltip)
        tabs.tabBarClicked.connect(self._clicked)
        tabs.currentChanged.connect(self._changed)

    def _clicked(self, index: int) -> None:
        if index == self.index:
            self.clicked = True
            self.action()

    def _changed(self, index: int) -> None:
        if index == self.index:
            if not self.clicked:
                self.action()
            self.clicked = False
            self.tabs.setCurrentIndex(self.previous)
        elif index >= 0:
            self.previous = index
