# SPDX-License-Identifier: GPL-3.0-or-later
"""RPCN, RPCS3's online service (github.com/RipleyTom/rpcn; owner, 18-11-2026: as shadPS4 Manager has shadNet):
creating an account on an RPCN server and trying a sign-in, as RPCS3's own client speaks to it
(rpcs3/Emu/NP/rpcn_client.cpp and rpcs3qt/rpcn_settings_dialog.cpp at the build the app brings), and the account in
RPCS3's own files.

RPCS3 signs in by itself when a game starts, with what its files say: rpcn.yml beside config.yml holds the server
(Host), the account's name (NPID), the password as RPCS3 derives it (Password) and the token the server mailed
(Token); config.yml's Net section says whether it signs in at all (Internet enabled: Connected, PSN status: RPCN).

The protocol, over TLS (RPCS3 does not check the server's certificate, and neither does this): the server first
sends ServerInfo (packet type 3, a u32 protocol version, 34). A request is a 15-byte header (packet type u8 0,
command u16, total size u32 with the header, packet number u64; little-endian), then the texts, each ending in a
zero byte. The reply (packet type 1, same command and number) starts with an error code u8 (0: none).

The password never leaves the machine as typed: RPCS3 sends and keeps PBKDF2-HMAC-SHA3-256 of it (its fixed salt,
200,000 rounds) as 64 hex digits, and so does this. Whether RPCS3 is signed in right now only RPCS3 knows; while it
runs, its log says so ("You are now logged in RPCN(name | name)!")."""

from __future__ import annotations

import hashlib
import re
import socket
import ssl
import struct
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import userdata

DEFAULT_HOST = "np.rpcs3.net"                   # RPCS3's own default (rpcn_config.h)
DEFAULT_PORT = 31313
PROTOCOL = 34                                   # RPCN_PROTOCOL_VERSION of the RPCS3 build the app brings
HEADER = struct.Struct("<BHIQ")                 # packet type, command, total size, packet number
REQUEST, REPLY, NOTIFICATION, SERVER_INFO = 0, 1, 2, 3
LOGIN, CREATE, SEND_TOKEN = 0, 2, 4
TIMEOUT = 10                                    # seconds
MAX_PACKET = 1 << 20
NPID = re.compile(r"^[A-Za-z0-9_-]{3,16}$")     # RPCS3's rule (validate_rpcn_username): 3 to 16 of these
TOKEN = re.compile(r"^[0-9A-Z]{16}$")           # as the server mails it (validate_token)
SALT = b"No matter where you go, everybody's connected."
ROUNDS = 200_000
AVATAR = "https://rpcs3.net/cdn/netplay/DefaultAvatar.png"      # as RPCS3's own window sends for a new account
INTERNET, PSN = "Internet enabled", "PSN status"                # config.yml, section Net
CONNECTED, DISCONNECTED, PSN_RPCN = "Connected", "Disconnected", "RPCN"

# The error codes of rpcn_types.h's ErrorType that these two requests can get, as the person using the app needs to
# read them.
ERRORS = {
    1: "the server did not understand the request (another RPCN version?)",
    2: "the server refused the request as invalid",
    3: "the name, password or email is not accepted by the server",
    4: "too many attempts: wait a little and try again",
    5: "the sign-in failed on the server",
    6: "this account is signed in already, elsewhere (a running RPCS3?)",
    7: "there is no account with this name (names are case-sensitive)",
    8: "the password is wrong",
    9: "the token is wrong or missing: it is in the email the server sent when the account was made",
    10: "the server could not create the account",
    11: "this name is taken: choose another",
    12: "the server does not accept email addresses of this provider",
    13: "an account with this email address exists already",
    23: "the server does not allow it",
    24: "the server's database failed: try again later",
    25: "the server could not send its email: try again later",
}

Connect = Callable[[tuple[str, int], float], socket.socket]


class RpcnError(Exception):
    pass


@dataclass(frozen=True)
class Server:
    host: str
    port: int = DEFAULT_PORT

    def __str__(self) -> str:
        return self.host if self.port == DEFAULT_PORT else f"{self.host}:{self.port}"


@dataclass(frozen=True)
class Account:
    """What rpcn.yml says, and whether config.yml has RPCS3 sign in."""
    host: str = DEFAULT_HOST
    npid: str = ""
    password: str = ""                          # derived: 64 hex digits, never the password as typed
    token: str = ""
    on: bool = False

    @property
    def signs_in(self) -> bool:
        return self.on and bool(self.npid and self.password)


