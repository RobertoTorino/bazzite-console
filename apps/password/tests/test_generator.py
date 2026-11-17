# SPDX-License-Identifier: GPL-3.0-or-later
"""The passwords meet the rules, come from the system's random source and never repeat while the app runs."""

from __future__ import annotations

import string

import pytest

from password_generator import generator
from password_generator.generator import ALPHABET, LENGTHS, LONG, SHORT, SPECIAL, Generator, meets_rules, new_password


def test_the_rules_are_eight_or_fifteen_characters_of_printable_ascii_without_the_space():
    assert (SHORT, LONG) == LENGTHS == (8, 15)
    assert len(ALPHABET) == len(set(ALPHABET)) == 94
    assert set(ALPHABET) == {chr(code) for code in range(33, 127)}
    assert SPECIAL == string.punctuation and " " not in ALPHABET


@pytest.mark.parametrize("length", LENGTHS)
def test_every_password_has_a_capital_a_small_letter_a_number_and_a_special_character(length):
    for _ in range(2000):
        password = new_password(length)
        assert len(password) == length
        assert any(c.isupper() for c in password), password
        assert any(c.islower() for c in password), password
        assert any(c.isdigit() for c in password), password
        assert any(c in SPECIAL for c in password), password
        assert meets_rules(password, length)


def test_meets_rules_refuses_what_lacks_a_kind_a_length_or_a_character():
    assert meets_rules("Ab1!efgh")
    for password in ("ab1!efgh", "AB1!EFGH", "Abc!efgh", "Ab1cefgh", "Ab1!efg", "Ab1!efghi", "Ab1! fgh", "Ab1!éfgh"):
        assert not meets_rules(password), password
    assert meets_rules("Ab1!efghijklmno", LONG) and not meets_rules("Ab1!efghijklmno") and not meets_rules("Ab1!efgh", LONG)


def test_a_password_has_no_other_length():
    assert new_password() and len(new_password()) == SHORT
    for length in (0, 7, 9, 14, 16):
        with pytest.raises(ValueError):
            new_password(length)


def test_the_characters_come_from_secrets(monkeypatch):
    drawn = iter("aaaaaaaa" "Ab1!efgh")                 # the first draw lacks three kinds and is thrown away
    monkeypatch.setattr(generator.secrets, "choice", lambda alphabet: next(drawn))
    assert new_password() == "Ab1!efgh"


def test_every_kind_turns_up_in_every_position():
    seen = [set() for _ in range(LONG)]
    for _ in range(3000):
        for position, c in enumerate(new_password(LONG)):
            seen[position].add("capital" if c.isupper() else "small" if c.islower() else
                               "number" if c.isdigit() else "special")
    assert all(len(kinds) == 4 for kinds in seen)


def test_a_generator_never_gives_the_same_password_twice(monkeypatch):
    made = iter(["Ab1!efgh", "Ab1!efgh", "Ab1!efgh", "Zy9?wvut"])
    monkeypatch.setattr(generator, "new_password", lambda length: next(made))
    passwords = Generator()
    assert passwords.new() == "Ab1!efgh"
    assert passwords.new() == "Zy9?wvut"


def test_a_generator_remembers_digests_not_passwords():
    passwords = Generator()
    password = passwords.new()
    assert len(passwords.new(LONG)) == LONG and len(passwords._made) == 2
    assert all(isinstance(digest, bytes) and len(digest) == 32 for digest in passwords._made)
    assert password.encode() not in passwords._made
