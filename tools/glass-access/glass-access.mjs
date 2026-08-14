#!/usr/bin/env node
// glass-access.mjs — access-controlled glass/slot switching.
//
// The point of this tool over bare wmctrl/kiosk-switch.sh: every action
// checks a real identity -> allowed-slots mapping (config.json) BEFORE
// touching the display, and the backend (x11 today, wayland once a
// target machine is confirmed) is swappable without this file or the
// config format changing. Direct ask, 2026-08-13: "a wayland control
// utility that handles access rights to slots on the glass."
//
// Usage:
//   node glass-access.mjs switch  --identity <id> --slot <n>
//   node glass-access.mjs whoami  --identity <id>
//   node glass-access.mjs status
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const DIR = path.dirname(fileURLToPath(import.meta.url));
const CONFIG_FILE = process.env.GLASS_CONFIG || "config.json"; // e.g. GLASS_CONFIG=config.dell-kiosk.json
const config = JSON.parse(fs.readFileSync(path.join(DIR, CONFIG_FILE), "utf8"));

function parseArgs(argv) {
  const [cmd, ...rest] = argv;
  const opts = {};
  for (let i = 0; i < rest.length; i += 2) opts[rest[i].replace(/^--/, "")] = rest[i + 1];
  return { cmd, opts };
}

async function loadBackend() {
  const mod = await import(`./backends/${config.backend}.mjs`);
  return mod;
}

function checkAccess(identity, slot) {
  const id = config.identities[identity];
  if (!id) throw new Error(`Unknown identity "${identity}" — not in config.json's identities map.`);
  if (!id.allowedSlots.includes(String(slot))) {
    throw new Error(`Access denied: "${identity}" is not permitted on slot ${slot} (allowed: ${id.allowedSlots.join(", ")}).`);
  }
  const slotDef = config.slots[String(slot)];
  if (!slotDef) throw new Error(`Unknown slot "${slot}" — not in config.json's slots map.`);
  return slotDef;
}

async function main() {
  const { cmd, opts } = parseArgs(process.argv.slice(2));

  if (cmd === "status") {
    const backend = await loadBackend();
    console.log(`Host: ${config.host} (backend: ${config.backend})`);
    console.log(`Current slot: ${backend.currentSlot()}`);
    console.log(`Slots:`);
    for (const [idx, def] of Object.entries(config.slots)) console.log(`  ${idx}: ${def.label}`);
    return;
  }

  if (cmd === "whoami") {
    const identity = config.identities[opts.identity];
    if (!identity) throw new Error(`Unknown identity "${opts.identity}".`);
    console.log(`${opts.identity}: allowed slots [${identity.allowedSlots.join(", ")}] — ${identity.note}`);
    return;
  }

  if (cmd === "switch") {
    if (!opts.identity || opts.slot === undefined) throw new Error("Usage: switch --identity <id> --slot <n>");
    const slotDef = checkAccess(opts.identity, opts.slot);
    const backend = await loadBackend();
    backend.wakeDisplay();
    backend.switchToSlot(opts.slot);
    backend.raiseWindow(slotDef.windowMatch);
    console.log(`OK: ${opts.identity} -> slot ${opts.slot} (${slotDef.label})`);
    return;
  }

  console.error("Usage: glass-access.mjs {switch|whoami|status} [--identity <id>] [--slot <n>]");
  process.exit(1);
}

main().catch((err) => {
  console.error(`DENIED/ERROR: ${err.message}`);
  process.exit(1);
});
