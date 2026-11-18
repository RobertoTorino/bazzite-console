# SPDX-License-Identifier: GPL-3.0-or-later
"""The RPCN account window (owner, 18-11-2026: as shadPS4 Manager's shadNet window): the account RPCS3 signs in with and
on which server; creating an account, trying a sign-in and asking for the token again (off the GUI thread); saving it
all in RPCS3's own files, from where RPCS3 signs in when a game starts."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QVBoxLayout, QWidget)

from bazzite_console_core import window_title
from bazzite_console_core.updates import UpdateChecker
from bazzite_console_core.widgets import hint_label

from . import rpcn, style, userdata

RPCN_PAGE = "https://wiki.rpcs3.net/index.php?title=Help:Netplay"
KEPT = "unchanged: type a new one to change it"


class RpcnDialog(QDialog):
    def __init__(self, rpcs3_home: Path, parent: QWidget | None = None, connect: rpcn.Connect = rpcn._connect,
                 running=userdata.rpcs3_running):
        """*connect*: opens the connection to the server, *running*: whether RPCS3 runs (tests pass fakes)."""
        super().__init__(parent)
        self.setWindowTitle(window_title("RPCN"))
        self.setMinimumWidth(520)
        self.rpcs3_home = rpcs3_home
        self.account = rpcn.read_account(rpcs3_home)
        self.connect = connect
        self.running = running
        self.worker = UpdateChecker(self)
        self.worker.finished.connect(self._done)

        self.use = QCheckBox("Sign in to RPCN when a game starts")
        self.use.setChecked(self.account.on)
        self.server = QLineEdit(self.account.host)
        self.server.setPlaceholderText(rpcn.DEFAULT_HOST)
        self.npid = QLineEdit(self.account.npid)
        self.npid.setMaxLength(16)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        if self.account.password:                       # RPCS3 keeps it derived: it cannot be shown
            self.password.setPlaceholderText(KEPT)
        self.email = QLineEdit()
        self.email.setPlaceholderText("only to create an account")
        self.token = QLineEdit(self.account.token)
        self.token.setMaxLength(16)
        self.token.setPlaceholderText("from the email the server sends for a new account")
        form = QFormLayout()
        form.addRow("Server", self.server)
        form.addRow("RPCN name", self.npid)
        form.addRow("Password", self.password)
        form.addRow("Email", self.email)
        form.addRow("Token", self.token)

        self.create_button = QPushButton("Create account")
        self.create_button.setToolTip("Create this account on the server (needs the email address): the server "
                                      "mails the token")
        self.create_button.clicked.connect(self.on_create)
        self.try_button = QPushButton("Try sign-in")
        self.try_button.setToolTip("Sign in once to the server with this name, password and token, and out again")
        self.try_button.clicked.connect(self.on_try)
        self.resend_button = QPushButton("Resend token")
        self.resend_button.setToolTip("Have the server mail the token again to the account's email address (once "
                                      "every 24 hours)")
        self.resend_button.clicked.connect(self.on_resend)
        self.save_button = style.primary_button("Save", "Keep these settings in RPCS3's own files")
        self.save_button.clicked.connect(self.on_save)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        for button in (self.create_button, self.try_button, self.resend_button):
            buttons.addWidget(button)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(self.save_button)

        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.addWidget(hint_label(
            "RPCN is RPCS3's online service: online play, friends and scores in the games it supports. RPCS3 signs "
            "in by itself when a game starts. No account yet? Fill in a name, a password and your email, and press "
            "Create account; the server mails a token, which goes in Token. "
            f"{style.link(self, RPCN_PAGE, 'About RPCN')}"))
        lay.addWidget(self.use)
        lay.addLayout(form)
        lay.addWidget(hint_label(
            "The password is kept and sent as RPCS3 does it: scrambled, never as you typed it. The email address is "
            "sent to the server once, to create the account, and is not kept."))
        lay.addWidget(self.result_label)
        lay.addLayout(buttons)
        style.apply(self)

        self.use.toggled.connect(self._update_buttons)
        for field in (self.server, self.npid, self.password, self.email, self.token):
            field.textChanged.connect(self._update_buttons)
        self._update_buttons()

    def _password(self) -> str:
        """The derived password: of what was typed, else the one RPCS3 has."""
        typed = self.password.text()
        return rpcn.derive_password(typed) if typed else self.account.password

    def _has_password(self) -> bool:
        return bool(self.password.text() or self.account.password)

    def _account(self) -> tuple[rpcn.Server, str]:
        """The server and the name, checked; RpcnError with what is wrong."""
        server = rpcn.parse_server(self.server.text() or rpcn.DEFAULT_HOST)
        npid = self.npid.text().strip()
        if why := rpcn.check_npid(npid):
            raise rpcn.RpcnError(why)
        if not self._has_password():
            raise rpcn.RpcnError("Fill in the password.")
        if why := rpcn.check_token(self.token.text().strip()):
            raise rpcn.RpcnError(why)
        return server, npid

    def _update_buttons(self) -> None:
        idle = not self.worker.running
        account = bool(self.npid.text().strip() and self._has_password())
        self.create_button.setEnabled(idle and account and bool(self.password.text())
                                      and bool(self.email.text().strip()))
        self.try_button.setEnabled(idle and account)
        self.resend_button.setEnabled(idle and account)
        self.save_button.setEnabled(idle and (account or not self.use.isChecked()))

    def _say(self, text: str, ok: bool = True) -> None:
        self.result_label.setText(text)
        self.result_label.setStyleSheet("" if ok else "color:#c62828;")

    def _start(self, text: str, job) -> None:
        if self.worker.start(job):
            self._say(text)
            self._update_buttons()

    def _done(self, result: tuple[bool, str]) -> None:
        ok, message = result
        self._say(message, ok)
        self._update_buttons()

    def on_create(self) -> None:
        try:
            server, npid = self._account()
        except rpcn.RpcnError as error:
            self._say(str(error), False)
            return
        typed, email, connect = self.password.text(), self.email.text().strip(), self.connect

        def job() -> tuple[bool, str]:
            try:
                rpcn.create_account(server, npid, rpcn.derive_password(typed), email, connect)
            except rpcn.RpcnError as error:
                return False, str(error)
            return True, (f"The account {npid} was created on {server}. The server mails a token: fill it in under "
                          "Token and press Save.")
        self._start(f"Creating {npid} on {server}…", job)

    def on_try(self) -> None:
        try:
            server, npid = self._account()
        except rpcn.RpcnError as error:
            self._say(str(error), False)
            return
        typed, kept, token, connect = self.password.text(), self.account.password, self.token.text().strip(), \
            self.connect

        def job() -> tuple[bool, str]:
            try:
                rpcn.try_sign_in(server, npid, rpcn.derive_password(typed) if typed else kept, token, connect)
            except rpcn.RpcnError as error:
                return False, str(error)
            return True, f"{npid} signed in to {server}."
        self._start(f"Signing in to {server}…", job)

    def on_resend(self) -> None:
        try:
            server, npid = self._account()
        except rpcn.RpcnError as error:
            self._say(str(error), False)
            return
        typed, kept, connect = self.password.text(), self.account.password, self.connect

        def job() -> tuple[bool, str]:
            try:
                rpcn.resend_token(server, npid, rpcn.derive_password(typed) if typed else kept, connect)
            except rpcn.RpcnError as error:
                return False, str(error)
            return True, f"{server} mails the token of {npid} again: fill it in under Token and press Save."
        self._start(f"Asking {server} for the token…", job)

    def on_save(self) -> None:
        on = self.use.isChecked()
        try:
            server = rpcn.parse_server(self.server.text() or rpcn.DEFAULT_HOST)
            npid = self.npid.text().strip()
            if (on or npid) and (why := rpcn.check_npid(npid)):
                raise rpcn.RpcnError(why)
            if why := rpcn.check_token(self.token.text().strip()):
                raise rpcn.RpcnError(why)
        except rpcn.RpcnError as error:
            self._say(str(error), False)
            return
        if self.running():
            self._say("RPCS3 is running: close it first, as it writes its own settings back when it ends.", False)
            return
        try:
            rpcn.save_account(self.rpcs3_home, server, npid, self._password(), self.token.text().strip(), on)
        except OSError as error:
            self._say(f"RPCS3's files could not be written: {error}", False)
            return
        self.accept()

    def done(self, code: int) -> None:
        self.worker.stop()
        super().done(code)
