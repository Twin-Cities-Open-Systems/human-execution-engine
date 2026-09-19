% HEE-URL(1) | HEE Tools

# NAME

hee-url - short links: u.tcos.us/axgoose8/ -> the page it stands for

# SYNOPSIS

    hee-url add URL [--slug SLUG] [--tag T ...] [--note TEXT] [--force]
    hee-url get SLUG
    hee-url list
    hee-url search TERM [TERM ...] [--or]
    hee-url rm SLUG
    hee-url build --out DIR
    hee-url deploy [--dry-run] [--message TEXT]
    hee-url verify
    hee-url config [--init [--force]]
    hee-url [VERB] help

    The first version's spelling still works: -short URL, -get SLUG,
    -search TERM..., -tags "a b" and -or are read as add, get, search,
    --tag and --or. The old .hee/urls.db it wrote is not read.

    Every verb also takes --store DIR, --base URL, --length N, --infix TEXT
    and --config FILE, which override the config file for that one run.


# DESCRIPTION


    A URL shortener whose store is a directory of YAML files, one HEE object
    per short link, kept in git like anything else. Nothing here needs a
    database or a server: the links are records, and the serving side is a
    static tree generated from them.

    Slugs are derived, not random. sha256 of the target URL fills the free
    characters and places the infix, so the same URL shortens to the same
    slug on every machine and shortening twice changes nothing. By default a
    slug is 8 characters and contains "goose" -- axgoose8, goose1zk, x7goosem
    -- because the operator asked that every short link carry it. Both are
    settings, not rules of the tool.

    A record looks like this (hee lint passes it: the inuid reproduces from
    its seed, which is the short URL itself):

      apiVersion: hee/v1
      kind: Card
      metadata:
        name: axgoose8
        labels: {hee.object: "true", hee.tcos/topic: url, artifact: short-link}
        annotations: {inuid: <sha256>, inuid_seed: https://u.tcos.us/axgoose8/,
                      inuid_derivation: sha256(inuid_seed), created_utc: ..., author: ...}
      spec:
        slug: axgoose8
        short: https://u.tcos.us/axgoose8/
        url: https://example.com/some/other-url.html
        status: 302
        tags: []
        note: ""


# ENVIRONMENT

    HEE_URL_CONFIG         config file instead of ~/.config/hee/url.yaml
    CLOUDFLARE_API_TOKEN   token for deploy; HEE_CRED_PASS is read when
                           `hee cred -exec` set it
    CLOUDFLARE_ACCOUNT_ID  skips the account lookup


# FILES

    ~/.config/hee/url.yaml            settings
    ~/git/fleet-ops/hee/urls/*.yaml   the records (default store)


# EXIT STATUS

    0  OK        done; for verify, every link answers correctly
    1  CRITICAL  a refusal: bad URL or slug, slug taken, missing record,
                 unknown setting, wrangler or Cloudflare error
    2  CRITICAL  verify found a link that is wrong or missing
    3  UNKNOWN   usage error, or verify could not reach the host


# EXAMPLES

    $ hee-url --store tests/fixtures/urls list                                   # ci
    $ hee-url --store tests/fixtures/urls get axgoose8                           # ci
    $ hee-url --store tests/fixtures/urls search example                         # ci
    $ hee-url --store tests/fixtures/urls build --out "$(mktemp -d)"             # ci
    $ hee-url --store tests/fixtures/urls --config /dev/null config              # ci
    $ hee-url --store tests/fixtures/urls deploy --dry-run                       # ci
    $ hee-url add https://example.com/some/other-url.html
    $ hee-url add https://tcos.us/people --slug meetgoose --tag people
    $ hee-url --infix "" --length 4 add https://tcos.us/
    $ hee cred -pass cloudflare-tcos-www -dir ~/git/tcos-www/.hee/secrets -exec hee url deploy
    $ hee-url verify


# SEE ALSO

    hee-cred(1), hee-lint(1), hee-qr(1), library/py/hee_url

# VERBS

    add URL        shorten URL; print the short link. --slug picks the slug
                   by hand (it must still contain the infix); --tag and --note
                   are for `search`; --force retargets a slug that is taken.
                   A URL already in the store prints its existing link.
    get SLUG       print the target of one slug
    list           every link, one per line: slug, target, when it was made
    search TERMS   links whose slug, target, tags or note contain every term
                   (any term with --or); case-insensitive
    rm SLUG        delete the record. The live site keeps serving the old
                   redirect until the next deploy.
    build --out D  write the static tree to D: _redirects (one server-side
                   redirect per slug, with and without the trailing slash),
                   <slug>/index.html (the same redirect as a meta refresh, for
                   a host without _redirects), index.html and 404.html.
    deploy         build into a temporary directory and ship it as the
                   Cloudflare Worker named in the config (static assets, the
                   same path tcos-www uses for tcos.us), then attach the base
                   hostname to that Worker if it is not already -- Cloudflare
                   creates the DNS record itself. Needs Node >= 20 and a
                   token in CLOUDFLARE_API_TOKEN or HEE_CRED_PASS with
                   Workers Scripts:Edit and DNS:Edit on the zone:

                     hee cred -pass cloudflare-tcos-www -dir ~/git/tcos-www/.hee/secrets -exec hee url deploy

                   --dry-run builds and reports without touching Cloudflare.
    verify         ask the live host about every record, over the internet:
                   OK when the server redirects to the recorded target,
                   WARNING when only the meta refresh would, CRITICAL when it
                   goes elsewhere or is missing, UNKNOWN when unreachable.
    config         print the effective settings and where each came from.
                   --init writes ~/.config/hee/url.yaml with every key
                   commented out (--force overwrites one that exists).


# CONFIGURATION

    ~/.config/hee/url.yaml, or the file HEE_URL_CONFIG names. Every key is
    optional. An unknown key is an error, not a no-op.

      base: https://u.tcos.us      the public base of every short link
      store: ~/git/fleet-ops/hee/urls   where the records live
      length: 8                    slug length, infix included
      infix: goose                 text every slug must contain; "" drops it
      alphabet: abcdefghijklmnopqrstuvwxyz0123456789
      status: 302                  redirect code (301, 302, 307 or 308)
      worker: tcos-u               Cloudflare Worker name for deploy
      compatibility_date: 2026-08-15
      wrangler: wrangler@4.86.0    the pinned wrangler npx runs

    So `length: 4` with `infix: ""` gives four-character slugs, and
    `infix: ""` alone keeps eight characters with no required text. A length
    that leaves no free character beside the infix is refused.
