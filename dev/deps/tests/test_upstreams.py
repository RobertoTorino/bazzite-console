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
PAGE = (b'<html><head><meta name="version" content="3.48.0-hotfix-2026.11.0-1.0"><script>{"version":"3.48.0"}'
        b'</script></head><body><h2>PS5 system software update</h2><h3>Version: 26.07</h3><p>Fixes.</p>'
        b'<h3>Version: 26.06</h3></body></html>')


def catalog():
    return upstreams.load()


def entry(key, data=None):
    data = data or catalog()
    return next(item for item in data["sony"] if item["id"] == key)


def test_the_catalog_is_in_sync_with_the_apps():
    """The apps' names and launchers are the portal's: dev/deps/run.sh --sync-upstreams fixes this."""
    assert upstreams.dump(upstreams.sync(catalog())) == CATALOG.read_text(encoding="utf-8")


def test_every_emulator_app_is_listed():
    """Every app with an emulator.py has its card, with its pins read from that file (owner, 28-11-2026)."""
    listed = {item["apps"][0]["app"] for item in catalog()["github"]}
    assert listed == upstreams.emulator_apps() and len(listed) == 7
    for item in catalog()["github"]:
        assert item["compare"] in ("version", "build", "published") and isinstance(item["stable"], bool)
        assert all(item["apps"][0][field] for field in ("repo", "pin", "version", "name", "launcher"))


def test_a_new_pin_makes_the_catalog_stale():
    data = catalog()
    next(item for item in data["github"] if item["id"] == "pcsx2")["apps"][0]["pin"] = "2.0.0"
    assert upstreams.sync(data) == catalog()


def test_newer_by_version_build_and_date():
    assert upstreams.newer("version", {"tag_name": "v2.8.3"}, "2.8.2")
    assert not upstreams.newer("version", {"tag_name": "v.0.21.0"}, "0.21.0")
    assert not upstreams.newer("version", {"tag_name": "v0.0.43"}, "0.0.43")
    assert upstreams.newer("build", {"tag_name": "4460"}, "4377")
    assert not upstreams.newer("build", {"tag_name": "continuous"}, "4377")
    assert upstreams.newer("published", {"published_at": "2026-11-28T02:44:00Z"}, "2026-11-27")
    assert not upstreams.newer("published", {"published_at": "2026-11-27T23:59:00Z"}, "2026-11-27")      # same day
    assert upstreams.newer("published", {"published_at": "2026-11-28T01:06:00Z"}, "2026-11-19T20:05:38Z")


def _github(entry_id):
    return next(item for item in catalog()["github"] if item["id"] == entry_id)


def test_an_emulator_card_compares_the_pin_with_github():
    vita = _github("vita3k")
    pin = vita["apps"][0]["pin"]
    newer_tag = str(int(pin) + 83)
    seen = []
    source = upstreams.check_github(vita, fetch=lambda url: seen.append(url) or {
        "tag_name": newer_tag, "published_at": "2026-11-28T00:00:00Z", "html_url": "https://github.com/x/releases/1"})
    assert seen == [f"https://api.github.com/repos/{vita['apps'][0]['repo']}/releases/latest"]
    assert source.group == "emulators" and source.step is None
    assert [(u.current, u.latest) for u in source.updates] == [(vita["apps"][0]["version"], newer_tag)]
    assert "no stable releases" in source.detail and "after a test on a board" in source.note
    assert 'href="https://github.com/x/releases/1"' in source.about
    pcsx2 = _github("pcsx2")
    same = upstreams.check_github(pcsx2, fetch=lambda url: {"tag_name": "v" + pcsx2["apps"][0]["pin"]})
    assert same.updates == () and "Latest stable on GitHub" in same.detail
    failed = upstreams.check_github(_github("pcsx2"), fetch=lambda url: (_ for _ in ()).throw(OSError("offline")))
    assert failed.error.startswith("GitHub could not be asked") and failed.group == "emulators"


def test_the_reminder_names_a_newer_build_once(tmp_path):
    state = tmp_path / "state.json"
    catalog_ = {"github": [_github("xenia")], "sony": []}
    fetch = lambda url: {"tag_name": "b85977e", "published_at": "2099-01-01T00:00:00Z"}      # noqa: E731
    assert upstreams.read("notified", catalog_, state=state, fetch=fetch)[0].updates
    assert upstreams.read("notified", catalog_, state=state, fetch=fetch)[0].updates == ()
    assert upstreams.read("seen", catalog_, state=state, fetch=fetch)[0].updates                  # the window keeps it


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


def test_the_system_software_pages_give_their_newest_version(tmp_path):
    """The PS5's and the Portal's pages: the first version a person reads, not the site's own numbers."""
    assert upstreams.parse_page(PAGE, "PS5") == {"PS5": "26.07"}
    assert upstreams.parse_page(b"<h3>Version 7.3.2</h3><p>Version 7.3.0</p>", "PlayStation Portal") == {
        "PlayStation Portal": "7.3.2"}
    for bad in (b"<p>No versions here</p>", b'<script>{"Version": "26.08"}</script>', b'<meta version="3.48.0">'):
        try:
            upstreams.parse_page(bad, "PS5")
        except ValueError:
            continue
        raise AssertionError(bad)
    state = tmp_path / "state.json"
    catalog_ = {"sony": [entry("ps5")]}
    first = upstreams.read("seen", catalog_, get=lambda url: PAGE, state=state)
    assert first[0].detail == "Latest: PS5 26.07." and first[0].updates == ()
    newer = PAGE.replace(b"Version: 26.07", b"Version: 26.08")
    assert [(u.current, u.latest) for u in upstreams.read("seen", catalog_, get=lambda url: newer,
                                                          state=state)[0].updates] == [("26.07", "26.08")]


def test_every_card_links_to_sonys_pages():
    for item in catalog()["sony"]:
        source = upstreams.check_sony(item, None, get=lambda url: INFO if url.endswith(".json") else PAGE
                                      if item["kind"] == "page" else PS4)
        assert item["pages"] and all(f'href="{page["url"]}"'.replace("&", "&amp;") in source.about
                                     for page in item["pages"])
        assert all(page["url"].startswith("https://www.playstation.com/") and "srsltid" not in page["url"]
                   for page in item["pages"])