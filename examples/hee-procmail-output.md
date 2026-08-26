# `hee-procmail` — real run

Real trigger: spitballing an email-to-IRC relay
(`hee-irc+<channel>@tcos.us` -> `hee-con -irc <channel>`, see
[fleet-ops#224](https://github.com/Twin-Cities-Open-Systems/fleet-ops/issues/224))
landed on "procmail's spirit, adapted syntax" per Spencer's own verdict:
"fuck yes to procmailrc, I fucking hate that thing. very hee."

Rule file (`.hee/mailrules.yaml`):

```yaml
rules:
  - name: irc-relay
    match:
      header: To
      plus_of: hee-irc
    action: "echo hee-con -irc {tag}"
  - name: ping
    match:
      header: Subject
      regex: "^ping"
    action: "echo pong"
```

Four real cases, piped via stdin exactly the way an MTA would invoke it:

```
$ printf 'From: spencer@tcos.us\r\nTo: hee-irc+tclug@tcos.us\r\nSubject: join please\r\n\r\nbody\r\n' | hee-procmail
hee-procmail: rule 'irc-relay' matched -> ['echo', 'hee-con', '-irc', 'tclug']
hee-con -irc tclug

$ printf 'From: spencer@tcos.us\r\nTo: someone@tcos.us\r\nSubject: ping\r\n\r\nbody\r\n' | hee-procmail
hee-procmail: rule 'ping' matched -> ['echo', 'pong']
pong

$ printf 'From: spencer@tcos.us\r\nTo: someone@tcos.us\r\nSubject: unrelated\r\n\r\nbody\r\n' | hee-procmail
hee-procmail: no rule matched -- message dropped

$ printf 'From: spencer@tcos.us\r\nTo: hee-irc+tclug; rm -rf /@tcos.us\r\nSubject: x\r\n\r\nbody\r\n' | hee-procmail
hee-procmail: rule 'irc-relay' matched but tag 'tclug; rm -rf /' failed safe-charset check -- skipping
hee-procmail: no rule matched -- message dropped
```

The last case is the one that actually matters: a hostile `To` header
that would be a real shell-injection footgun in a naive procmail-style
config (unquoted extracted value flowing into a shell action) is caught
by the safe-charset check before it ever reaches `shlex`/`subprocess`.

## Explicitly not built here

- No real MTA/mail-server wiring -- this reads a message from stdin,
  same real interface procmail uses, but nothing delivers mail to it
  yet. That's `mxN.tcos.us`'s dependency, not this tool's.
- No `regex` capture-group substitution beyond `{match}` (the whole
  matched text) -- `plus_of`'s `{tag}` is the only structured extraction
  today. Add named groups if a real rule needs more.
- No stop/continue flag system like real procmail's `:0`/`:0c` -- first
  matching rule wins, full stop. Deliberate simplification, not
  forgotten scope.
