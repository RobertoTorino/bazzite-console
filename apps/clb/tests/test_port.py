# SPDX-License-Identifier: GPL-3.0-or-later
"""Target identity, keyboard behavior and installer lifecycle."""

import os
from pathlib import Path
import subprocess

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QDialog, QWidget

from console_linkb import APP_ID, INFO, ROOT, __version__, auth, exit_keys


def test_target_identity_and_account_path(tmp_path):
    assert APP_ID == "ps5-xbox-remoteplay"
    assert __version__ == (ROOT / "VERSION").read_text().strip()         # the number is the release's, not the test's
    assert INFO.tag_prefix == "ps5-clb-v"
    assert auth.account_file() == tmp_path / "config" / APP_ID / "account.json"


def test_escape_leaves_stream_and_dialog_to_handle_their_keys(qapp):
    handler = exit_keys.install(qapp)
    window = QWidget()
    window.show()
    QTest.keyClick(window, Qt.Key.Key_Escape)
    assert not window.isVisible()

    stream = QWidget()
    stream.exit_keys = False
    stream.show()
    QTest.keyClick(stream, Qt.Key.Key_Escape)
    assert stream.isVisible()
    stream.close()

    dialog = QDialog()
    dialog.show()
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    assert not dialog.isVisible()
    qapp.removeEventFilter(handler)
    handler.deleteLater()


def test_installer_private_venv_and_uninstall(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python = bin_dir / "python3"
    python.write_text("""#!/bin/sh
if [ "$1" = "-m" ] && [ "$2" = "venv" ]; then
    mkdir -p "$3/bin"
    printf '#!/bin/sh\\nexit 0\\n' > "$3/bin/python"
    chmod +x "$3/bin/python"
fi
exit 0
""")
    python.chmod(0o755)
    identity = bin_dir / "id"
    identity.write_text("#!/bin/sh\nprintf '1000\\n'\n")
    identity.chmod(0o755)
    env = os.environ | {
        "HOME": str(home), "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "XDG_DATA_HOME": str(home / "data"), "XDG_CONFIG_HOME": str(home / "config"),
    }

    def run(*args):
        return subprocess.run(["bash", str(ROOT / "install.sh"), *args], env=env, text=True,
                              capture_output=True, check=True)

    result = run("--no-desktop-shortcut")
    data = home / "data" / APP_ID
    assert (data / "app" / "bazzite_console_core" / "__init__.py").is_file()
    assert (data / "venv" / "bin" / "python").is_file()
    assert "No XBOX Remote Play icon" not in result.stdout
    launcher = (home / ".local" / "bin" / APP_ID).read_text()
    assert str(data / "venv" / "bin" / "python") in launcher
    assert "-m console_linkb" in launcher
    desktop = (home / "data" / "applications" / f"{APP_ID}.desktop").read_text()
    assert f"Icon={data}/app/images/ps5-xbox-remoteplay-128.png" in desktop
    config = home / "config" / APP_ID
    config.mkdir(parents=True)
    (config / "account.json").write_text("private")
    run("--uninstall")
    assert (config / "account.json").is_file()
    assert not (data / "venv").exists()
    run("--uninstall", "--purge")
    assert not config.exists()
