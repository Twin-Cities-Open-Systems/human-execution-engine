# hee-pwgen(1)

```
hee-pwgen -- cryptographically secure password generator

SYNOPSIS
  hee-pwgen [LENGTH]
  hee-pwgen help

DESCRIPTION
  Prints one password to stdout and nothing else, so it pipes cleanly
  into a file or a password manager.

  LENGTH is the character count, default 20. It must be a positive
  integer; there is no maximum. A LENGTH under 12 still generates, but
  prints a warning to stderr first -- stdout stays exactly one line
  either way.

  Characters are drawn from ASCII letters and digits only (62 symbols,
  no punctuation), using secrets.choice -- Python's CSPRNG, not the
  `random` module. The alphabet is deliberately punctuation-free so the
  output survives shell quoting, config files, and web forms that reject
  symbols; that costs about 0.7 bits per character against a full
  printable set, so add characters rather than reaching for punctuation.

  Nothing is stored, logged, or echoed anywhere else -- if the password
  ends up on a shared surface, it is because the caller piped it there.

EXIT STATUS
  Nagios plugin convention.
  0 OK        a password was printed
  1 WARNING   LENGTH was not an integer, or was less than 1 -- message on
              stderr, nothing on stdout. Note: this is a usage error, which
              the org vocabulary would put at 2 CRITICAL; the tool really
              exits 1 today and is documented as-is, not changed here.

EXAMPLES
  hee-pwgen                  20 characters
  hee-pwgen 32               32 characters
  hee-pwgen > ~/.secret      straight to a private file, never to a log

SEE ALSO
  hee-cred -- which deliberately does NOT generate for you; its -seal
  step relies on a human typing their own password.
```
