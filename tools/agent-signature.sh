#!/usr/bin/env bash
# path: tools/agent-signature.sh
# Prints the signature block defined by
# contracts/agent-instance-signature-v1.contract.yaml -- every field is
# read from this process's own environment, nothing invented or
# centrally issued. Use this instead of hand-assembling the fields.
#
# Usage:
#   tools/agent-signature.sh          # human-readable block
#   tools/agent-signature.sh --footer # markdown footer for a GitHub comment
set -euo pipefail

session_id="${CLAUDE_CODE_SESSION_ID:-unknown}"
pid="${CLAUDE_PID:-$$}"
host="$(hostname)"
ts="$(date -Is)"

if [[ -n "${TMUX:-}" ]]; then
  socket_path="${TMUX%%,*}"
  tmux_uri="${socket_path}:${TMUX_SESSION:-unknown}:${TMUX_PANE:-unknown}"
else
  tmux_uri="none"
fi

msg_socket="${CLAUDE_CODE_MESSAGING_SOCKET:-none}"

gh_actor="$(gh auth status 2>&1 | grep -oP 'account \K\S+' | head -1 || echo unknown)"

if [[ "${1:-}" == "--footer" ]]; then
  cat <<EOF

---
<sub>signed: session \`${session_id}\` · pid \`${pid}\` · tmux \`${tmux_uri}\` · ${gh_actor}@${host} · ${ts}</sub>
EOF
else
  cat <<EOF
session_id:        ${session_id}
pid:                ${pid}
tmux_uri:           ${tmux_uri}
messaging_socket:   ${msg_socket}
host:               ${host}
gh_actor:           ${gh_actor}
timestamp:          ${ts}
EOF
fi
