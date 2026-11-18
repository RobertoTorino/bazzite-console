# SPDX-License-Identifier: GPL-3.0-or-later
"""RPCN (rpcn.py) against a fake server: the requests as RPCS3 sends them, the answers and errors, a server that is
not RPCN or another version, the password as RPCS3 derives it, the account in RPCS3's own files, what RPCS3's log
says of its session, and the account window."""

from __future__ import annotations

import hashlib

import pytest
from conftest import FakeRpcn, write_rpcs3_files

from rpcs3_manager import rpcn
from rpcs3_manager.rpcn import RpcnError, Server
from rpcs3_manager.rpcn_dialog import RpcnDialog

SERVER = Server("np.example")
DERIVED = rpcn.derive_password("pässword")


def test_the_password_as_rpcs3_derives_it():
    assert DERIVED == hashlib.pbkdf2_hmac("sha3_256", "pässword".encode(),
                                          b"No matter where you go, everybody's connected.", 200_000).hex().upper()
    assert len(DERIVED) == 64 and rpcn.is_derived(DERIVED) and not rpcn.is_derived("pässword")


def test_create_an_account():
    fake = FakeRpcn()
    rpcn.create_account(SERVER, "Player_1", DERIVED, "me@example.com", connect=fake.connect)
    assert fake.addresses == [("np.example", 31313)]
    # The name is the online name too and the avatar is RPCS3's default, as RPCS3's own window sends them.
    assert fake.requests == [(rpcn.CREATE, ["Player_1", DERIVED, "Player_1", rpcn.AVATAR, "me@example.com"])]


@pytest.mark.parametrize("error, says", [(11, "name is taken"), (12, "this provider"),
                                         (13, "email address exists"), (99, "error 99")])
def test_the_server_refuses_an_account(error, says):
    with pytest.raises(RpcnError, match=says):
        rpcn.create_account(SERVER, "Player_1", DERIVED, "me@example.com", connect=FakeRpcn(error).connect)


def test_try_a_sign_in():
    fake = FakeRpcn()
    rpcn.try_sign_in(SERVER, "Player_1", DERIVED, "0123456789ABCDEF", connect=fake.connect)
    assert fake.requests == [(rpcn.LOGIN, ["Player_1", DERIVED, "0123456789ABCDEF"])]
    with pytest.raises(RpcnError, match="password is wrong"):
        rpcn.try_sign_in(SERVER, "Player_1", DERIVED, "", connect=FakeRpcn(8).connect)
    with pytest.raises(RpcnError, match="token is wrong or missing"):
        rpcn.try_sign_in(SERVER, "Player_1", DERIVED, "", connect=FakeRpcn(9).connect)


def test_the_token_asked_for_again():
    fake = FakeRpcn()
    rpcn.resend_token(SERVER, "Player_1", DERIVED, connect=fake.connect)
    assert fake.requests == [(rpcn.SEND_TOKEN, ["Player_1", DERIVED])]
    for error, says in ((4, "once every 24 hours"), (2, "needs no token"), (5, "do not belong together"),
                        (25, "could not send its email")):
        with pytest.raises(RpcnError, match=f"The token was not sent: .*{says}"):
            rpcn.resend_token(SERVER, "Player_1", DERIVED, connect=FakeRpcn(error).connect)


def test_not_rpcn_another_version_or_no_server():
    with pytest.raises(RpcnError, match="not an RPCN server"):
        rpcn.try_sign_in(SERVER, "Player_1", "x", "", connect=FakeRpcn(first=1).connect)
    with pytest.raises(RpcnError, match="another RPCN version"):
        rpcn.server_answers(SERVER, connect=FakeRpcn(version=33).connect)
    answering = FakeRpcn()
    rpcn.server_answers(SERVER, connect=answering.connect)
    assert answering.requests == []                                             # asked, not signed in

    def refused(address, timeout):
        raise ConnectionRefusedError(111, "Connection refused")
    with pytest.raises(RpcnError, match="could not be reached: Connection refused"):
        rpcn.try_sign_in(SERVER, "Player_1", "x", "", connect=refused)


def test_a_packet_as_rpcs3_builds_it():
    assert rpcn.packet(rpcn.LOGIN, 1, b"a\0b\0\0") == (
        b"\x00" + b"\x00\x00" + (15 + 5).to_bytes(4, "little") + (1).to_bytes(8, "little") + b"a\0b\0\0")


def test_server_address_name_and_token():
    assert rpcn.parse_server("np.rpcs3.net") == Server("np.rpcs3.net", 31313)
    assert rpcn.parse_server(" test-np.rpcs3.net:31314 ") == Server("test-np.rpcs3.net", 31314)
    assert str(Server("np.rpcs3.net")) == "np.rpcs3.net" and str(Server("h", 5)) == "h:5"    # as rpcn.yml keeps it
    for bad in ("", "host:port", "ho st", "host:0", "host:70000"):
        with pytest.raises(RpcnError):
            rpcn.parse_server(bad)
    assert rpcn.check_npid("Player_1") == "" and rpcn.check_npid("ab") and rpcn.check_npid("has space")
    assert rpcn.check_token("") == "" and rpcn.check_token("0123456789ABCDEF") == ""
    assert rpcn.check_token("0123") and rpcn.check_token("0123456789abcdef")


