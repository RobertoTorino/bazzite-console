# SPDX-License-Identifier: GPL-3.0-or-later
from bazzite_console_core.theme import Theme

INK = "#010101"
MAIN = "#0f0f0f"
SILVER = "#c0c0c0"
TEAL = "#17b6a7"
EDGE = "#66808080"
NEXUS = Theme("Nexus", True, window=INK, base=MAIN, alt=INK, text=SILVER, button=MAIN,
              button_low=INK, edge=EDGE, accent=TEAL, accent_text=INK)

__all__ = ["EDGE", "INK", "MAIN", "NEXUS", "SILVER", "TEAL"]
