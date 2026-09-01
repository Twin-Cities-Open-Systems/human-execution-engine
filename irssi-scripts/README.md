# irssi scripts

Real irssi Perl scripts, native to the client -- distinct from
`tooling/bin/`'s standalone Python tools (which run outside irssi
entirely). Different runtime, so logic isn't shared code, just kept in
sync by hand where the two overlap.

## `hee_finger.pl`

Adds a real `/FINGER` command to irssi. Local queries shell to the
real `finger(1)` (already correct, not reimplemented). Remote queries
(`user@host[:port]`) speak RFC 1288 directly over a socket -- same
protocol logic as `tooling/bin/hee-net -proto finger` in
human-execution-engine.

Real trigger: "we imp finger in custom irssi plugin," then "I hate
perl, it is a must for hee. yes perl is way hee use it" -- irssi's
native scripting language is Perl, so a real client-native command
means Perl, not a workaround.

Install: copy to `~/.irssi/scripts/`, then `/SCRIPT LOAD hee_finger`
inside irssi (or `/SCRIPT LOAD hee_finger.pl` from outside `scripts/`).

Usage: `/FINGER spencer` or `/FINGER spencer@some.host:79`
