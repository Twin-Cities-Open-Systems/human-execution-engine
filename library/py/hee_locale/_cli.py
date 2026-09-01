"""Entry point for `hee check locale`. Kept thin -- the logic is in the package."""
from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hee_locale import (DEFAULT_LOCALE, build_pattern, load_tool_locales,  # noqa: E402
                        load_variants, scan_line)
from hee_status import Status, emit  # noqa: E402

SKIP = ["docs/history", "*/evidence/*", "man/*", "*.log",
        "library/regex/patterns.yaml", "library/locale/*", "node_modules/*",
        "tooling/bin/hee-check", "library/py/hee_locale/*"]


def main(argv):
    root = argv[0] if argv else "."
    tool_root = os.environ["HEE_TOOL_ROOT"]
    locale = os.environ.get("HEE_LOCALE", DEFAULT_LOCALE)

    variants = load_variants(os.path.join(tool_root, "library", "locale", "en.yaml"))
    if locale not in ("en_US", "en_GB"):
        emit(Status.UNKNOWN, f"HEE_LOCALE={locale} is not in library/locale/en.yaml")
        return 3

    # Provenance for tools whose config vocabulary is another locale. Found,
    # not hardcoded -- and its absence is REPORTED, because a silently
    # skipped exemption is how a false positive comes back.
    prim = os.environ.get("HEE_PRIMITIVES") or os.path.join(
        os.environ.get("HEE_GIT_ROOT", os.path.expanduser("~/git")), "primitives")
    reg = os.path.join(prim, "external.yaml")
    tools = load_tool_locales(reg)

    # Built as a list, never by index surgery. The first version assigned
    # the pattern to args[6] and silently overwrote `-E`, so git rejected the
    # whole invocation and the tool reported "not a git repository" about a
    # repository that was fine.
    words = "|".join(sorted({p[0 if locale == DEFAULT_LOCALE else 1] for p in variants}))
    args = ["git", "-C", root, "grep", "-n", "-I", "-E", f"({words})", "--"]
    args += [f":!{s}" for s in SKIP]
    out = subprocess.run(args, capture_output=True, text=True)
    if out.returncode not in (0, 1):
        emit(Status.UNKNOWN,
             f"git grep failed in {root}: {out.stderr.strip().splitlines()[0] if out.stderr.strip() else 'no output'}")
        return 3

    rx = build_pattern(variants, locale)
    findings = []
    for line in out.stdout.splitlines():
        path, _, rest = line.partition(":")
        lineno, _, text = rest.partition(":")
        f = scan_line(text, path, rx, variants, locale, tools)
        if f:
            findings.append((path, lineno, f, text))

    if not tools:
        emit(Status.WARNING,
             f"no tool-locale provenance at {reg} -- a config vocabulary in "
             "another locale cannot be recognized. Set HEE_PRIMITIVES.")

    if not findings:
        emit(Status.OK, f"locale {locale}: all authored text matches")
        return 0

    for path, lineno, f, text in findings[:20]:
        emit(Status.WARNING,
             f"locale {locale}: {path}:{lineno} '{f.word}' -> '{f.expected}': {text.strip()[:90]}")
    if len(findings) > 20:
        emit(Status.WARNING,
             f"locale {locale}: {len(findings) - 20} more not shown ({len(findings)} total)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