def parse_server(text: str) -> Server:
    """"host" or "host:port" (as RPCS3 keeps it in rpcn.yml); the port defaults to RPCN's 31313."""
    text = text.strip()
    host, _, port = text.rpartition(":") if ":" in text else (text, "", str(DEFAULT_PORT))
    if not host or not port.isdigit() or not 0 < int(port) < 65536 or any(c.isspace() for c in host):
        raise RpcnError(f"{text!r} is not a server address like {DEFAULT_HOST}.")
    return Server(host, int(port))


def check_npid(npid: str) -> str:
    """"" when the server takes it as a name, else why not."""
    if not NPID.match(npid):
        return "An RPCN name has 3 to 16 letters, digits, - or _ (no spaces)."
    return ""


def check_token(token: str) -> str:
    """"" for no token or one as the server mails it, else why not."""
    if token and not TOKEN.match(token):
        return "A token has 16 digits and capital letters, as in the email the server sent."
    return ""


def derive_password(password: str) -> str:
    """The password as RPCS3 sends and keeps it (rpcn_settings_dialog.cpp, derive_password): PBKDF2-HMAC-SHA3-256
    with RPCS3's salt, 200,000 rounds, as 64 capital hex digits."""
    return hashlib.pbkdf2_hmac("sha3_256", password.encode(), SALT, ROUNDS).hex().upper()


def is_derived(password: str) -> bool:
    return bool(re.fullmatch(r"[0-9A-F]{64}", password))


def _texts(*texts: str) -> bytes:
    return b"".join(text.encode() + b"\0" for text in texts)


def packet(command: int, number: int, data: bytes) -> bytes:
    return HEADER.pack(REQUEST, command, HEADER.size + len(data), number) + data


