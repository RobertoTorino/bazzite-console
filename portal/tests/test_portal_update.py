# SPDX-License-Identifier: GPL-3.0-or-later
"""What a newer portal release brings: its pins compared with the running portal's."""

from __future__ import annotations

from dataclasses import replace

from bazzite_console_core.updates import ReleaseInfo
from bazzite_console_portal import MANIFEST
from bazzite_console_portal import portal_update as pu
from bazzite_console_portal.manifest import load

RELEASE = ReleaseInfo(version="99.0.0", tag="ps5-portal-v99.0.0", url="https://example.invalid/r", published="2030-01-01")


def bumped(entries, **tags):
    """The shipped entries with some apps moved to other tags."""
    return [replace(e, tag=tags[e.key]) if e.key in tags else e for e in entries]


def text_of(entries) -> str:
    """apps.toml text for *entries*: the shipped file with their tags swapped in."""
    text = MANIFEST.read_text(encoding="utf-8")
    for old, new in zip(load(MANIFEST), entries):
        text = text.replace(f'tag = "{old.tag}"', f'tag = "{new.tag}"')
    return text


def test_compare_names_the_changed_apps():
    current = load(MANIFEST)
    new = bumped(current, fan="ps5-fan-v9.0.0", upscaler="ps5-upscaler-v9.1.0")
    changes = pu.compare(current, new)
    assert [(c.name, c.new) for c in changes] == [("PS5 Upscaler Manager", "9.1.0"),
                                                  ("PS5 Fan Controller", "9.0.0")]
    assert all(c.old for c in changes)
    assert pu.compare(current, current) == []


def test_compare_names_a_withdrawn_app():
    current = load(MANIFEST)
    new = [replace(e, withdrawn="Privacy: shows the account ID.") if e.key == "remoteplay" else e for e in current]
    changes = pu.compare(current, new)
    assert [(c.name, c.withdrawn) for c in changes] == [("Remote Play", "Privacy: shows the account ID.")]
    update = pu.PortalUpdate(RELEASE, changes)
    assert update.summary() == "withdraws Remote Play"
    assert update.details() == ("Remote Play: not available any more (Privacy: shows the account ID.); "
                                "removed from the system")
    assert pu.compare(new, new) == []                       # withdrawn already: nothing new


def test_summary_and_details():
    two = pu.PortalUpdate(RELEASE, [pu.AppChange("PS5 ACE Queues", "0.1.0", "0.1.1"),
                                    pu.AppChange("PS5 Memory Manager", "0.1.0", "0.1.1")])
    assert two.summary() == "updates ACE Queues and Memory Manager"
    assert two.details() == "PS5 ACE Queues: 0.1.0 → 0.1.1\nPS5 Memory Manager: 0.1.0 → 0.1.1"
    many = pu.PortalUpdate(RELEASE, [pu.AppChange(f"PS5 App {i}", "1.0.0", "1.0.1") for i in range(4)]
                           + [pu.AppChange("PS5 New One", "", "0.1.0")])
    assert many.summary() == "updates 4 apps, adds New One"
    assert "PS5 New One: new, 0.1.0" in many.details()
    assert pu.PortalUpdate(RELEASE, []).summary() == pu.PortalUpdate(RELEASE).summary() == ""
    tiled = pu.PortalUpdate(RELEASE, [pu.AppChange("PS5 CEC Manager", "", "0.1.0", "HDMI-CEC")])
    assert tiled.summary() == "adds HDMI-CEC"


def test_check_reads_the_pins_at_the_release_tag():
    current = load(MANIFEST)
    urls = []

    def read(url, _agent):
        urls.append(url)
        return text_of(bumped(current, fan="ps5-fan-v9.0.0"))

    update = pu.check("owner/repo", "portal-v", current, "ua", release_of=lambda *a, **k: RELEASE, read=read)
    assert urls == ["https://raw.githubusercontent.com/owner/repo/ps5-portal-v99.0.0/portal/apps.toml",
                    "https://github.com/owner/repo/releases/download/ps5-portal-v99.0.0/SHA256SUMS"]
    assert update.release is RELEASE and update.summary() == "updates Fan Controller"


def test_check_without_details_or_release():
    current = load(MANIFEST)

    def offline(_url, _agent):
        raise OSError("offline")

    assert pu.check("o/r", "portal-v", current, "ua", release_of=lambda *a, **k: RELEASE, read=offline).changes is None
    assert pu.check("o/r", "portal-v", current, "ua", release_of=lambda *a, **k: RELEASE,
                    read=lambda *_: "not toml [").changes is None
    empty = ReleaseInfo(error="no connection (offline)")
    asked = []
    result = pu.check("o/r", "portal-v", current, "ua", release_of=lambda *a, **k: empty,
                      read=lambda *a: asked.append(a) or "")
    assert result.release is empty and result.changes is None and asked == []


def test_check_reads_the_tarballs_sha256_and_the_running_build(tmp_path):
    """The newest release's SHA256SUMS tells a new build of this version (owner, 03-11-2026); build.sha256 beside
    the program is what this portal came from."""
    sums = "a" * 64 + "  ps5-portal-v99.0.0.tar.gz\n" + "b" * 64 + "  other.tar.gz\n"

    def read(url, user_agent):
        if url.endswith("/SHA256SUMS"):
            return sums
        return text_of(load(MANIFEST))
    update = pu.check("owner/repo", "portal-v", load(MANIFEST), "ua", release_of=lambda *a, **k: RELEASE, read=read)
    assert update.sha256 == "a" * 64 and update.changes == []

    def no_sums(url, user_agent):
        if url.endswith("/SHA256SUMS"):
            raise OSError("offline")
        return text_of(load(MANIFEST))
    assert pu.check("owner/repo", "portal-v", load(MANIFEST), "ua", release_of=lambda *a, **k: RELEASE,
                    read=no_sums).sha256 == ""
    assert pu.running_build(tmp_path) == ""                                   # no file: offered once
    (tmp_path / "suite-checkout").write_text("/a/checkout\n", encoding="utf-8")
    assert pu.running_build(tmp_path) is None                                 # installed from a checkout: never
    (tmp_path / "suite-checkout").unlink()
    (tmp_path / pu.BUILD_FILE).write_text("C" * 64 + "  ps5-portal-v1.0.0.tar.gz\n")
    assert pu.running_build(tmp_path) == "c" * 64
    (tmp_path / pu.BUILD_FILE).write_text("not a checksum\n")
    assert pu.running_build(tmp_path) == ""
