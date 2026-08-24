# HA kiosk credential storage (low-value creds) — options + tradeoffs

Recovered from a private working repo (`tcos-plan-private`) 2026-08-24 as
part of the [fleet-ops#272](https://github.com/Twin-Cities-Open-Systems/fleet-ops/issues/272)
recovery epic. Generic sysadmin reference material -- no private content,
migrated as-is.

## Context
Goal: kiosk-ish Home Assistant display on a Linux box. Need "it just loads"
behavior with minimal future fuss. Credentials are low-value, but sane
blast-radius still matters.

## Best practical (recommended): don't store the password — store a session
**Idea:** Use a dedicated HA "display/kiosk" user and rely on a persistent
login session (cookie) in a dedicated browser profile.

### Steps
1. Home Assistant:
   - Create a non-admin user: `display` / `kiosk`
   - Give minimum privileges (at least: not admin)
   - Set its default dashboard to the intended Lovelace view
2. Kiosk box (Firefox recommended):
   - Create a dedicated Firefox profile for HA kiosk (keeps cookies/session isolated)
   - Log in once as the `display` user
   - Enable "Keep me logged in / Remember me" (whatever the HA login flow offers)
   - After that, the kiosk uses the stored session cookie instead of retyping a password

### Why this is good
- If the kiosk box is compromised, an attacker gets a "display user session," not admin creds.
- Less password handling; fewer "where did I store it?" problems.
- Clean separation if the same machine is used for other browsing.

## Next best: store password in the browser password manager
**Idea:** Let the browser save the password (convenient, usually fine for low-value creds).

Pros: easiest UX; works across browser restarts even if the session cookie expires.

Cons: anyone with access to the browser profile/home dir can often exfiltrate it (not plaintext, but not "safe" against a local attacker).

Optional guardrail: a browser "primary password" adds friction (may be annoying for an unattended kiosk).

## More "systems-y": OS keyring (mostly for Chrome-family browsers)
Chrome/Chromium/Edge often integrate with GNOME Keyring/Secret Service.

Pros: centralized credential store.

Cons: on auto-login kiosks, keyring unlock behavior can be finicky unless intentionally configured.

## Convenience-first (riskier): skip login via trusted network setup
Some HA setups allow network-trusted access (e.g., from a specific IP/subnet).

Pros: no credentials stored and no login prompts.

Cons: anyone with access to that "trusted" network path may gain access. If used: pin to a single static IP, isolate VLAN, and treat it as a security-boundary decision.

## Recommended plan for this shape of environment
- Create an HA user: `display` (non-admin)
- Use a dedicated browser profile for the kiosk
- Log in once and keep the session persistent
- Avoid admin creds on kiosk devices
- Only consider trusted-network auth if you intentionally accept the risk and have network isolation
