// wayland-sway.mjs — real Sway backend, same interface as x11.mjs.
// Target confirmed 2026-08-14 (human-execution-engine#193): all-in-one
// Dell touchscreen kiosk, Sway compositor. UNTESTED — no access to the
// physical machine yet, only its hostname/compositor are confirmed.
// Written directly against Sway's own IPC (`swaymsg`), not the more
// generic wlrctl/wdotool — swaymsg is simpler and more reliable when the
// compositor is known specifically, rather than "some wlroots thing."
import { execSync } from "child_process";

function sway(cmd) {
  return execSync(`swaymsg ${cmd}`, { encoding: "utf8" }).trim();
}
function swayJson(cmd) {
  return JSON.parse(execSync(`swaymsg -t ${cmd}`, { encoding: "utf8" }));
}

export function switchToSlot(slotIndex) {
  sway(`workspace number ${slotIndex}`);
}

export function wakeDisplay() {
  sway(`'output * dpms on'`);
}

// Walks Sway's node tree looking for a window whose name/title contains
// `windowMatch` — mirrors x11.mjs's findWindowId, returns a con_id instead
// of an X11 window id (used the same way: passed back into the other
// functions below via a `[con_id=...]` criteria selector).
export function findWindowId(windowMatch) {
  const tree = swayJson("get_tree");
  let found = null;
  (function walk(node) {
    if (found) return;
    if (node.name && node.name.includes(windowMatch)) { found = node.id; return; }
    for (const child of node.nodes || []) walk(child);
    for (const child of node.floating_nodes || []) walk(child);
  })(tree);
  if (!found) throw new Error(`No window matching "${windowMatch}" found in Sway's tree — is it running?`);
  return found;
}

export function moveWindowToSlot(windowMatch, slotIndex) {
  const id = findWindowId(windowMatch);
  sway(`[con_id=${id}] move to workspace number ${slotIndex}`);
  return id;
}

export function forceFullscreen(windowMatch) {
  const id = findWindowId(windowMatch);
  sway(`[con_id=${id}] fullscreen enable`);
  return id;
}

export function raiseWindow(windowMatch) {
  const id = findWindowId(windowMatch);
  sway(`[con_id=${id}] focus`);
  return id;
}

export function currentSlot() {
  const workspaces = swayJson("get_workspaces");
  const active = workspaces.find((w) => w.focused);
  return active ? active.num : null;
}
