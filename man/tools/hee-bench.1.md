% HEE-BENCH(1) | HEE Tools

# NAME

hee-bench - judge a model against this org's own work, not a leaderboard

# SYNOPSIS

    hee-bench list   [--cases DIR]
    hee-bench check  [--cases DIR]
    hee-bench run    [--cases DIR] [--endpoint URL] [--model NAME] [--repeats N]
                     [--only CASE ...] [--timeout SEC] [--out FILE] [--dry-run]
    hee-bench grade  RUN.json [--out FILE]
    hee-bench report RUN.json [RUN.json ...]
    hee-bench [VERB] help


# DESCRIPTION


    HEE#361. Operator, 2026-08-24: "we only care about LLMs and models acting
    against things we care about, not some broad marketing benchmark." A bench
    here is a directory of cases, one YAML file each, every one drawn from
    real work this org already did and graded against what the org valued in
    the real outcome. The graders are deterministic -- no model judges a
    model -- and a saved run can be re-graded with no network.

    The endpoint is any OpenAI-compatible server (/v1/chat/completions):
    llama.cpp's llama-server, Ollama, vLLM. Every request goes at temperature
    0 with the case's own token budget.

    Scoring is HEE#326's RPN, not a new scheme. A case declares severity (what
    a wrong answer costs where that gate sits, 1..10) and detection (how
    likely a wrong answer slips past whatever checks it downstream, 1..10,
    10 = never caught). Occurrence is measured: the failure rate over the
    run's repeats on a 0..10 scale, 0 when every repeat passed. The run's RPN
    is the sum over cases; lower is better, and the ceiling (every case
    failing every time) is printed beside it so a number has a scale.

    Why RPN and not a percentage: a model that misses one cheap, well-caught
    case and one that misses the one case nobody checks downstream have the
    same pass rate. They are not the same model for this org's work.


# ENVIRONMENT

    HEE_BENCH_CASES      the cases directory when --cases is not given
    HEE_BENCH_ENDPOINT   the endpoint when --endpoint is not given; there is
                         no default, a fleet's endpoint is fleet state
    HEE_BENCH_MODEL      the model name sent in the request (default "default",
                         which llama-server maps to the one it has loaded)


# FILES

    <cases>/*.yaml       the cases; a fleet keeps them in its own repo
    RUN.json             a saved run (hee_bench: 1), self-contained


# EXIT STATUS

    0  OK        list/check: every case valid; run/grade: every case passed
    2  CRITICAL  a case file is invalid, or run/grade found a failing case
    3  UNKNOWN   usage error, no cases directory, endpoint unset or unreachable,
                 a run file that is not one


# EXAMPLES

    $ hee-bench list --cases tests/fixtures/bench/cases                               # ci
    $ hee-bench check --cases tests/fixtures/bench/cases                              # ci
    $ hee-bench run --cases tests/fixtures/bench/cases --endpoint http://127.0.0.1:9 --dry-run   # ci
    $ hee-bench grade tests/fixtures/bench/run.json                                   # ci
    $ hee-bench report tests/fixtures/bench/run.json                                  # ci
    $ HEE_BENCH_ENDPOINT=http://llm.lab.example:8080 hee-bench run --cases ~/git/fleet/hee/bench/cases --out runs/$(date -u +%Y%m%dT%H%M%SZ).json
    $ hee-bench run --only pr-title-conventional-yes --repeats 5
    $ hee-bench report runs/*.json

    The run example is not marked for CI because it needs a live endpoint.


# SEE ALSO

    hee-lint(1), hee-check(1), library/py/hee_bench, HEE#352, HEE#361, HEE#326

# A CASE

    One file, <name>.yaml; the file name is the case name.

      kind: predicate        # predicate | choice | set | exact | no_invented
      source: "fleet-ops#1003's title, merged 2026-10-16"   # required: the real work this came from
      system: "You are a strict gate. Answer YES or NO."     # optional
      prompt: "Is this a Conventional Commits subject? 'fix(pve): ...'"
      expected: YES          # predicate: YES|NO. choice: one of choices. set: a list
                             # (empty = NONE). exact: a string. no_invented: omitted.
      choices: [OK, WARNING, CRITICAL, UNKNOWN]   # choice only
      allowed: [example.org] # no_invented only: specifics the answer may name
                             # besides those already in the prompt
      max_tokens: 4          # default predicate/choice 8, set/exact 64, no_invented 1024
      severity: 6            # 1..10, default 5
      detection: 4           # 1..10, default 5
      why: "a wrong gate here lets an unconventional title reach main"   # optional

    Graders, by kind:
      predicate    the answer's first word, upper-cased, equals YES or NO
      choice       the first word equals the expected choice (case folded)
      set          the answer split on commas/newlines/semicolons, compared as
                   a case-folded set; the word NONE is the empty set
      exact        whitespace and case folded, a trailing period dropped
      no_invented  every URL, IPv4 address, ctNNN vmid and dotted hostname in
                   the answer must appear in the prompt, the system text or
                   `allowed`. The failure llm-1 showed on its first real task:
                   right dependency order, invented repository URL and names.
    A <think>...</think> trace is stripped before grading if the server let
    one through.


# VERBS

    list     every case: name, kind, severity, detection, token budget, source
    check    validate every case file; CRITICAL names the first bad one
    run      ask the endpoint every case --repeats times (default 1), grade
             each answer, print one line per answer and the totals. --out
             writes the whole run as JSON: every raw answer, the server's own
             timings, the grading, and the case itself, so the file stands
             alone. --only limits the run to the named cases. --dry-run
             prints what would be sent and touches no network.
    grade    re-grade a saved run with today's graders, no network. --out
             writes the re-graded run; without it the totals are printed.
    report   a Markdown table, one row per case and one column per run.
             Several runs of one model over time show drift; runs of several
             models against one corpus show which to pick.
