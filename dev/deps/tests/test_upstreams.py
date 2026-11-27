# SPDX-License-Identifier: GPL-3.0-or-later
"""catalogs/upstreams.json in sync with the apps, and the cards of Sony's firmware from Sony's answers (as they were
on 09-11-2026)."""

from __future__ import annotations

import json

from nexus_deps import upstreams
from nexus_deps.upstreams import CATALOG

INFO = json.dumps({"ApplicationLatestVersion": "2.2.1.2", "FwUpdate0004LatestVersion": "0x0630",
                   "FwUpdate000BLatestVersion": "0x0630", "FwUpdate000ELatestVersion": "0x0641",
                   "FwUpdate0044LatestVersion": "0x0217"}).encode()
PS4 = (b'<?xml version="1.0" ?>\n<update_data_list>\n\t<region id="us">\n\t\t<system_pup ex_version="0" '
       b'label="14.02" sdk_version="14.020.001" version="14.020.000">\n\t\t</system_pup>\n\t</region>\n'
       b'</update_data_list>\n')


def catalog():
    return upstreams.load()


def entry(key, data=None):
    data = data or catalog()
    return next(item for item in data["sony"] if item["id"] == key)


def test_the_catalog_is_in_sync_with_the_apps():
    """The apps' names and launchers are the portal's: dev/deps/run.sh --sync-upstreams fixes this."""
    assert upstreams.dump(upstreams.sync(catalog())) == CATALOG.read_text(encoding="utf-8")


def test_no_emulator_is_listed():
    """Each emulator app chooses its version from GitHub's list itself (owner, 28-11-2026)."""
    assert "github" not in catalog()


def test_a_renamed_app_makes_the_catalog_stale():
    data = catalog()
    entry("dualsense", data)["apps"][0]["name"] = "Old name"
    assert upstreams.sync(data) != data
    assert entry("dualsense", upstreams.sync(data))["apps"][0]["name"] == entry("dualsense")["apps"][0]["name"]


def test_sonys_firmware_is_news_once(tmp_path):
    """The first look learns the versions; a later one names what changed; the one after says nothing again."""
    state = tmp_path / "state.json"
    catalog_ = {"sony": [entry("dualsense"), entry("ps4")]}
    first = upstreams.read("seen", catalog_, get=lambda url: INFO if url.endswith(".json") else PS4, state=state)
    assert all(source.updates == () for source in first)
    assert first[0].detail.startswith("Latest: DualSense (0x0004) 0x0630") and first[1].detail == "Latest: PS4 14.02."
    newer_info = INFO.replace(b'"0x0217"', b'"0x0218"')
    second = upstreams.read("seen", catalog_, get=lambda url: newer_info if url.endswith(".json") else PS4,
                            state=state)
    assert [(u.name, u.current, u.latest) for u in second[0].updates] == [("DualSense Edge (0x0044)", "0x0217",
                                                                          "0x0218")]
    assert "USB cable" in second[0].note and second[0].manual
    third = upstreams.read("seen", catalog_, get=lambda url: newer_info if url.endswith(".json") else PS4,
                           state=state)
    assert third[0].updates == ()
    # The reminder keeps its own memory: the window's look does not use up its news
    assert upstreams.read("notified", catalog_, get=lambda url: newer_info if url.endswith(".json") else PS4,
                          state=state)[0].updates == ()                    # its first look


def test_the_ps4_list_is_read_by_its_one_attribute():
    assert upstreams.parse_ps4(PS4) == {"PS4": "14.02"}
    for bad in (b"<x/>", b'<system_pup label="14.02; rm -rf"/>', b"<!DOCTYPE x [<!ENTITY a 'b'>]><x>&a;</x>"):
        try:
            upstreams.parse_ps4(bad)
        except ValueError:
            continue
        raise AssertionError(bad)


def test_devices_with_no_list_say_where_to_look():
    for key in ("ps5", "psportal"):
        source = upstreams.check_sony(entry(key), None, get=lambda url: (_ for _ in ()).throw(AssertionError(url)))
        assert not source.checked and "System Software" in source.about and source.updates == ()

