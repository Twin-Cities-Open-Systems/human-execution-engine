"""hee_smtp -- submit one message to a mail exchanger, over an authenticated,
certificate-verified connection.

The tool in ``tooling/bin/hee-mail`` is a thin CLI over this module (``hee
mail send``); everything testable without a network lives here. It exists
because three different things in this fleet had begun to grow their own
submission code -- the mail host's ``flow-check.py``, CI, and now the store
service's order notice -- and each one is a fresh chance to get certificate
verification or credential handling subtly wrong.

**The password is never an argument.** It arrives in the environment as
``MAIL_PASSWORD`` (the convention ``flow-check.py`` already set) or is
passed to :func:`submit` by a caller that read it from there. An argument
is visible in ``ps`` to every user on the box; that is the whole reason.

**TLS is verified, always.** :func:`submit` builds an
``ssl.create_default_context()`` and never lowers it -- no
``check_hostname = False``, no ``CERT_NONE``, no flag to ask for either.
A submission server whose certificate does not verify is a submission
server that might not be ours, and the failure a caller wants there is a
refusal, not a delivery to somewhere else.

Two ports, one behaviour: 587 negotiates STARTTLS on a plain connection,
465 is TLS from the first byte. Both authenticate and both verify. 25 is
refused outright -- it is the port between exchangers, it carries no
credential, and a fleet host reaching for it is nearly always a mistake
that would have worked by accident and then been marked as spam.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid, parseaddr

__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "IMPLICIT_TLS_PORT",
    "SubmitError",
    "build_message",
    "split_addresses",
    "submit",
]

DEFAULT_HOST = "mx1.tcosagent.com"
DEFAULT_PORT = 587          # STARTTLS
IMPLICIT_TLS_PORT = 465     # TLS from the first byte


class SubmitError(RuntimeError):
    """Submission failed. ``reason`` is the real reason, safe to log.

    It never carries the password, and never carries the body: a failure
    that is written to a log must not be a second copy of the message.
    """

    def __init__(self, reason, *, stage="submit"):
        super().__init__(reason)
        self.reason = reason
        self.stage = stage


def split_addresses(value):
    """``"a@x, b@y"`` -> ``["a@x", "b@y"]``. Empty entries are dropped.

    Accepts a list already split, so a caller need not care which it holds.
    Raises ValueError when an entry has no ``@`` -- a local-only address is
    valid in the RFC and useless here, since this module always talks to a
    remote exchanger which would have no idea whose ``root`` was meant.
    """
    if value is None:
        return []
    items = value.split(",") if isinstance(value, str) else list(value)
    out = []
    for item in items:
        addr = parseaddr(str(item).strip())[1].strip()
        if not addr:
            continue
        if "@" not in addr:
            raise ValueError(f"address: {item!r} has no domain -- this module only submits to a remote exchanger")
        out.append(addr)
    return out


def build_message(sender, to, subject, body, *, reply_to=None, sender_name=None,
                  headers=None, date=None, message_id=None):
    """One ``text/plain; charset=utf-8`` message, ready to submit.

    Split out from :func:`submit` so the shape of a message can be tested
    without a socket, which is most of what goes wrong with a notification:
    a missing Date, a Message-ID that is not unique, a subject that grew a
    newline from user input and split the header.

    ``headers`` adds extra headers (``{"X-Store": "wbu"}``); a value
    containing a newline is refused rather than folded, because a folded
    newline from untrusted input is header injection.
    """
    to_list = split_addresses(to)
    if not to_list:
        raise ValueError("to: at least one recipient is required")
    sender_addr = split_addresses(sender)
    if len(sender_addr) != 1:
        raise ValueError("from: exactly one sender address is required")
    sender_addr = sender_addr[0]

    msg = EmailMessage()
    msg["From"] = formataddr((sender_name, sender_addr)) if sender_name else sender_addr
    msg["To"] = ", ".join(to_list)
    # A subject is the field most likely to carry text a stranger typed.
    # Newlines are stripped rather than refused: a customer's order note
    # ending in a newline is not an attack, and failing their order over it
    # would be the wrong trade. Extra headers ARE refused -- nothing that
    # reaches those comes from a stranger.
    msg["Subject"] = " ".join(str(subject).splitlines()).strip() or "(no subject)"
    msg["Date"] = date or formatdate(localtime=False)
    msg["Message-ID"] = message_id or make_msgid(domain=sender_addr.split("@", 1)[1])
    if reply_to:
        msg["Reply-To"] = ", ".join(split_addresses(reply_to))
    for name, value in (headers or {}).items():
        if "\n" in str(value) or "\r" in str(value):
            raise ValueError(f"header {name}: must not contain a newline")
        msg[name] = str(value)
    msg.set_content(body if body is not None else "")
    return msg


def submit(msg, *, host=None, port=None, user=None, password=None, timeout=30):
    """Hand ``msg`` to the exchanger and return the envelope actually sent:
    ``{"host", "port", "user", "from", "to", "message_id"}``.

    Raises :class:`SubmitError` with the stage that failed -- ``connect``,
    ``starttls``, ``auth`` or ``send`` -- so a caller logging one line can
    still say which of the four broke. They fail for entirely different
    reasons and a single "mail failed" hides that.

    ``password`` defaults to ``MAIL_PASSWORD`` in the environment. ``user``
    defaults to the message's From address, which is what a submission
    server almost always wants and what every mailbox this fleet issues
    expects.
    """
    host = host or os.environ.get("HEE_MAIL_HOST") or DEFAULT_HOST
    port = int(port or os.environ.get("HEE_MAIL_PORT") or DEFAULT_PORT)
    if port == 25:
        raise SubmitError(
            "port 25 is the port between exchangers and carries no credential: "
            f"submit on {DEFAULT_PORT} (STARTTLS) or {IMPLICIT_TLS_PORT} (implicit TLS)",
            stage="connect")
    sender = parseaddr(msg["From"])[1]
    user = user or sender
    if password is None:
        password = os.environ.get("MAIL_PASSWORD", "")
    if not password:
        raise SubmitError(
            "no password: set MAIL_PASSWORD in the environment "
            "(hee cred -pass <account> -exec ...), never on the command line",
            stage="auth")

    to_list = split_addresses(msg["To"])
    ctx = ssl.create_default_context()
    try:
        if port == IMPLICIT_TLS_PORT:
            client = smtplib.SMTP_SSL(host, port, timeout=timeout, context=ctx)
        else:
            client = smtplib.SMTP(host, port, timeout=timeout)
    except (OSError, smtplib.SMTPException) as exc:
        raise SubmitError(f"cannot reach {host}:{port}: {exc}", stage="connect") from exc

    try:
        client.ehlo()
        if port != IMPLICIT_TLS_PORT:
            try:
                client.starttls(context=ctx)
                client.ehlo()
            except (OSError, smtplib.SMTPException, ssl.SSLError) as exc:
                raise SubmitError(f"STARTTLS on {host}:{port} failed: {exc}", stage="starttls") from exc
        try:
            client.login(user, password)
        except smtplib.SMTPException as exc:
            # str(exc) on an auth failure is the server's refusal, which
            # names the user but never the password.
            raise SubmitError(f"{host}:{port} refused the credential for {user}: {exc}", stage="auth") from exc
        try:
            client.send_message(msg)
        except smtplib.SMTPException as exc:
            raise SubmitError(f"{host}:{port} refused the message: {exc}", stage="send") from exc
    finally:
        try:
            client.quit()
        except Exception:   # noqa: BLE001, S110 -- deliberate: the message is already accepted by here, and a server that drops the connection before QUIT has still delivered it. Raising would report a delivered message as failed, which is the worse error of the two.
            pass

    return {"host": host, "port": port, "user": user, "from": sender,
            "to": to_list, "message_id": msg["Message-ID"]}


def send(sender, to, subject, body, *, host=None, port=None, user=None,
         password=None, reply_to=None, sender_name=None, headers=None, timeout=30):
    """:func:`build_message` then :func:`submit`, for the common case."""
    msg = build_message(sender, to, subject, body, reply_to=reply_to,
                        sender_name=sender_name, headers=headers)
    return submit(msg, host=host, port=port, user=user, password=password, timeout=timeout)
