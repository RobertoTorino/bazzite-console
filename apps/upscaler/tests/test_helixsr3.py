# SPDX-License-Identifier: GPL-3.0-or-later
"""HelixSR 3 (owner, 20-11-2026: HLX FSR 4 is the default for a game with FSR 3.1): the release's HLX-FSR4 DLL as the
payload, from the zip or the extracted folder, with nothing built; deployed under the game's DLL name with the game's
file kept as *.original.dll, removed again with HLX FSR 4's own files; a HelixSR 2 deployment updated to it; no
stand-alone OptiScaler folder from it."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest import mock

import pytest

from tests.conftest import FAKE_GAME_DLL
from upscaler import acquire, backend
from upscaler.acquire import ReleaseInfo, SetupRequest
from upscaler.backend import HelixError

# HLX FSR 4's DLL as the release has it: its name early in the file, the footer at its end
HLX = b"MZ" + b"\0" * 64 + b"HLX FSR 4 (4.1.2)" + b"\0" * 64 + b"HLXFSR4D" + b"\0" * 16
README_3 = "# HelixSR 3.4.1\n\nHelixSR runs DLSS and FSR 4 upscaling networks...\n"


def release_3(folder: Path, dll: bytes = HLX) -> Path:
    """An extracted HelixSR 3.4.1 release: HLX-FSR4/, the README, the license, HelixSR Scaler's folder."""
    (folder / "HLX-FSR4").mkdir(parents=True)
    (folder / "HLX-FSR4" / backend.HLX_DLL).write_bytes(dll)
    (folder / "HLX-FSR4" / "HLX-FSR4-built.txt").write_text("HLX FSR 4 comes built")
    (folder / "README.md").write_text(README_3)
    (folder / "LICENSE").write_text("license")
    (folder / "helixsr-scaler" / "OptiScaler").mkdir(parents=True)
    (folder / "helixsr-scaler" / "OptiScaler" / backend.HLX_DLL).write_bytes(dll)
    (folder / "HelixSR").mkdir()
    (folder / "HelixSR" / "helixsr.dll").write_bytes(b"MZ helixsr")
    return folder


def zip_3(path: Path, dll: bytes = HLX) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("HelixSR-3.4.1/README.md", README_3)
        zf.writestr("HelixSR-3.4.1/LICENSE", "license")
        zf.writestr(f"HelixSR-3.4.1/helixsr-scaler/OptiScaler/{backend.HLX_DLL}", dll)
        zf.writestr(f"HelixSR-3.4.1/HLX-FSR4/{backend.HLX_DLL}", dll)
        zf.writestr("HelixSR-3.4.1/HelixSR/helixsr.dll", b"MZ helixsr")
        zf.writestr("HelixSR-3.4.1/helixsr-setup.sh", "#!/bin/sh\n")
    path.write_bytes(buf.getvalue())
    return buf.getvalue()


def test_hlx_is_recognized(tmp_path):
    (tmp_path / "hlx.dll").write_bytes(HLX)
    (tmp_path / "footer.dll").write_bytes(b"MZ" + b"\0" * 100 + b"HLXFSR4D" + b"\0" * 16)
    (tmp_path / "game.dll").write_bytes(FAKE_GAME_DLL)
    assert backend.is_hlx(tmp_path / "hlx.dll") and backend.is_hlx(tmp_path / "footer.dll")
    assert not backend.is_hlx(tmp_path / "game.dll") and not backend.is_hlx(tmp_path / "missing.dll")


@pytest.mark.parametrize("kind", ["folder", "zip"])
def test_a_helixsr_3_payload(tmp_path, payload, kind):
    """Imported over a HelixSR 2 payload: HLX FSR 4 and the notices come in, HelixSR's DLL and network files go, the
    user's helixsr.ini template stays."""
    source = release_3(tmp_path / "HelixSR-3.4.1") if kind == "folder" else tmp_path / "HelixSR-3.4.1.zip"
    if kind == "zip":
        zip_3(source)
    result = backend.import_payload(source, payload)
    assert sorted(result.copied) == sorted([backend.HLX_DLL, "README.md", "LICENSE"]) and result.missing == []
    assert not (payload / backend.HELIXSR_DLL).exists() and not (payload / backend.WEIGHTS).exists()
    assert (payload / backend.INI).is_file()
    status = backend.payload_status(payload)
    assert status.hlx and status.ready and status.network_ready and status.missing() == []
    assert status.version == "3.4.1" and backend.payload_dll(payload) == payload / backend.HLX_DLL


