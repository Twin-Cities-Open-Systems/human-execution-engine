% HEE-VIEW(1) | HEE Tools

# NAME

hee-view - hee-view command

# SYNOPSIS

    hee-view [-h] [--pve-host PVE_HOST] [--haproxy-host HAPROXY_HOST]

# DESCRIPTION

                    [--dns-host DNS_HOST] [--nerd] [--sites] [--sitemap SITEMAP]
                    [--via [USER@]HOST] [--crawl] [--sites-only]
                    [--network {lab,public,all}]

    options:
      -h, --help            show this help message and exit
      --pve-host PVE_HOST
      --haproxy-host HAPROXY_HOST
      --dns-host DNS_HOST
      --nerd                per-container cpu/mem/disk-io/net-io/elapsed + totals;
                            also full per-URL --sites detail
      --sites               check every real URL in the site map answers 200-399
      --sitemap SITEMAP     sitemap source -- URL or local path (default: real
                            .github/profile/SITEMAP.yaml on main)
      --via [USER@]HOST     run the --sites checks FROM that host over ssh (this
                            file is sent with `python3 -`; the host needs only
                            python3). The point is a vantage that is not the
                            operator's own IP: the DigitalOcean droplet
                            (man.tcos.us) sees tcos.us the way the public does --
                            Cloudflare edge, no LAN split-DNS, no home-IP
                            exemptions. Implies --sites-only and --network public
                            unless given.
      --crawl               with --sites: follow same-host links from each listed
                            site (depth 2), check every page found, follow
                            blog->media redirects to a 2xx, and report reachable
                            pages the site map does not list
      --sites-only          skip the pve/haproxy/dns section; just the site checks
      --network {lab,public,all}
                            only check sites on this network. A GitHub-hosted
                            runner can only reach 'public'; an on-host checker
                            inside the lab can reach 'lab'. Default all.
