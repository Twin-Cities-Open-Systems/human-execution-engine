"""The executable half of ``hee mail send``.

``tooling/bin/hee-mail`` is POSIX sh, and authenticated, certificate-verified
SMTP submission is past the shell's ceiling by two of the Tool Maturity
Ladder's own graduation signals -- real parsing (MIME headers, address
lists) and untestable-without-spawning-a-process. So the verb parses its
arguments in sh, as every other verb does, and hands them here.

  python3 -m hee_smtp -from ADDR -to ADDR[,ADDR] -subject S [options] < body

The body is read from stdin, so it never appears in ``ps`` and has no length
limit an argument list would impose. The password comes from MAIL_PASSWORD
in the environment for the same reason.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import DEFAULT_HOST, DEFAULT_PORT, SubmitError, build_message, submit


def main(argv=None):
    p = argparse.ArgumentParser(add_help=False, prog="python3 -m hee_smtp")
    p.add_argument("-from", dest="sender", required=True)
    p.add_argument("-to", dest="to", required=True)
    p.add_argument("-subject", dest="subject", required=True)
    p.add_argument("-reply-to", dest="reply_to", default=None)
    p.add_argument("-name", dest="sender_name", default=None)
    p.add_argument("-host", dest="host", default=None)
    p.add_argument("-port", dest="port", default=None)
    p.add_argument("-user", dest="user", default=None)
    p.add_argument("-header", dest="headers", action="append", default=[],
                   help="NAME=VALUE, repeatable")
    p.add_argument("-timeout", dest="timeout", type=int, default=30)
    p.add_argument("-dry-run", dest="dry_run", action="store_true")
    p.add_argument("-json", dest="as_json", action="store_true")
    p.add_argument("-h", "--help", action="store_true")
    a = p.parse_args(argv)
    if a.help:
        print(__doc__)
        return 0

    headers = {}
    for item in a.headers:
        if "=" not in item:
            print(f"❌ CRITICAL -header must be NAME=VALUE, got {item!r}", file=sys.stderr)
            return 3
        name, value = item.split("=", 1)
        headers[name.strip()] = value

    body = sys.stdin.read() if not sys.stdin.isatty() else ""

    try:
        msg = build_message(a.sender, a.to, a.subject, body,
                            reply_to=a.reply_to, sender_name=a.sender_name,
                            headers=headers)
    except ValueError as exc:
        print(f"❌ CRITICAL {exc}", file=sys.stderr)
        return 3

    if a.dry_run:
        # Everything but the socket: the headers that would go, and the
        # envelope. Deliberately prints the body too -- a dry run is the one
        # place someone is checking what a customer would actually receive.
        host = a.host or os.environ.get("HEE_MAIL_HOST") or DEFAULT_HOST
        port = int(a.port or os.environ.get("HEE_MAIL_PORT") or DEFAULT_PORT)
        print(f"would submit to {host}:{port} as {a.user or a.sender}")
        print(msg.as_string())
        return 0

    try:
        sent = submit(msg, host=a.host, port=a.port, user=a.user, timeout=a.timeout)
    except SubmitError as exc:
        print(f"❌ CRITICAL {exc.stage}: {exc.reason}", file=sys.stderr)
        return 2

    if a.as_json:
        print(json.dumps(sent, sort_keys=True))
    else:
        print(f"✅ OK submitted to {', '.join(sent['to'])} via {sent['host']}:{sent['port']} "
              f"as {sent['user']} ({sent['message_id']})")
    return 0


if __name__ == "__main__":   # pragma: no cover -- the entry point itself
    sys.exit(main())