def test_a_helixsr_2_payload_again_drops_hlx(tmp_path, release):
    """The fallback (or a 2.x import by hand) makes the payload HelixSR's again."""
    payload = tmp_path / "payload"
    backend.import_payload(release_3(tmp_path / "HelixSR-3.4.1"), payload)
    backend.import_payload(release, payload)
    status = backend.payload_status(payload)
    assert not status.hlx and status.ready and not (payload / backend.HLX_DLL).exists()


def test_a_helixsr_3_release_is_not_an_hlx_one_without_it(tmp_path):
    folder = release_3(tmp_path / "HelixSR-3.4.1", dll=b"MZ not hlx")
    with pytest.raises(HelixError, match="No amd_fidelityfx_dx12.dll"):
        backend.import_payload(folder, tmp_path / "payload")


def test_deploy_and_remove_hlx(tmp_path, game):
    payload = tmp_path / "payload"
    backend.import_payload(release_3(tmp_path / "HelixSR-3.4.1"), payload)
    [dll] = backend.find_game_dlls(game, payload)
    folder = dll.path.parent
    (folder / backend.WEIGHTS).write_bytes(b"left from HelixSR 2")
    (folder / backend.INI).write_text("[Log]\n")
    assert backend.deploy(dll.path, payload, "[Sharpening]\n") == [dll.path]
    assert dll.path.read_bytes() == HLX and dll.original.read_bytes() == FAKE_GAME_DLL
    assert not (folder / backend.WEIGHTS).exists() and not (folder / backend.INI).exists()   # HLX reads neither
    [after] = backend.find_game_dlls(game, payload)
    assert after.deployed and after.matches_payload and after.network_files and not after.restored
    assert after.state == "HelixSR deployed"
    scan = backend.scan_game(game, payload)
    assert scan.state() == ("ok", "HelixSR 3.4.1 installed")
    for name in backend.HLX_FILES:
        (folder / name).write_text("written by HLX FSR 4")
    backend.remove(dll.path, payload)
    assert dll.path.read_bytes() == FAKE_GAME_DLL and not dll.original.exists()
    assert not any((folder / name).exists() for name in backend.HLX_FILES)


def test_a_helixsr_2_deployment_becomes_hlx(tmp_path, payload, game):
    """Deployed with HelixSR 2, the payload then HelixSR 3: the deployment is an older build, and updating it puts HLX
    FSR 4 in its place; the game's own file stays the backup. Removing it still works before and after."""
    [dll] = backend.find_game_dlls(game, payload)
    backend.deploy(dll.path, payload)
    store = backend.DeploymentStore(tmp_path / "deployments.json")
    dep = store.record(dll.path, backend.MODE_REPLACE, "SomeGame", "2.0.0")
    backend.import_payload(release_3(tmp_path / "HelixSR-3.4.1"), payload)
    assert backend.deployment_state(dep, payload) == ("warn", backend.OLDER) and backend.needs_update(dep, payload)
    backend.update_deployment(dep, payload)
    assert dll.path.read_bytes() == HLX and dll.original.read_bytes() == FAKE_GAME_DLL
    assert not (dll.path.parent / backend.WEIGHTS).exists()
    dep.helixsr_version = "3.4.1"
    assert backend.deployment_state(dep, payload) == ("ok", "In place")
    backend.remove(dll.path, payload)
    assert dll.path.read_bytes() == FAKE_GAME_DLL


def test_a_game_that_put_its_file_back_over_hlx(tmp_path, game):
    payload = tmp_path / "payload"
    backend.import_payload(release_3(tmp_path / "HelixSR-3.4.1"), payload)
    [dll] = backend.find_game_dlls(game, payload)
    backend.deploy(dll.path, payload)
    dll.path.write_bytes(FAKE_GAME_DLL + b" updated")              # a game update
    [after] = backend.find_game_dlls(game, payload)
    assert after.restored and after.state == "Game's own DLL again"


