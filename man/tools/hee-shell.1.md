# hee-shell(1)

section: 1
hee-shell -- ssh into a known TCOS host by short alias.

Real, deliberately thin: this is `ssh` with TCOS's own host aliases
baked in, not a new protocol or a permissions mechanism. It cannot
grant access a key doesn't already have -- if the calling session's
key isn't authorized on the target host/account, this fails exactly
like a bare `ssh` call would, with the same real error.

Alias table only includes hosts actually confirmed reachable by name
this session -- not speculative. Add more here as they're verified,
not guessed.

usage:
  hee-shell <alias|host> [user]

*(no --help/-h output -- generated from the script's own header comment)*
