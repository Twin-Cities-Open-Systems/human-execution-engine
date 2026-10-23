% HEE-LLM(1) | HEE Tools

# NAME

hee-llm - give a local model work, not access: a checkout in, a patch out

# SYNOPSIS

    hee-llm job start NAME (--repo DIR [--ref REF] | --from PATH) [--dry-run] [--ledger DIR] [--ticket ID]
    hee-llm job ask NAME "PROMPT" [--allow-write] [--allow-shell] [--allow-web] [--read-also DIR ...]
                   [--max-steps N] [--max-tokens N] [--max-result-chars N] [--context N]
                   [--repo-name NAME] [--json] [--ledger DIR]
    hee-llm job collect NAME --out DIR [--repo-name NAME] [--ledger DIR]
    hee-llm job list
    hee-llm job rm NAME
    hee-llm tools [--allow-write] [--allow-shell]
    hee-llm [VERB] help

    Every verb takes --host HOST, --vmid N and --endpoint URL, or reads
    HEE_LLM_HOST, HEE_LLM_VMID and HEE_LLM_ENDPOINT. There are no defaults: a
    fleet's node, container and endpoint are fleet state, not engine state.


# DESCRIPTION


    Operator, 2026-10-16: "where should it keep its git worktrees? how do we
    allow it access?" Inside its own container, and it is given work, not
    access. The model server (llama-server with --agent) runs its built-in
    tools inside its own process, as its own user, from the unit's
    WorkingDirectory. This tool is the dispatcher's side of that:

    start    `git archive` of DIR at REF (tracked files only; no .git, no
             untracked secrets), shipped over `ssh root@HOST pct exec VMID`
             into /var/lib/llm/work/NAME/<repo>, then `git init`, one baseline
             commit and a `baseline` tag inside, so the model's edits are a
             diff against a known tree. Or --from PATH: a path INSIDE the
             container (a read-only mirror on a share, say) copied into the
             job, history kept, nothing over the wire; the `baseline` tag is
             its HEAD. (Copied, not cloned: git refuses to read another user's
             tree as a repository.) Exactly one of --repo and --from.
    ask      the tool loop over the OpenAI-compatible API. The server's tool
             definitions (GET /tools) are passed with the prompt; by default
             only the read-only ones (read_file, file_glob_search, grep_search,
             get_info). --allow-write adds write_file and edit_file,
             --allow-shell adds exec_shell_command, each per job. Every call is
             guarded: a path outside the job's root is refused and the model
             is told so; --read-also DIR (repeatable) lets the READ-ONLY tools
             look under DIR too (other repositories on a mirror), while the
             write tools stay held to the root; a shell command is run with
             `cd` into the root. Calls
             execute on the server (POST /tools) and their results go back to
             the model until it answers in text or --max-steps (default 8) is
             spent. Each tool result is clipped to --max-result-chars (default
             3000) before the model sees it, with a note saying so, and when
             the conversation nears --context tokens (default 8192, llm-1's
             -c) the OLDEST tool results are compacted to 300 chars: on
             2026-10-17 five results overran the server at 8639 tokens.
             --allow-web adds two tools that run HERE, on the dispatching
             host, never in the container: web_search (HEE_LLM_SEARCH_URL as
             a template with {q}; default DuckDuckGo's HTML endpoint, no key)
             and fetch_url (a page reduced to text). Both read-only, both
             clipped. The transcript of tool calls is printed; --json dumps it.
    collect  commits whatever the model left uncommitted (as hee-llm, not as
             anyone's identity), then `git format-patch baseline` into
             DIR/NAME.patch, also kept at /var/lib/llm/out/NAME/ in the
             container. Apply with `git am` on a branch of your own and review
             it like any other change; the PR is yours, signed by you.
    list     the jobs present under /var/lib/llm/work.
    rm       removes the job's work and out directories.
    tools    the tool names the loop would allow with the given flags.

    What never happens: no repository credential enters the container, no
    push leaves it, and nothing the model writes reaches a repo unreviewed.
    Why the shell tool is off by default: the fleet's bench (hee bench) shows
    this class of model answering that it may run `pct destroy` itself.

    Records  every other runner writes a dispatch record to
             <ledger>/.hee/dispatch/<job id>.yaml, which `hee view --jobs`, the
             daily cap and the factory registry read; without one this job is
             invisible to all three. `start` writes one (agent: llm, a class,
             never a fleet host name; subtype started, cost 0, no endpoint
             yet). Each `ask` adds its prompt/completion tokens and a one-line
             summary to it. `collect` finalizes ended_at, exit, subtype and the
             patch produced, with cost_usd 0.0 -- the local model has no
             marginal cost. --ledger DIR says where the record lives (default:
             this process's git top level, else its current directory); a dry
             run writes nothing. An `ask` or `collect` against a job started
             before this existed warns and carries on without a record.


# ENVIRONMENT

    HEE_LLM_SEARCH_URL web_search backend as a URL template containing {q}; a
                       SearXNG instance's /search?q={q}&format=json works, the
                       default is https://html.duckduckgo.com/html/?q={q}
    HEE_LLM_HOST       the pve node (ssh root@HOST)
    HEE_LLM_VMID       the container's vmid
    HEE_LLM_ENDPOINT   the model server (http://host:port), for ask and tools
    HEE_LLM_MODEL      model name in requests (default "default")


# FILES

    /var/lib/llm/work/NAME/<repo>/   the job's checkout, in the container
    /var/lib/llm/out/NAME/NAME.patch what collect produced, in the container
    DIR/NAME.patch                   the same, locally
    <ledger>/.hee/dispatch/<job id>.yaml   the dispatch record (see Records)


# EXIT STATUS

    0  OK        done; ask: the model answered
    1  WARNING   ask: the step budget ran out before a final answer
    2  CRITICAL  a refusal: bad name, git archive failed, the node or server
                 said no, collect produced nothing
    3  UNKNOWN   usage error, no host/vmid/endpoint, server unreachable


# EXAMPLES

    $ hee-llm tools                                                              # ci
    $ hee-llm tools --allow-write --allow-shell                                  # ci
    $ hee-llm job start ci-demo --repo . --ref HEAD --host pve.example --vmid 1 --dry-run   # ci
    $ hee-llm job start ci-demo --from /data/storage/git/repo --host pve.example --vmid 1 --dry-run   # ci
    $ HEE_LLM_HOST=10.0.0.153 HEE_LLM_VMID=120 hee-llm job start fix-readme --repo ~/git/fleet-ops --ref origin/main
    $ HEE_LLM_ENDPOINT=http://10.0.0.169:8080 hee-llm job ask fix-readme "Which manifests under pve/services lack onboot? Read them."
    $ hee-llm job ask fix-readme --allow-write "Fix the typo 'recieve' in pve/llm/README.md."
    $ hee-llm job ask audit --allow-web "What is the current stable llama.cpp release tag? Search, then cite the URL."
    $ hee-llm job start audit --from /data/storage/git/fleet-ops && hee-llm job ask audit --read-also /data/storage/git "Which hosts in inventory are not in pve/services?"
    $ hee-llm job collect fix-readme --out /tmp/fix-readme && git am /tmp/fix-readme/fix-readme.patch
    $ hee-llm job rm fix-readme

    The live examples are not marked for CI: they need a node and a model.


# SEE ALSO

    hee-bench(1), hee-pve-deploy(8), hee-pve-dispatch(1), library/py/hee_llm