def _receive(sock: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise RpcnError("the server closed the connection.")
        data += chunk
    return data


def _read_packet(sock: socket.socket) -> tuple[int, int, int, bytes]:
    kind, command, total, number = HEADER.unpack(_receive(sock, HEADER.size))
    if not HEADER.size <= total <= MAX_PACKET:
        raise RpcnError("the server sent something that is not RPCN.")
    return kind, command, number, _receive(sock, total - HEADER.size)


def _connect(address: tuple[str, int], timeout: float) -> socket.socket:
    """A TLS connection as RPCS3 opens it: TLS 1.2 or newer, the server's certificate not checked (RPCN servers
    use their own; rpcn_client.cpp sets SSL_VERIFY_NONE)."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    plain = socket.create_connection(address, timeout=timeout)
    try:
        return context.wrap_socket(plain, server_hostname=address[0])
    except BaseException:
        plain.close()
        raise


def _greeting(sock: socket.socket, server: Server) -> None:
    """The server's ServerInfo, as RPCS3 checks it before anything else."""
    kind, _command, _number, info = _read_packet(sock)
    if kind != SERVER_INFO or len(info) != 4:
        raise RpcnError(f"{server} is not an RPCN server.")
    version = struct.unpack("<I", info)[0]
    if version != PROTOCOL:
        raise RpcnError(f"{server} speaks another RPCN version than the RPCS3 this app brings ({version}, not "
                        f"{PROTOCOL}).")


@contextmanager
def _connection(server: Server, connect: Connect):
    """A connection that has the server's greeting; network errors as RpcnError with the reason."""
    try:
        with connect((server.host, server.port), TIMEOUT) as sock:
            sock.settimeout(TIMEOUT)
            _greeting(sock, server)
            yield sock
    except socket.timeout as error:
        raise RpcnError(f"{server} did not answer in {TIMEOUT} s.") from error
    except OSError as error:
        reason = getattr(error, "strerror", None) or getattr(error, "reason", None) or str(error)
        raise RpcnError(f"{server} could not be reached: {reason}.") from error


def server_answers(server: Server, connect: Connect = _connect) -> None:
    """Whether the server answers as RPCN, in the version RPCS3 speaks, without signing in. RpcnError with the
    reason when it does not."""
    with _connection(server, connect):
        pass


def request(server: Server, command: int, data: bytes, connect: Connect = _connect) -> int:
    """Sends one request and returns the error code of its reply (0: none). Notifications the server sends in
    between are passed over. RpcnError when the server cannot be reached or does not speak this RPCN."""
    with _connection(server, connect) as sock:
        sock.sendall(packet(command, 1, data))
        while True:
            kind, answer, number, payload = _read_packet(sock)
            if kind == REPLY and answer == command and number == 1:
                if not payload:
                    raise RpcnError("the server's answer was empty.")
                return payload[0]


def explain(error: int) -> str:
    return ERRORS.get(error, f"the server answered with error {error}")


def create_account(server: Server, npid: str, password: str, email: str, connect: Connect = _connect) -> None:
    """A new account (Create: npid, the derived password, the online name, the avatar, the email; RPCS3's own
    window gives the name as the online name too). *password* is the derived one. The server mails the token.
    RpcnError with the reason when the server refuses it."""
    error = request(server, CREATE, _texts(npid, password, npid, AVATAR, email), connect)
    if error:
        raise RpcnError(f"The account was not created: {explain(error)}.")


def try_sign_in(server: Server, npid: str, password: str, token: str, connect: Connect = _connect) -> None:
    """Signs in (Login: npid, the derived password, the token) as RPCS3 would, and closes the connection, which
    signs out again. RpcnError with the reason when it fails."""
    error = request(server, LOGIN, _texts(npid, password, token), connect)
    if error:
        raise RpcnError(f"The sign-in failed: {explain(error)}.")


# What the server answers to a request for the token again, as RPCS3's own window words it (rpcn_settings_dialog.cpp).
RESEND_ERRORS = {
    2: "this server does not check email addresses and needs no token",
    4: "the server mails a token once every 24 hours: try again later",
    5: "the name and password do not belong together",
}


def resend_token(server: Server, npid: str, password: str, connect: Connect = _connect) -> None:
    """Asks the server to mail the account's token again (SendToken: npid, the derived password), as Resend Token
    in RPCS3's own window does. RpcnError with the reason when the server refuses."""
    error = request(server, SEND_TOKEN, _texts(npid, password), connect)
    if error:
        raise RpcnError(f"The token was not sent: {RESEND_ERRORS.get(error) or explain(error)}.")


# --- RPCS3's own files -------------------------------------------------------------------------------------------

def account_path(home: Path) -> Path:
    """rpcn.yml, beside RPCS3's config.yml."""
    return home / "rpcn.yml"


def _config_lines(home: Path) -> list[str]:
    try:
        return (home / "config.yml").read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []


def read_account(home: Path) -> Account:
    """The account RPCS3 has, and whether it signs in with it when a game starts."""
    found = userdata.read_map(account_path(home))
    lines = _config_lines(home)
    on = (userdata.yaml_value(lines, "Net", INTERNET) == CONNECTED
          and userdata.yaml_value(lines, "Net", PSN) == PSN_RPCN)
    return Account(found.get("Host", "") or DEFAULT_HOST, found.get("NPID", ""), found.get("Password", ""),
                   found.get("Token", ""), on)


def _set_top(lines: list[str], key: str, value: str) -> None:
    """One "key: value" line of a flat YAML map set in place, or added at its end."""
    plain = re.fullmatch(r"[A-Za-z0-9._|-]+(?: [A-Za-z0-9._|-]+)*", value)       # as RPCS3 writes these itself
    text = f"{key}: {value if plain else userdata._yaml_string(value)}"
    for n, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            lines[n] = text
            return
    lines.append(text)


def save_account(home: Path, server: Server, npid: str, password: str, token: str, on: bool) -> None:
    """The account into rpcn.yml (every other line as RPCS3 wrote it) and the switch into config.yml: on, RPCS3 is
    connected and signs in to RPCN; off, its PSN status is Disconnected and the rest stays. *password* is the
    derived one. OSError is the caller's; the caller makes sure RPCS3 does not run."""
    path = account_path(home)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        lines = ["Version: 2"]
    for key, value in (("Host", str(server)), ("NPID", npid), ("Password", password), ("Token", token)):
        _set_top(lines, key, value)
    userdata.write_lines(path, lines)
    config = _config_lines(home)
    if on:
        userdata.yaml_set(config, "Net", INTERNET, CONNECTED)
    userdata.yaml_set(config, "Net", PSN, PSN_RPCN if on else DISCONNECTED)
    userdata.write_lines(home / "config.yml", config)


LOGGED_IN = re.compile(r"rpcn: You are now logged in RPCN\(([^ |)]*)")
FAILED = re.compile(r"^·[EF] .*?\brpcn: (.*)$")
LOG_HEAD = 64 << 20                     # RPCS3 signs in when a game starts: the log's first 64 MB hold it


def session(log_path: Path) -> tuple[str, str]:
    """What RPCS3's log of this run says about its RPCN session: ("online", name), ("offline", why) or ("", "")
    when it has not signed in or tried yet."""
    state = ("", "")
    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as log:
            read = 0
            for line in log:
                read += len(line)
                if read > LOG_HEAD:
                    break
                if "rpcn: " not in line:
                    continue
                if match := LOGGED_IN.search(line):
                    state = ("online", match.group(1))
                elif match := FAILED.match(line.rstrip("\n")):
                    state = ("offline", f"RPCS3 says: {match.group(1).rstrip('.!')}")
    except OSError:
        return "", ""
    return state
