#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Installs the Bazzite Console Suite from this checkout, for testing: the portal and PS5 Board Test, as
# portal/install.sh does. The installed portal then installs the other apps from this checkout as well, so keep
# the checkout where it is. Same options as portal/install.sh:
#
#   ./install.sh                         # install or update
#   ./install.sh --no-desktop-shortcut   # app menu entries only, no icons on the Desktop
#   ./install.sh --uninstall             # remove the portal, Board Test and (asked per app) the other apps;
#                                        # keeps settings, results and the wallpaper
#   ./install.sh --uninstall --purge     # also remove settings, history and results
#   ./install.sh --uninstall --all       # the whole suite: every other app too, without a question per app,
#                                        # after one confirmation; with --purge their settings go as well
set -euo pipefail
exec bash "$(dirname "${BASH_SOURCE[0]}")/portal/install.sh" "$@"
