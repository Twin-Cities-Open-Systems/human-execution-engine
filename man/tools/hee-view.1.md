% HEE-VIEW(1) | HEE Tools

# NAME

hee-view - hee-view command

# SYNOPSIS

    hee-view [-h] [--pve-host PVE_HOST] [--haproxy-host HAPROXY_HOST]

# DESCRIPTION

                    [--dns-host DNS_HOST] [--nerd] [--sites] [--sitemap SITEMAP]
                    [--via [USER@]HOST] [--crawl] [--braindump] [--job JID]
                    [--json] [--jobs] [--md] [--live] [--publish VMID:PATH]
                    [--mark-seen] [--braindump-url URL] [--sites-only]
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
      --via [USER@]HOST     an ssh target or alias, never a URL: run the --sites
                            checks FROM that host (this file is sent with `python3
                            -`; the host needs only python3). The point is a
                            vantage that is not the operator's own IP: the
                            DigitalOcean droplet (man.tcos.us) sees tcos.us the
                            way the public does -- Cloudflare edge, no LAN split-
                            DNS, no home-IP exemptions. Implies --sites-only and
                            --network public unless given.
      --crawl               with --sites: follow same-host links from each listed
                            site (depth 2), check every page found, follow
                            blog->media redirects to a 2xx, and report reachable
                            pages the site map does not list
      --braindump           what has been written to the view.lab brain dump since
                            you last looked. Append-only file, so the only
                            question is what is NEW -- this keeps a cursor and
                            reports the difference. WARNING exit (1) when there is
                            something unread, so it drives a watch or a status
                            line.
      --job JID, -job JID   one dispatched agent job, by id or unique prefix: the
                            dispatch record and results when finished; while
                            running, the container's cgroup, the claude process
                            and out/ read from the pve host
      --json                with --job: also print the raw record or probe as JSON
      --jobs, -jobs         every dispatch record (current repo, then ~/git/fleet-
                            ops): one row per job and a per-agent scorecard
      --md                  with --jobs: Markdown tables, for committing as
                            pve/agents/SCORECARD.md
      --live                with --jobs: also probe every running job on the pve
                            host (cgroup, process, out/)
      --publish VMID:PATH   with --jobs: write the JSON to that path inside a
                            container on the pve host (view.lab:
                            107:/www/data/jobs.json) instead of printing it --
                            what the 30 s timer on kiosk runs
      --mark-seen           with --braindump: remember the newest entry, so the
                            next run reports only what arrives after it. Separate
                            from reading on purpose -- a run that scrolled past
                            should not silently mark it read.
      --braindump-url URL   override the dump endpoint (heerc:
                            HEE_VIEW_BRAINDUMP_URL, default
                            https://view.lab.tcos.us/cgi-bin/braindump.cgi)
      --sites-only          skip the pve/haproxy/dns section; just the site checks
      --network {lab,public,all}
                            only check sites on this network. A GitHub-hosted
                            runner can only reach 'public'; an on-host checker
                            inside the lab can reach 'lab'. Default all.
