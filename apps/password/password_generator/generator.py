# SPDX-License-Identifier: GPL-3.0-or-later
"""The passwords: 8 or 15 characters with a capital letter, a small letter, a number and a special character.

The rules are the ones the international guidance has in common:

* the lengths are the two of NIST SP 800-63B and the OWASP Application Security Verification Standard: 8
  characters, the minimum, for an account that also has a second sign-in step, and 15 characters where the
  password is the only step;
* the four kinds of characters are the composition rule most sites and company policies ask for;
* the special characters are OWASP's list of password special characters, without the space, so every character is
  printable ASCII and can be typed on any keyboard layout;
* the characters come from the system's cryptographic random source (the standard library's secrets), and every
  password that meets the rules is as likely as any other.

Nothing here writes to a file. A Generator remembers the passwords it made as SHA-256 digests, in memory only, so it
never gives the same one twice while the app runs."""

from __future__ import annotations

import hashlib
import secrets
import string

SHORT, LONG = 8, 15         # with a second sign-in step; where the password is the only step
LENGTHS = (SHORT, LONG)
CAPITALS = string.ascii_uppercase
SMALL = string.ascii_lowercase
NUMBERS = string.digits
SPECIAL = string.punctuation            # OWASP's password special characters without the space
KINDS = (CAPITALS, SMALL, NUMBERS, SPECIAL)
ALPHABET = "".join(KINDS)               # 94 characters: about 51 bits for 8 of them, 98 for 15


def meets_rules(password: str, length: int = SHORT) -> bool:
    """*length* characters of ALPHABET with at least one of every kind."""
    return (len(password) == length and all(c in ALPHABET for c in password)
            and all(any(c in kind for c in password) for kind in KINDS))


def new_password(length: int = SHORT) -> str:
    """A random password of *length* characters that meets the rules. It draws whole passwords until one has every kind, so no position
    is more likely to hold one kind than another."""
    if length not in LENGTHS:
        raise ValueError(f"a password has {SHORT} or {LONG} characters, not {length}")
    while True:
        password = "".join(secrets.choice(ALPHABET) for _ in range(length))
        if meets_rules(password, length):
            return password


class Generator:
    """Passwords that differ from every one it made before."""

    def __init__(self) -> None:
        self._made: set[bytes] = set()

    def new(self, length: int = SHORT) -> str:
        while True:
            password = new_password(length)
            digest = hashlib.sha256(password.encode("ascii")).digest()
            if digest not in self._made:
                self._made.add(digest)
                return password
