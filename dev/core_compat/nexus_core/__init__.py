# SPDX-License-Identifier: GPL-3.0-or-later
"""Compatibility imports for the Nexus developer apps on Bazzite Console core."""

from bazzite_console_core import AppInfo, SUITE_MANUAL_URL, SUITE_REPO_URL, __version__

from . import appinfo, instance

__all__ = ["AppInfo", "SUITE_MANUAL_URL", "SUITE_REPO_URL", "__version__", "appinfo", "instance"]