def test_the_account_in_rpcs3s_own_files(tmp_path):
    home = write_rpcs3_files(tmp_path / "rpcs3")
    assert rpcn.read_account(home) == rpcn.Account()                            # no rpcn.yml, no config.yml
    (home / "rpcn.yml").write_text("Version: 2\nHost: np.rpcs3.net\nNPID: \"\"\nPassword: \"\"\nToken: \"\"\n"
                                   "Hosts: Official RPCN Server|np.rpcs3.net\nExperimental IPv6 support: false\n")
    (home / "config.yml").write_text("Core:\n  PPU Decoder: Recompiler (LLVM)\nNet:\n  Internet enabled: "
                                     "Disconnected\n  IP address: 0.0.0.0\n  PSN status: Disconnected\n")
    rpcn.save_account(home, Server("np.rpcs3.net"), "Player_1", DERIVED, "0123456789ABCDEF", True)
    assert (home / "rpcn.yml").read_text() == (
        f"Version: 2\nHost: np.rpcs3.net\nNPID: Player_1\nPassword: {DERIVED}\nToken: 0123456789ABCDEF\n"
        "Hosts: Official RPCN Server|np.rpcs3.net\nExperimental IPv6 support: false\n")       # the rest as it was
    config = (home / "config.yml").read_text()
    assert "  Internet enabled: Connected\n" in config and "  PSN status: RPCN\n" in config
    assert "  IP address: 0.0.0.0\n" in config and "  PPU Decoder: Recompiler (LLVM)\n" in config
    account = rpcn.read_account(home)
    assert account == rpcn.Account("np.rpcs3.net", "Player_1", DERIVED, "0123456789ABCDEF", True)
    assert account.signs_in
    rpcn.save_account(home, Server("np.example", 31314), "Player_1", DERIVED, "", False)
    config = (home / "config.yml").read_text()
    assert "  PSN status: Disconnected\n" in config and "  Internet enabled: Connected\n" in config   # the rest stays
    off = rpcn.read_account(home)
    assert (off.host, off.token, off.on, off.signs_in) == ("np.example:31314", "", False, False)


def test_what_rpcs3s_log_says_of_its_session(tmp_path):
    log = tmp_path / "RPCS3.log"
    assert rpcn.session(log) == ("", "")                                        # no log
    log.write_text("·! 0:00:00.000008 SYS: argc: 1\n·! 0:00:05.1 rpcn: connect: Protocol version matches\n")
    assert rpcn.session(log) == ("", "")
    with log.open("a") as out:
        out.write("·S 0:00:05.4 rpcn: You are now logged in RPCN(Player_1 | Player_1)!\n")
    assert rpcn.session(log) == ("online", "Player_1")
    with log.open("a") as out:
        out.write("·E 0:10:00.0 rpcn: Error receiving data from RPCN!\n")
    assert rpcn.session(log) == ("offline", "RPCS3 says: Error receiving data from RPCN")


def test_the_account_window(qapp, tmp_path):
    """RPCN Account: the account as RPCS3 has it, a sign-in tried with the kept password, an account created with
    the typed one (derived, never as typed), and Save into RPCS3's own files, not while RPCS3 runs."""
    import time
    home = write_rpcs3_files(tmp_path / "rpcs3")
    rpcn.save_account(home, Server("np.rpcs3.net"), "Player_1", DERIVED, "0123456789ABCDEF", False)
    fake, running = FakeRpcn(), [True]
    dialog = RpcnDialog(home, connect=fake.connect, running=lambda: running[0])
    assert (dialog.server.text(), dialog.npid.text(), dialog.token.text()) == ("np.rpcs3.net", "Player_1",
                                                                              "0123456789ABCDEF")
    assert dialog.password.text() == "" and "unchanged" in dialog.password.placeholderText()   # derived: not shown
    assert not dialog.use.isChecked() and dialog.try_button.isEnabled() and not dialog.create_button.isEnabled()

    def wait():
        deadline = time.monotonic() + 10
        while dialog.worker.running and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)
        qapp.processEvents()
    dialog.on_try()
    wait()
    assert fake.requests == [(rpcn.LOGIN, ["Player_1", DERIVED, "0123456789ABCDEF"])]            # the kept password
    assert dialog.result_label.text() == "Player_1 signed in to np.rpcs3.net."
    fake.requests.clear()
    assert dialog.resend_button.text() == "Resend token" and dialog.resend_button.isEnabled()
    dialog.on_resend()
    wait()
    assert fake.requests == [(rpcn.SEND_TOKEN, ["Player_1", DERIVED])]
    assert dialog.result_label.text().startswith("np.rpcs3.net mails the token of Player_1 again")
    fake.requests.clear()
    dialog.npid.setText("New_One")
    dialog.password.setText("secret")
    dialog.email.setText("me@example.com")
    assert dialog.create_button.isEnabled()
    dialog.on_create()
    wait()
    sent = fake.requests[0][1]
    assert sent[:2] == ["New_One", rpcn.derive_password("secret")] and "secret" not in sent
    assert "The server mails a token" in dialog.result_label.text()
    dialog.token.setText("nope")
    dialog.on_save()
    assert "A token has 16" in dialog.result_label.text()
    dialog.token.setText("ABCDEFGH01234567")
    dialog.use.setChecked(True)
    dialog.on_save()
    assert "RPCS3 is running" in dialog.result_label.text() and rpcn.read_account(home).npid == "Player_1"
    running[0] = False
    dialog.on_save()
    assert rpcn.read_account(home) == rpcn.Account("np.rpcs3.net", "New_One", rpcn.derive_password("secret"),
                                                   "ABCDEFGH01234567", True)
    assert "secret" not in (home / "rpcn.yml").read_text() and "me@example.com" not in (home / "rpcn.yml").read_text()
