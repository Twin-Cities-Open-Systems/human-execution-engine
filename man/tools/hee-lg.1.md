# hee-lg(1)

```
hee-lg -- BGP looking glass for a domain, IP, or ASN

SYNOPSIS
  hee-lg <domain>
  hee-lg <ip>
  hee-lg AS<number>
  hee-lg help

DESCRIPTION
  Takes exactly one target and prints a short, flat report on the
  autonomous system behind it. Read-only: three public lookups, no auth,
  no scraping, nothing written anywhere.

  How the target is resolved, in order:
    AS<number>   used directly, no resolution step (case-insensitive)
    an IP        used directly
    anything else  resolved with gethostbyname(3) -- IPv4 only, and only
                   the FIRST address returned, so a multi-homed name
                   reports on whichever A record resolution hands back

  From the IP, the origin ASN comes from a Team Cymru whois query
  (whois -h whois.cymru.com), which needs the whois(1) binary on PATH.

  Then, for that ASN:
    holder          RIPEstat as-overview
    announced now   RIPEstat announced-prefixes, counted as IPv4 / IPv6
    peeringdb       policy, scope and type from the PeeringDB net record,
                    plus the network's published looking-glass URL if it
                    has one

  Each of the three ASN lookups fails independently and prints its own
  "(lookup failed)" line -- a dead RIPEstat does not stop the PeeringDB
  line from printing, and does NOT change the exit status. Read the
  lines, not the exit code, to know whether every source answered.

  Every network call has a 15 second timeout; a fully unreachable run
  therefore takes about a minute rather than hanging.

EXIT STATUS
  Nagios plugin convention.
  0 OK        a report was printed -- possibly with some sources failed
  1 WARNING   wrong number of arguments (this page is printed), the target
              would not resolve to an IP, or Team Cymru returned nothing
              usable for it. Note: these are usage/UNKNOWN-shaped failures
              that the org vocabulary would put at 2 CRITICAL or 3 UNKNOWN;
              the tool really exits 1 today and is documented as-is, not
              changed here.

ENVIRONMENT
  No environment variables are read. Real external requirements: the
  whois(1) binary on PATH, and outbound network access to
  whois.cymru.com, stat.ripe.net and www.peeringdb.com.

EXAMPLES
  hee-lg AS25720
  hee-lg honeycomb.net
  hee-lg 8.8.8.8
```