def test_no_standalone_folder_from_helixsr_3(tmp_path):
    payload = tmp_path / "payload"
    backend.import_payload(release_3(tmp_path / "HelixSR-3.4.1"), payload)
    with pytest.raises(HelixError, match="HelixSR Scaler"):
        backend.deploy_folder(tmp_path / "HelixSR-folder", payload)
    assert backend.payload_folder(tmp_path / "HelixSR-3.4.1") == tmp_path / "HelixSR-3.4.1" / "HLX-FSR4"


def prepared_3x(tmp_path, build="ok", dll: bytes = HLX):
    """A HelixSR 3.4.1 release zip: HLX FSR 4 built, HLX DLSS's helixsr.dll for the fake builder, HelixSR Scaler and
    the bridge; the same pinned downloads as the 1.x and 2.x tests."""
    from tests.test_acquire import BUILDER_2X, GOOD_SCRIPT, SCRIPT_2X, prepared
    release, dlss = prepared(tmp_path)
    one_x = Path(release.asset_url[len("file://"):])
    buf = io.BytesIO()
    with zipfile.ZipFile(one_x) as old, zipfile.ZipFile(buf, "w") as zf:
        setup_sh = old.read("HelixSR-1.2.0/helixsr-setup.sh").decode().split(GOOD_SCRIPT)[0] + SCRIPT_2X
        pins_py = old.read("HelixSR-1.2.0/setup/helixsr_setup.py").decode()
        builder = BUILDER_2X.replace("out / 'amd_fidelityfx_dx12.dll'", "out / 'helixsr.dll'")
        zf.writestr("HelixSR-3.4.1/helixsr-setup.sh", setup_sh)
        zf.writestr("HelixSR-3.4.1/setup/helixsr_setup.py", pins_py + f"BUILD = {build!r}\n" + builder)
        zf.writestr("HelixSR-3.4.1/setup/helixsr_bridge.py", "print('{}')\n")
        zf.writestr("HelixSR-3.4.1/HelixSR/helixsr.dll", b"MZ helixsr")
        zf.writestr(f"HelixSR-3.4.1/HLX-FSR4/{backend.HLX_DLL}", dll)
        zf.writestr("HelixSR-3.4.1/helixsr-scaler/OptiScaler.dll", b"MZ optiscaler")
        zf.writestr("HelixSR-3.4.1/README.md", README_3)
    archive = tmp_path / "srv" / "HelixSR-3.4.1.zip"
    archive.write_bytes(buf.getvalue())
    return ReleaseInfo("3.4.1", "v3.4.1", "u", "2026-11-17", archive.name, archive.as_uri(), len(buf.getvalue()))


def run_3x(qapp, tmp_path, build="ok", dll: bytes = HLX, vulkan: bool = False):
    import sys
    from tests.test_acquire import run_worker
    from upscaler.acquire import SetupWorker
    release = prepared_3x(tmp_path, build, dll)
    request = SetupRequest(release, tmp_path / "work", tmp_path / "data" / "HelixSR", vulkan=vulkan)
    with mock.patch.object(acquire, "is_immutable_system", return_value=True), \
            mock.patch.object(acquire, "find_wine", return_value="/opt/wine/bin/wine"), \
            mock.patch.object(SetupWorker, "_python", return_value=sys.executable):
        return run_worker(qapp, request)


def test_setup_worker_builds_helixsr_3(qapp, tmp_path):
    """HLX FSR 4 comes built; the builder builds HLX DLSS's network into HelixSR/helixsr.dll, without frame generation.
    The import then has HLX FSR 4 and the release for HelixSR Scaler, ready."""
    outcome, log = run_3x(qapp, tmp_path)
    assert outcome.ok and not outcome.warning, outcome.message
    assert outcome.message.startswith("HelixSR 3.4.1 is built in")
    args = (outcome.release_dir / "args.txt").read_text()
    assert args.split()[0].endswith("/HelixSR") and "--no-fg" in args
    assert any("HelixSR: network=1" in line for line in log)
    payload = tmp_path / "payload"
    backend.import_payload(outcome.release_dir, payload)
    status = backend.payload_status(payload)
    assert status.hlx and status.scaler and backend.scaler_ready(payload)


