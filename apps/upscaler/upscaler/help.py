# SPDX-License-Identifier: GPL-3.0-or-later
"""Help page content: what the app does, its chapter in the wiki and where its files are (owner, 16-11-2026)."""

from __future__ import annotations

from PyQt6.QtWidgets import QTextBrowser, QWidget

from . import APP_NAME, HELIXSR_URL, __version__
from bazzite_console_core import SUITE_MANUAL_URL
from bazzite_console_core.platform import private


def help_html(payload_dir: str, deployments_file: str,
              work_dir: str = "~/.local/share/ps5-upscaler/work") -> str:
    """The Help page. The paths and URLs are filled into the paragraphs afterwards."""
    values = dict(app_name=APP_NAME, version=__version__, helixsr_url=HELIXSR_URL,
                  wiki_url=f"{SUITE_MANUAL_URL}apps/upscaler/", payload_dir=private(payload_dir),
                  deployments_file=private(deployments_file), work_dir=private(work_dir))
    parts = [
        '<h1>{app_name} <small>v{version}</small></h1>',
        ('<p>{app_name} puts <a href="{helixsr_url}">HelixSR</a> into games on <b>Bazzite</b> OS running on '
         'a <b>PS5</b> board. It also keeps track of where it put HelixSR. HelixSR is an FSR 3.1 drop-in upscaler with '
         'DLSS-style neural networks. Games talk to it as FSR 3.1. In a game with FSR 3.1, you choose '
         '<b>AMD FSR</b>.</p>'),
        ('<p>How to use it: <a href="{wiki_url}">{app_name} in the wiki</a>.</p>'),
        '<h2>Where its files are</h2>',
        '<ul>',
        '<li>The payload, your copy of a HelixSR release: <code>{payload_dir}</code></li>',
        '<li>The list of deployed games: <code>{deployments_file}</code></li>',
        ("<li>The downloads: <code>{work_dir}</code> and <code>~/.local/share/HelixSR</code>, the setup script's "
         'own cache</li>'),
        '</ul>',
        ('<p>Removing the app with <code>install.sh --uninstall</code> leaves the payload and the list of deployed '
         'games alone.</p>'),
    ]
    return "\n".join(part.format(**values) for part in parts) + "\n"

class HelpView(QTextBrowser):
    def __init__(self, payload_dir: str, deployments_file: str, work_dir: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setHtml(help_html(payload_dir, deployments_file, work_dir) if work_dir
                     else help_html(payload_dir, deployments_file))
