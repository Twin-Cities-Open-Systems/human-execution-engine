// wayland.mjs — NOT YET IMPLEMENTED.
//
// Deliberately a stub, not a guess. Real research (2026-08-13, see the
// project_wayland_display_control memory) found no single universal
// tool — Wayland's window-management/input story is fragmented per
// compositor:
//   - wlrctl / wdotool for wlroots-based compositors (Sway, Hyprland,
//     river, Wayfire), via wlr-foreign-toplevel-management
//   - kdotool for KDE (KWin scripting)
//   - swaymsg for Sway specifically
//   - hyprctl for Hyprland specifically
//   - underlying cross-compositor mechanism for most of this: the XDG
//     RemoteDesktop portal + libei
//
// Per spencer, 2026-08-13: "the metal is mine and I will have
// claude@nuc-1 direct that" — which machine/compositor this targets is
// an infrastructure decision that arrives as a directive from nuc-1's
// session, not something touchy's session should guess. Implement the
// real functions below (matching x11.mjs's exact interface, so
// glass-access.mjs doesn't change) once that's known.

const NOT_CONFIGURED = "Wayland backend not implemented — target machine/compositor not yet confirmed by nuc-1. See project_wayland_display_control memory.";

export function switchToSlot() { throw new Error(NOT_CONFIGURED); }
export function wakeDisplay() { throw new Error(NOT_CONFIGURED); }
export function findWindowId() { throw new Error(NOT_CONFIGURED); }
export function moveWindowToSlot() { throw new Error(NOT_CONFIGURED); }
export function forceFullscreen() { throw new Error(NOT_CONFIGURED); }
export function raiseWindow() { throw new Error(NOT_CONFIGURED); }
export function currentSlot() { throw new Error(NOT_CONFIGURED); }