def test_a_failed_helixsr_3_build_keeps_hlx_fsr_4(qapp, tmp_path):
    outcome, _ = run_3x(qapp, tmp_path, build="fail")
    assert outcome.ok and outcome.message.startswith("HelixSR 3.4.1 is downloaded in")
    assert outcome.warning.startswith("HLX FSR 4 is ready; HLX DLSS's network for HelixSR Scaler was not built")
    payload = tmp_path / "payload"
    backend.import_payload(outcome.release_dir, payload)
    status = backend.payload_status(payload)
    assert status.hlx and status.ready and not status.scaler


def test_setup_worker_refuses_a_helixsr_3_zip_without_hlx(qapp, tmp_path):
    outcome, _ = run_3x(qapp, tmp_path, dll=b"MZ not hlx")
    assert not outcome.ok and "has no HLX FSR 4" in outcome.message


FOOTER = b"HXSRNET1" + (7).to_bytes(8, "little") * 2 + (1).to_bytes(8, "little")


def scaler_payload(tmp_path: Path, built: bool = True) -> Path:
    """A payload with HelixSR 3's release for HelixSR Scaler: the bridge, Scaler's download, HLX DLSS (built or not)."""
    folder = release_3(tmp_path / "HelixSR-3.4.1")
    (folder / "setup").mkdir()
    (folder / backend.BRIDGE).write_text("print('{}')\n")
    (folder / backend.SCALER_PKG / "OptiScaler.dll").write_bytes(b"MZ optiscaler")
    (folder / backend.NGX_DLL).write_bytes(b"MZ helixsr" + (b"weightskernels" + FOOTER if built else b""))
    payload = tmp_path / "payload"
    result = backend.import_payload(folder, payload)
    assert backend.SCALER_RELEASE + "/" in result.copied
    return payload


class Bridge:
    """subprocess.run for the bridge: records the calls, answers with *answer* (JSON) on stdout."""

    def __init__(self, answer: dict | str, code: int = 0, stderr: str = ""):
        self.answer, self.code, self.stderr, self.calls = answer, code, stderr, []

    def __call__(self, argv, **kwargs):
        import json
        import subprocess
        self.calls.append((argv, kwargs))
        out = self.answer if isinstance(self.answer, str) else json.dumps(self.answer)
        return subprocess.CompletedProcess(argv, self.code, "some line\n" + out + "\n", self.stderr)


def test_the_release_for_helixsr_scaler(tmp_path):
    """Kept whole in the payload (hard links where it can), ready once HLX DLSS carries the network."""
    payload = scaler_payload(tmp_path)
    release = backend.scaler_release(payload)
    assert (release / backend.BRIDGE).is_file() and (release / "HLX-FSR4" / backend.HLX_DLL).is_file()
    assert (release / backend.NGX_DLL).stat().st_nlink == 2              # a link to the extracted release
    status = backend.payload_status(payload)
    assert status.hlx and status.scaler and backend.scaler_ready(payload)
    unbuilt = scaler_payload(tmp_path / "unbuilt", built=False)
    assert backend.scaler_available(unbuilt) and not backend.payload_status(unbuilt).scaler


def test_the_release_from_the_zip(tmp_path):
    archive = tmp_path / "HelixSR-3.4.1.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(f"HelixSR-3.4.1/HLX-FSR4/{backend.HLX_DLL}", HLX)
        zf.writestr("HelixSR-3.4.1/README.md", README_3)
        zf.writestr(f"HelixSR-3.4.1/{backend.BRIDGE}", "print('{}')\n")
        zf.writestr(f"HelixSR-3.4.1/{backend.SCALER_PKG}/OptiScaler.dll", b"MZ")
        zf.writestr(f"HelixSR-3.4.1/{backend.NGX_DLL}", b"MZ helixsr")     # not built: the zip as downloaded
    payload = tmp_path / "payload"
    backend.import_payload(archive, payload)
    assert backend.scaler_available(payload) and not backend.scaler_ready(payload)
    assert (backend.scaler_release(payload) / "README.md").read_text() == README_3


