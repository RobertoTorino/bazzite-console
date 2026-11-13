# SPDX-License-Identifier: GPL-3.0-or-later
"""MkDocs hook: the disclaimer shown in the Bazzite Console manual.

It sets config.extra.disclaimer, which a template shows with {{ config.extra.disclaimer }} (the footer of each
home page), and puts the text in place of a line that is only MARKER in a page's Markdown."""

from __future__ import annotations

DISCLAIMER = (
    "Bazzite Console is an independent community project, not affiliated with or endorsed by AMD, ASRock, the "
    "Bazzite / Universal Blue project, Sony, Microsoft, Valve, or the makers of the emulators and the other "
    "programs the apps work with. Bazzite is developed by the Universal Blue project. "
    "PlayStation, PS4, PS5, PS3, PS2, PSP, PS Vita, PSN, DualSense and Remote Play are Sony's; XBOX, XBOX 360, XBOX "
    "Cloud Gaming, Game Pass and Windows are Microsoft's; Steam, Steam Deck and Big Picture are Valve's; the names of "
    "the emulators (shadPS4, RPCS3, PPSSPP, PCSX2, Vita3K, and Xenia) belong to their owners. "
    "The project uses their names only to say what its apps work with."
)
MARKER = "<!-- disclaimer -->"


def on_config(config):
    config.extra["disclaimer"] = DISCLAIMER
    return config


def on_page_markdown(markdown, page, config, files):
    return "\n".join(DISCLAIMER if line.strip() == MARKER else line for line in markdown.split("\n"))
