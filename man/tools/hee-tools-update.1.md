% HEE-TOOLS-UPDATE(1) | HEE Tools

# NAME

hee-tools-update - install or refresh the pinned external toolchain

# SYNOPSIS

    hee-tools-update [MANIFEST] [LOG_DIR]
    hee-tools-update help


# DESCRIPTION


    Walks the toolchain manifest and acts on each entry according to its
    `kind` column. This tool WRITES to the filesystem and DOWNLOADS from
    the network -- it is the mutating half of the pair; hee-tools-check is
    the read-only half.

    MANIFEST defaults to tooling/tools.manifest.txt resolved relative to
    this script, so it works from any directory.

    LOG_DIR defaults to $XDG_STATE_HOME/hee/tools (that is
    ~/.local/state/hee/tools unless XDG_STATE_HOME is set). A run log
    records what got installed on THIS machine at one moment -- host
    state, not repo content -- and XDG_STATE_HOME is the directory the
    spec reserves for exactly that.

    It used to default to the RELATIVE path hee/evidence/tools, which
    landed the log wherever you happened to be standing. Run from a repo
    root -- the documented way -- that dirtied the worktree, and
    ci/git/hee-preflight.sh is a hard gate that refuses a dirty worktree.
    So a SUCCESSFUL toolchain update blocked the next session's entry
    until someone cleaned up after it. Real, and it happened
    (issue:501@human-execution-engine).

    Pass LOG_DIR explicitly if you do want the log inside a repo.

    Manifest lines are `name kind desired`. Blank lines and # comments are
    skipped. Handled kinds, and only these:

      go tar <version>    downloads https://go.dev/dl/go<version>.linux-amd64.tar.gz,
                          records its sha256 in the log, wipes and re-extracts
                          $HOME/.local/go/<version>, then symlinks go and gofmt
                          into $HOME/.local/bin. Always reinstalls -- there is no
                          "already at this version" short-circuit for go.
      yq bin <version>    compares `yq --version` against <version> and, only if
                          they differ (or yq is absent), downloads the
                          mikefarah/yq linux_amd64 release binary and moves it
                          into $HOME/.local/bin/yq (via a temp file, so a failed
                          download never leaves a truncated yq on PATH ahead of
                          the distro's Python yq).
      <name> pkg <any>    reports presence only and prints an apt hint. NEVER
                          installs anything. Recognized for jq, bat, glow, rg
                          and tmux by name; any other name:kind pair is logged
                          as an unknown manifest entry and skipped.

    A FAILED download does not abort the run. Each downloading kind guards its
    own download and returns cleanly on failure; the loop records the severity
    from the line's requiredness (`req`, the 5th manifest column -- absent means
    required) and moves on to the next line. So a broken OPTIONAL entry -- the go
    tarball is optional -- can no longer block a REQUIRED one that follows it,
    such as yq. Before this, a `curl (23)` write error on the go download aborted
    the whole run under `set -e` and yq was never reached.

    Architecture is hardcoded linux/amd64 for both downloading kinds. On
    any other OS or architecture this tool will fetch the wrong artifact
    rather than refuse -- a real limitation, not a documented option.

    Real footgun: every line of output goes to the log file only. `log()`
    pipes through `tee -a "$OUT" >/dev/null`, and the downloads are quiet
    (curl -fsSL), so a successful run prints NOTHING to the terminal. Read
    LOG_DIR/tools-update.<UTC-timestamp>.log to see what happened. The
    resolved path is printed when the run starts.


# ENVIRONMENT

    HOME               install prefix -- $HOME/.local/bin and $HOME/.local/go
    TMPDIR             download scratch space for the go tarball (default /tmp)
    PATH               must contain $HOME/.local/bin for the installed
                       binaries to be reachable; the log says so if it is not
    HEE_STATUS_STYLE   icon (default), ascii, or plain. See heerc.


# FILES

    tooling/tools.manifest.txt              default manifest
    $XDG_STATE_HOME/hee/tools/tools-update.*.log   per-run log


# EXIT STATUS

    Nagios plugin convention; the worst line wins, matching hee-tools-check.
    0 OK        every manifest line was processed and every install succeeded
    1 WARNING   an OPTIONAL line's install failed (bad download/extract). Other
                lines still ran.
    2 CRITICAL  a REQUIRED line's install failed, or a line names a kind this
                tool cannot act on (that line was skipped, so a pin is unapplied).

    A failed download no longer aborts the run or leaks curl's own exit code:
    the download is guarded, the failure is mapped to WARNING/CRITICAL by the
    line's requiredness, and the remaining lines are still processed.


# EXAMPLES

    hee tools-update

    Not marked "# ci": it downloads and installs the pinned toolchain (go, yq)
    into ~/.local, a mutation of the host, so there is no read-only run to prove.
    hee tools-check is the read-only half and IS proven in CI.


# SEE ALSO

    hee-tools, hee-tools-check