def test_a_helixsr_2_payload_has_no_scaler_release(tmp_path, release):
    payload = scaler_payload(tmp_path)
    backend.import_payload(release, payload)
    assert not backend.scaler_release(payload).exists()


def test_helixsr_scaler_through_the_bridge(tmp_path):
    payload = scaler_payload(tmp_path)
    game = tmp_path / "Game"
    bridge = Bridge({"ok": True, "game": {"exe_folder": str(game / "Bin"), "scaler_dll": "dxgi.dll",
                                          "launch_options": None}, "messages": ["HelixSR Scaler installed as dxgi.dll"]})
    answer = backend.scaler_install(game, payload, runner=bridge)
    assert answer["game"]["scaler_dll"] == "dxgi.dll"
    argv, kwargs = bridge.calls[0]
    release = backend.scaler_release(payload)
    assert argv[1:] == ["-I", str(release / backend.BRIDGE), str(release), "install", "--game", str(game),
                        "--way", "scaler", "--scaler", str(release / backend.SCALER_PKG), "--fg", "off"]
    assert kwargs["cwd"] == release and kwargs["timeout"] == backend.BRIDGE_TIMEOUT
    backend.scaler_remove(game, payload, runner=bridge)
    assert bridge.calls[1][0][4:] == ["remove", "--game", str(game)]


def test_the_bridge_says_no(tmp_path):
    payload = scaler_payload(tmp_path)
    with pytest.raises(HelixError, match=r"no game \(\.exe\) found"):
        backend.scaler_install(tmp_path, payload, runner=Bridge({"ok": False, "error": "no game (.exe) found in x"}))
    with pytest.raises(HelixError, match="gave no answer: Traceback"):
        backend.scaler_install(tmp_path, payload, runner=Bridge("not json", 1, "Traceback ..."))
    unbuilt = scaler_payload(tmp_path / "unbuilt", built=False)
    with pytest.raises(HelixError, match="network built"):
        backend.scaler_install(tmp_path, unbuilt, runner=Bridge({"ok": True}))
    with pytest.raises(HelixError, match="HelixSR-Scaler-remove.sh"):
        backend.scaler_remove(tmp_path, tmp_path / "empty", runner=Bridge({"ok": True}))
    # removed, but the bridge does not find a game outside the stores' libraries afterwards
    lost = Bridge({"ok": False, "error": "no game (.exe) found in x"})
    exe = tmp_path / "Game" / "Bin"
    exe.mkdir(parents=True)
    assert backend.scaler_remove(tmp_path / "Game", payload, runner=lost, exe_folder=exe)["ok"]
    (exe / backend.SCALER_RECORD).write_text("name=dxgi.dll\n")
    with pytest.raises(HelixError, match="no game"):                    # still there: it did not work
        backend.scaler_remove(tmp_path / "Game", payload, runner=lost, exe_folder=exe)


def test_a_helixsr_scaler_deployment(tmp_path):
    """Its state from the install record and HLX DLSS in the game; an older build updates through the bridge."""
    payload = scaler_payload(tmp_path)
    game = tmp_path / "Game"
    exe = game / "Bin"
    (exe / "HelixSR").mkdir(parents=True)
    store = backend.DeploymentStore(tmp_path / "deployments.json")
    dep = store.record(game, backend.MODE_SCALER, "Game", "3.4.1")
    dep.target = str(exe)
    store.save()
    assert backend.DeploymentStore(tmp_path / "deployments.json").items[0].target == str(exe)
    assert dep.folder == exe and backend.deployment_state(dep, payload) == ("bad", "Removed")
    (exe / backend.SCALER_RECORD).write_text("name=dxgi.dll\n")
    assert backend.deployment_state(dep, payload) == ("warn", "Network files missing")
    built = backend.scaler_release(payload) / backend.NGX_DLL
    (exe / backend.NGX_DLL).write_bytes(built.read_bytes())
    assert backend.deployment_state(dep, payload) == ("ok", "In place")
    (exe / backend.NGX_DLL).write_bytes(b"MZ older" + FOOTER)
    dep.helixsr_version = "3.3.0"
    assert backend.deployment_state(dep, payload) == ("warn", backend.OLDER) and backend.needs_update(dep, payload)
    bridge = Bridge({"ok": True, "game": {}})
    with mock.patch.object(backend.subprocess, "run", bridge):
        backend.update_deployment(dep, payload)
    assert bridge.calls[0][0][4:6] == ["install", "--game"]


