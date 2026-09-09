% HEE-PVE-HEALTH(1) | HEE Tools

# NAME

hee-pve-health - hee-pve-health command

# SYNOPSIS

    hee-pve-health [-h] {status,inventory,map,drift,warn} ...

# DESCRIPTION

    positional arguments:
      {status,inventory,map,drift,warn}
        status              node, storage overcommit and per-container state
        inventory           the container table, rendered from the pve API
        map                 topology on four axes: -src (where the facts come
                            from), -out (what shape), -diff (which comparison),
                            -archive (which revisions)
        drift               do the committed artifacts still match the machine?
        warn                exit 1 on real overcommit or a container that is not
                            running

    options:
      -h, --help            show this help message and exit


# THE MAP AXES


      `map` used to carry --term, --proposed and --diff as three peer flags. They
      are not peers: --term is an output format, --proposed is a source selector,
      and --diff is a comparison mode. Three questions, one flat namespace. They
      are now four independent axes, and every old flag still works as an alias.

      -src SRC      WHERE THE FACTS COME FROM
                      live      the pve API + the running haproxy config (default)
                      roster    the agent roster registry
                      target    the AUTHORED proposed-network block, extracted and
                                re-emitted -- never regenerated
                      pfsense   the AUTHORED pfSense destination block, same rule

                    --proposed is an alias for `-src roster`. It renders the
                    proposed AGENT ROSTER, not a proposed network; the proposed
                    infrastructure is `-src target` / `-src pfsense`.

      -out FMT      WHAT SHAPE IT IS RENDERED IN
                      mmd       the fenced mermaid block (default)
                      term      a terminal drawing; --term is an alias
                      md        the block wrapped in its <!-- pve-map --> markers
                      json      mermaid lines + provenance note, as data
                      png       the local meme-factory renderer; needs -o PATH
                      svg       NOT IMPLEMENTED -- meme-factory/diagram's run()
                                calls PIL.Image.open().size and og_card()
                                unconditionally and both are raster-only

                    mmd is the default and that is not taste: `drift` renders the
                    map through this same code path and compares it against the
                    committed block, so any other default silently breaks it.

      -diff MODE    WHICH COMPARISON RUNS, over -a and -b
                      none      no comparison (default)
                      sub       A minus B -- declared and not built, the build queue
                      add       B minus A -- running and undeclared
                      both      each direction; a bare --diff means this
                    `diff` is accepted as a spelling of `both`. Only
                    `-a roster -b live` is joinable today: no role -> container
                    binding is recorded anywhere, so there is no key for any other
                    pair. `-out png` with a diff is refused -- a diff is a text
                    report, not a graph.

      -archive SPEC WHICH REVISIONS, over the COMMITTED history of the map block
                      1-5       ordinal id/range, newest first
                      'REGEX'   matched against "<sha> <date> <subject>"
                    Selection is library/py/hee_range, the org's one range
                    implementation -- not a second copy of it. Git is the archive
                    because the rendered-PNG store is a single clobbered filename
                    per job whose .meta.json carries no timestamp at all.

    RENDERING IS LOCAL, ALWAYS. -out png drives the renderer that already exists
    (tools/meme-factory/diagram) rather than becoming a second one. There is no
    hosted fallback and there must never be one: these maps carry the lab's
    internal addressing and its haproxy backend names, so an off-host render is
    an exfiltration.
