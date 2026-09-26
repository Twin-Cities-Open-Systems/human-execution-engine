% HEE-TOOLS-CHECK(1) | HEE Tools

# NAME

hee-tools-check - is every external tool this org expects actually here

# SYNOPSIS

    hee-tools-check [MANIFEST]
    hee-tools-check help


# DESCRIPTION


    Reads a whitespace-separated manifest of external tools and reports,
    one line each, whether the tool is on PATH and what version it claims.

    MANIFEST defaults to tooling/tools.manifest.txt resolved relative to
    this script, not to the current directory, so it works from anywhere.
    Blank lines and lines starting with # are skipped. The NAME field (first)
    and the DESIRED-version field (third) are both used.

    Presence is `command -v`. The version string is the first line of
    `<tool> --version`, falling back to `<tool> -V`; if neither works the
    line reads (version-flag-unknown). Nothing is installed, downloaded,
    or modified -- this tool is strictly read-only.

    VERSION ENFORCEMENT. When the DESIRED field is a version (not `any`) and
    the reported version string does not contain it, the line is CRITICAL:
    "wrong version (have X, want Y)". This is why hee-print silently ran the
    distro's Python yq 3.x for days -- the manifest pins `yq 4.50.1`, the tool
    was present at 3.4.3, and presence-only reported OK. A version-flag-unknown
    tool cannot be compared, so it is reported present without enforcement.

    The exit code is the worst status reported, so a script can gate on it;
    each line's LABEL (per vis.status.shfn.bash) says which tool.


# ENVIRONMENT

    HEE_STATUS_STYLE   icon (default), ascii, or plain. See heerc.
    PATH               searched for each manifest tool


# EXIT STATUS

    Nagios plugin convention; the worst line wins.
    0 OK        every manifest tool present at the version it pins
    1 WARNING   an optional tool is missing
    2 CRITICAL  a required tool is missing, or present at the wrong version
    3 UNKNOWN   the MANIFEST cannot be read

    Until 2026-09-11 this tool exited 0 even with a required tool missing, and
    an unreadable MANIFEST exited 2 from the shell. Until 2026-09-26 it checked
    presence only and passed a tool pinned to a version it did not have.


# EXAMPLES

    $ hee tools-check tests/fixtures/tools-manifest/present.txt   # ci


# SEE ALSO

    hee-tools, hee-tools-update, tooling/tools.manifest.txt
