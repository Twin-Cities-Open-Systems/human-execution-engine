// x11.mjs — the real, working backend for touchy (Cinnamon/X11).
// Wraps the same wmctrl/xprop calls proven out manually this session
// (workspace switch, move-window-to-workspace, force-fullscreen,
// DPMS wake) behind a stable interface a Wayland backend can mirror
// later without the CLI or config format needing to change.
import { execSync } from "child_process";

function sh(cmd) {
  return execSync(`DISPLAY=:0 ${cmd}`, { encoding: "utf8" }).trim();
}

export function switchToSlot(slotIndex) {
  sh(`wmctrl -s ${slotIndex}`);
}

export function wakeDisplay() {
  sh(`xset dpms force on`);
  sh(`xset s reset`);
}

export function findWindowId(windowMatch) {
  const lines = sh(`wmctrl -l -x`).split("\n");
  const hit = lines.find((l) => l.includes(windowMatch));
  return hit ? hit.split(/\s+/)[0] : null;
}

export function moveWindowToSlot(windowMatch, slotIndex) {
  const id = findWindowId(windowMatch);
  if (!id) throw new Error(`No window matching "${windowMatch}" found — is it running?`);
  sh(`wmctrl -i -r ${id} -t ${slotIndex}`);
  return id;
}

export function forceFullscreen(windowMatch) {
  const id = findWindowId(windowMatch);
  if (!id) throw new Error(`No window matching "${windowMatch}" found — is it running?`);
  sh(`wmctrl -i -r ${id} -b add,fullscreen`);
  return id;
}

export function raiseWindow(windowMatch) {
  const id = findWindowId(windowMatch);
  if (!id) throw new Error(`No window matching "${windowMatch}" found — is it running?`);
  sh(`wmctrl -i -a ${id}`);
  return id;
}

export function currentSlot() {
  // wmctrl -d marks the active desktop with "*" in column 2
  const lines = sh(`wmctrl -d`).split("\n");
  const active = lines.find((l) => l.includes("*"));
  return active ? parseInt(active.trim()[0], 10) : null;
}
