"""hee_smtp -- the message shape and the refusals, without a socket.

Everything here is a thing that has gone wrong in a real mail feature
somewhere: a header split by user input, a password on the command line, a
certificate check switched off "for now", a fleet host quietly submitting
on port 25 and being filed as spam.
"""
import os
import sys
from email.utils import parseaddr

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "library", "py"))

from hee_smtp import (
    DEFAULT_PORT,
    SubmitError,
    build_message,
    split_addresses,
    submit,
)


def test_split_addresses_takes_a_string_or_a_list():
    assert split_addresses("a@x.test, b@y.test") == ["a@x.test", "b@y.test"]
    assert split_addresses(["a@x.test", " b@y.test "]) == ["a@x.test", "b@y.test"]
    assert split_addresses(None) == []
    assert split_addresses("") == []


def test_split_addresses_unwraps_a_display_name():
    assert split_addresses("WBU orders <store@tcos.app>") == ["store@tcos.app"]


def test_split_addresses_refuses_a_local_only_address():
    # Valid in the RFC, useless here: this module always talks to a remote
    # exchanger, which has no idea whose "root" was meant.
    with pytest.raises(ValueError, match="no domain"):
        split_addresses("root")


def test_build_message_sets_the_headers_that_get_forgotten():
    msg = build_message("store@tcos.app", "orders@tcos.app", "hi", "body")
    assert msg["Date"]                       # a message with no Date sorts wrong everywhere
    assert msg["Message-ID"].endswith("@tcos.app>")
    assert msg.get_content_type() == "text/plain"
    assert msg.get_content_charset() == "utf-8"
    assert msg.get_content().strip() == "body"


def test_a_newline_in_the_subject_cannot_split_the_header():
    # The subject is the field most likely to carry text a stranger typed.
    msg = build_message("a@x.test", "b@y.test", "order 1\nBcc: attacker@evil.test", "b")
    assert msg["Subject"] == "order 1 Bcc: attacker@evil.test"
    assert msg["Bcc"] is None


def test_a_newline_in_an_extra_header_is_refused_rather_than_folded():
    # Nothing that reaches -header comes from a stranger, so this is a
    # refusal rather than the subject's strip-and-carry-on.
    with pytest.raises(ValueError, match="newline"):
        build_message("a@x.test", "b@y.test", "s", "b", headers={"X-Order": "1\nBcc: e@evil.test"})


def test_an_empty_subject_becomes_something_rather_than_nothing():
    assert build_message("a@x.test", "b@y.test", "   ", "b")["Subject"] == "(no subject)"


def test_a_display_name_is_quoted_properly():
    msg = build_message("store@tcos.app", "b@y.test", "s", "b", sender_name="WBU, the shop")
    assert parseaddr(msg["From"])[1] == "store@tcos.app"
    assert "WBU, the shop" in msg["From"]


def test_no_recipient_and_no_sender_are_both_refused():
    with pytest.raises(ValueError, match="recipient"):
        build_message("a@x.test", "", "s", "b")
    with pytest.raises(ValueError, match="exactly one sender"):
        build_message("a@x.test, b@y.test", "c@z.test", "s", "b")


def test_port_25_is_refused_before_any_socket_is_opened(monkeypatch):
    # 25 carries no credential. A fleet host reaching for it is nearly always
    # a mistake that would deliver by accident and then be filed as spam.
    monkeypatch.setenv("MAIL_PASSWORD", "x")
    msg = build_message("a@x.test", "b@y.test", "s", "b")
    with pytest.raises(SubmitError) as e:
        submit(msg, host="mx1.invalid", port=25)
    assert e.value.stage == "connect"
    assert "port 25" in e.value.reason


def test_no_password_is_refused_before_any_socket_is_opened(monkeypatch):
    monkeypatch.delenv("MAIL_PASSWORD", raising=False)
    msg = build_message("a@x.test", "b@y.test", "s", "b")
    with pytest.raises(SubmitError) as e:
        submit(msg, host="mx1.invalid", port=DEFAULT_PORT)
    assert e.value.stage == "auth"
    assert "MAIL_PASSWORD" in e.value.reason
    assert "command line" in e.value.reason


def test_an_unreachable_host_fails_at_connect_and_says_so(monkeypatch):
    monkeypatch.setenv("MAIL_PASSWORD", "x")
    msg = build_message("a@x.test", "b@y.test", "s", "b")
    with pytest.raises(SubmitError) as e:
        submit(msg, host="mx1.invalid.invalid", port=DEFAULT_PORT, timeout=2)
    # The four stages fail for entirely different reasons; a single
    # "mail failed" hides which one, and they need different fixes.
    assert e.value.stage == "connect"


def test_the_error_never_carries_the_password_or_the_body(monkeypatch):
    monkeypatch.setenv("MAIL_PASSWORD", "hunter2-the-real-password")
    msg = build_message("a@x.test", "b@y.test", "s", "the body of the message")
    with pytest.raises(SubmitError) as e:
        submit(msg, host="mx1.invalid.invalid", port=DEFAULT_PORT, timeout=2)
    assert "hunter2" not in str(e.value)
    assert "the body of the message" not in str(e.value)
