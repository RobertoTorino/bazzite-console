# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared fixtures: an offscreen QApplication, settings in a temp folder, and a fake PS5 with the kernel's ps5-cec
adapter and a Xiaomi Mi TV behind it. The cec-ctl output is what the owner's PS5 (CFI-1000A, kernel 7.3.1) printed on
11-11-2026, with the OSD name cec-ctl --playback gives (Playback) instead of the one already set; the other answers
(power status, poll, topology) are the TV's, as recorded earlier with the same TV."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
CORE = Path(__file__).resolve().parents[3] / "core"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))           # bazzite_console_core from the checkout, as the installer bundles it
sys.path.insert(0, str(Path(__file__).resolve().parent))

INFO = """Driver Info:
\tDriver Name                : ps5-cec
\tAdapter Name               : ps5-cec
\tCapabilities               : 0x0000020e
\t\tLogical Addresses
\t\tTransmit
\t\tPassthrough
\t\tReply Vendor ID
\tDriver version             : 7.3.1
\tAvailable Logical Addresses: 1
\tConnector Info             : None
\tPhysical Address           : 1.0.0.0
\tLogical Address Mask       : 0x0010
\tCEC Version                : 2.0
\tVendor ID                  : 0x080046 (Sony)
\tOSD Name                   : 'Playback'
\tLogical Addresses          : 1 (Allow RC Passthrough)

\t  Logical Address          : 4 (Playback Device 1)
\t    Primary Device Type    : Playback
\t    Logical Address Type   : Playback
\t    All Device Types       : Playback
\t    RC TV Profile          : None
\t    Device Features        :
\t\tNone

"""

UNCONFIGURED = (INFO.split("\tLogical Addresses          :")[0]
                .replace("Logical Address Mask       : 0x0010", "Logical Address Mask       : 0x0000")
                + "\tLogical Addresses          : 0 \n")

TOPOLOGY = INFO + "\n\tTopology:\n\n\t    1.0.0.0: Playback Device 1\n"
TOPOLOGY_TV = INFO + "\n\tTopology:\n\n\t    0.0.0.0: TV\n\t        1.0.0.0: Playback Device 1\n"

NACK = """Transmit from Playback Device 1 to TV (4 to 0):
GIVE_DEVICE_POWER_STATUS (0x8f)
\tSequence: 82 Tx Timestamp: 87994.730395s
\tTx, Not Acknowledged (1), Max Retries
"""

POWER_ON = """
Transmit from Playback Device 1 to TV (4 to 0):
GIVE_DEVICE_POWER_STATUS (0x8f)
    Received from TV (0):
    REPORT_POWER_STATUS (0x90):
\tpwr-state: on (0x00)
\tSequence: 126 Tx Timestamp: 89061.825312s Rx Timestamp: 89061.918533s
\tApproximate response time: 21 ms
"""

ACK = """
Transmit from Playback Device 1 to TV (4 to 0):
POLL
\tSequence: 125 Tx Timestamp: 89061.761256s
"""

# The EDID base block of the owner's TV, cut to what the app reads: the header and the monitor name descriptor.
EDID = bytearray(128)
EDID[0:8] = bytes.fromhex("00ffffffffffff00")
EDID[54 + 18 * 3:54 + 18 * 4] = b"\0\0\0\xfc\0" + b"Mi TV\n" + b" " * 7


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def settings_dir(tmp_path, monkeypatch):
    """The app keeps an .ini (AppInfo.settings_ini), so this also keeps the tests out of the Windows registry."""
    from PyQt6.QtCore import QSettings
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    return tmp_path / "settings"


@pytest.fixture
def dev_root(tmp_path) -> Path:
    root = tmp_path / "dev"
    root.mkdir()
    (root / "cec0").touch()
    return root


@pytest.fixture
def sys_root(tmp_path) -> Path:
    root = tmp_path / "sys"
    connector = root / "class/drm/card0-DP-1"          # the PS5's HDMI port, behind its HDMI bridge
    connector.mkdir(parents=True)
    (connector / "edid").write_bytes(bytes(EDID))
    (connector / "status").write_text("connected\n")
    other = root / "class/drm/card0-DP-2"              # the USB-C DP output, nothing on it
    other.mkdir(parents=True)
    (other / "edid").write_bytes(b"")
    (other / "status").write_text("disconnected\n")
    return root


@pytest.fixture
def usr_root(tmp_path) -> Path:
    root = tmp_path / "usr"
    (root / "bin").mkdir(parents=True)
    (root / "bin/cecd").touch()
    return root


@pytest.fixture
def etc_root(tmp_path) -> Path:
    root = tmp_path / "etc"
    root.mkdir()
    return root