def test_the_deploy_page_with_helixsr_3(qapp):
    """HelixSR Scaler takes the stand-alone folder's place; its Deploy needs the network built and a game folder; the
    helixsr.ini option goes, as HelixSR 3 reads none."""
    from upscaler.pages import DeployPage
    page = DeployPage()
    assert page.mode_scaler.isHidden() and not page.mode_folder.isHidden()
    page.mode_folder.setChecked(True)
    page.set_payload_ready(True, False, True, False)
    assert page.mode() == backend.MODE_REPLACE                          # the folder mode it was in is gone
    assert not page.mode_scaler.isHidden() and page.mode_folder.isHidden() and page.write_ini.isHidden()
    page.mode_scaler.setChecked(True)
    assert page.mode() == backend.MODE_SCALER and not page.scaler_hint.isHidden()
    page.game_path.setText("/games/Some Game")
    assert not page.deploy.isEnabled() and "not built yet" in page.deploy.toolTip()
    page.set_payload_ready(True, False, True, True)
    assert page.deploy.isEnabled() and page.remove.isEnabled()
    page.game_path.setText("")
    assert not page.deploy.isEnabled()
    page.set_payload_ready(True, False, False, False)                   # back to HelixSR 2 (the fallback)
    assert page.mode() == backend.MODE_REPLACE and page.mode_scaler.isHidden() and not page.write_ini.isHidden()


def test_the_native_vulkan_kernels(qapp, tmp_path):
    """An option, off by default (owner, 20-11-2026): --vulkan to HelixSR 3's builder, and the payload says from the
    builder's record whether they were built."""
    outcome, log = run_3x(qapp, tmp_path, vulkan=True)
    assert outcome.ok and "--vulkan" in (outcome.release_dir / "args.txt").read_text().split()
    assert any("with its Vulkan kernels (this takes about twice as long" in line for line in log)
    (tmp_path / "plain").mkdir()
    plain, _ = run_3x(qapp, tmp_path / "plain")
    assert "--vulkan" not in (plain.release_dir / "args.txt").read_text().split()
    payload = scaler_payload(tmp_path / "p")
    assert not backend.payload_status(payload).vulkan                  # no record
    record = backend.scaler_release(payload) / backend.BUILD_RECORD
    record.write_text('{"vulkan": false, "shaders": 120}')
    assert not backend.scaler_vulkan(payload)
    record.write_text('{"vulkan": true, "shaders": 120}')
    assert backend.payload_status(payload).vulkan
    unbuilt = scaler_payload(tmp_path / "u", built=False)
    (backend.scaler_release(unbuilt) / backend.BUILD_RECORD).write_text('{"vulkan": true}')
    assert not backend.scaler_vulkan(unbuilt)                           # no network: nothing to run them with


def test_no_vulkan_for_helixsr_2(qapp, tmp_path):
    """HelixSR 2's builder has no --vulkan: the option leaves its build as it was."""
    import sys
    from tests.test_acquire import prepared_2x, run_worker
    from upscaler.acquire import SetupWorker
    release, _ = prepared_2x(tmp_path)
    request = SetupRequest(release, tmp_path / "work", tmp_path / "data" / "HelixSR", vulkan=True)
    with mock.patch.object(acquire, "is_immutable_system", return_value=True), \
            mock.patch.object(acquire, "find_wine", return_value="/opt/wine/bin/wine"), \
            mock.patch.object(SetupWorker, "_python", return_value=sys.executable):
        outcome, _ = run_worker(qapp, request)
    assert outcome.ok and "--vulkan" not in (outcome.release_dir / "args.txt").read_text().split()


def test_the_vulkan_option_on_the_setup_page(qapp):
    from upscaler.setup_page import SetupPage
    page = SetupPage()
    seen = []
    page.vulkan_changed.connect(seen.append)
    assert not page.vulkan.isChecked()                                 # off by default
    page.set_vulkan(True)
    assert page.vulkan.isChecked() and seen == []                      # restored without a signal
    page.vulkan.setChecked(False)
    assert seen == [False]
