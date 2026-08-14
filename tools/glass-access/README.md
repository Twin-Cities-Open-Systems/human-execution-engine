# glass-access

Access-controlled display/workspace ("slot") switching. Every action
checks a real identity → allowed-slots mapping (`config.json`) before
touching the display — not just bare `wmctrl`.

## Status (2026-08-13)

- **X11 backend (touchy): real, working, tested.** Dogfooded live —
  denial correctly blocks an out-of-scope slot, success correctly
  switches/wakes/raises for an allowed one. See `backends/x11.mjs`.
- **Wayland backend: deliberately a stub**, not a guess. `backends/wayland.mjs`
  throws a clear "not implemented" error rather than pretending to work.
  Blocked on one fact: which machine/compositor this targets — per
  spencer, that's an infra decision routed through claude@nuc-1
  ("the metal is mine and I will have claude@nuc-1 direct that"), not
  something to assume here. See the `project_wayland_display_control`
  memory for the real research (wlrctl/wdotool/kdotool/swaymsg/hyprctl)
  done ahead of that answer landing.

## Usage

```
node glass-access.mjs status
node glass-access.mjs whoami  --identity claude-touchy
node glass-access.mjs switch  --identity claude-touchy --slot 2
```

## Design

`glass-access.mjs` is backend-agnostic — it only knows "check identity
against config, then call `backend.switchToSlot()` etc." Adding a real
Wayland backend later means filling in `backends/wayland.mjs` with the
same function signatures `x11.mjs` already has; nothing else changes.

This supersedes `~/.local/bin/kiosk-switch.sh` for anything that needs
real access control (e.g. touchy's own Claude session only being
allowed on its own verification slot, not the dashboard/HA slots a
human drives) — `kiosk-switch.sh` still works for a human just switching
slots by hand, no permission model needed there.
