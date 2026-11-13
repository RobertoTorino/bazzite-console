#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail

libs=(libEGL.so.1 libGL.so.1 libxkbcommon.so.0 libdbus-1.so.3 libfontconfig.so.1 libglib-2.0.so.0)
packages=(libegl1 libgl1 libxkbcommon0 libdbus-1-3 libfontconfig1 libglib2.0-0)
if [ "${1:-}" = --pulse ]; then
    libs+=(libpulse.so.0)
    packages+=(libpulse0)
fi

known=$(ldconfig -p)
missing=()
for lib in "${libs[@]}"; do
    grep -qF -- "$lib (" <<<"$known" || missing+=("$lib")
done
if [ ${#missing[@]} -eq 0 ]; then
    echo "All on the runner already: ${libs[*]}"
    exit 0
fi

echo "Missing: ${missing[*]}; installing them from Ubuntu's mirror"
apt_options=(-o Acquire::Retries=3 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30)
sudo apt-get "${apt_options[@]}" update -q
sudo apt-get "${apt_options[@]}" install -y -q "${packages[@]}"
