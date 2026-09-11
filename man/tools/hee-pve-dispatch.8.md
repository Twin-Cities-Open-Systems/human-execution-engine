% HEE-PVE-DISPATCH(8) | HEE Tools

# NAME

hee-pve-dispatch - hand one bounded job to one agent container and collect the result

# SYNOPSIS

    hee-pve-dispatch [-h] [--cred ACCOUNT] [--cred-dir DIR] [--key-env VAR]
      hee-pve-dispatch AGENT JOBDIR --cred ACCOUNT [--cred-dir DIR] [--ticket ID]
      hee-pve-dispatch AGENT JOBDIR --wif --cred ISSUER-KEY-ACCOUNT [--ticket ID]
      hee-pve-dispatch AGENT JOBDIR --collect JID [--ticket ID]     # a job whose dispatcher died: outputs, evidence, record


# DESCRIPTION

                            [--wif] [--ticket ID] [--offline] [--collect JID]
                            [--dry-run] [--host HOST] [--allocations ALLOCATIONS]
                            agent jobdir

    hee-pve-dispatch -- hand one bounded job to one agent container and collect the result.

    The first dispatch mechanism for the pve agent containers (fleet-ops#387):
    until the GitHub App, the factory's per-job token and tick-task exist, this
    is how work reaches an agent. Operator, 2026-09-10: "this jobs go to the new
    agents", "do not run these on kiosk", "let's see if we can utilize hee cred
    to provide the anthropic auth needed", "hee ticket and tick-task will be
    merging soon".

    What a dispatch is:
      1. AGENT names a role in the fleet allocation registry (ci-triage,
         docs-keeper, ...). The registry gives its hostname and says it is an
         agent; the live node gives its vmid. A non-agent container is refused.
      2. JOBDIR holds job.yaml, a prompt file, the inputs the job may read, and
         (after the run) results/. Everything the agent sees is in that
         directory, so a job is reviewable before it runs and reproducible after.
      3. The job's files are shipped INTO the container over pct exec (no repo
         credential in the container), claude runs there as the `agent` user in
         -p mode with a dollar budget and a wall-clock timeout, and the outputs
         come back the same way into JOBDIR/results/<job id>/.
      4. The Anthropic key never touches the container's disk or any command
         line. With --cred, this tool re-runs itself under `hee cred -pass`, so
         the key exists only in this process's environment and is written to the
         job's stdin, where the generated run.sh reads it into the environment of
         the one claude process. `hee cred -seal` is the only way a key gets into
         the store, and it accepts input only from a real terminal.
      5. A record of every dispatch is written to <repo>/.hee/dispatch/<job id>.yaml
         (the repo JOBDIR lives in): agent, vmid, ticket, cost, turns, exit.

    job.yaml:
      name: convert-legacy-page           # short, becomes part of the job id
      prompt: prompt.md                   # file in JOBDIR; its text is the -p prompt
      inputs: [in/, rules.md]             # shipped; default: everything but results/
      outputs: [out/]                     # collected; default: out/
      agent: docs-keeper                  # optional: a dispatch that resolves to any other role is refused
      ticket: fleet-ops/0100              # optional: recorded when --ticket is not given
      blocked_by: [fleet-ops/0080]        # optional: while any is open a real dispatch refuses, a dry run warns
      budget_usd: 2.00                    # required -- claude --max-budget-usd; above 1.00 needs budget_reason
      budget_reason: "five doc pages to read and cite"   # required when budget_usd > 1.00
      timeout_s: 1800                     # default 1800 -- `timeout` around claude
      permission_mode: acceptEdits        # default; claude --permission-mode
      allowed_tools: [Read, Write, Edit, Glob, Grep]   # default; no Bash unless listed
      json_schema: schema.json            # optional; claude --json-schema
      system_prompt: system.md            # optional; claude --append-system-prompt-file


# EXAMPLES

      $ hee pve dispatch ci-triage tests/fixtures/dispatch/job --dry-run --offline --allocations tests/fixtures/dispatch/allocations.yaml   # ci
      $ hee pve dispatch ci-triage tests/fixtures/dispatch/job --wif --dry-run --offline --allocations tests/fixtures/dispatch/allocations.yaml   # ci
      $ hee pve dispatch ci-triage pve/agents/jobs/wif-prep-readonly --wif --cred wif-issuer-lab --ticket 0090     # the real thing; needs the lab

      --wif: workload identity federation instead of a static key. --cred names
         the hee cred account holding the lab issuer's ES256 private key (made by
         `hee cred -seal ... -genkey es256`). This tool mints ONE JWT for the job
         (iss/sub/aud from the allocation registry's console: block, unique jti,
         exp = the job timeout + 2 min), ships it on stdin exactly as a key would
         be, and the generated run.sh exchanges it once at the Claude Console
         (POST /v1/oauth/token, jwt-bearer) for a short-lived token bound to the
         role's service account, then runs claude with ANTHROPIC_AUTH_TOKEN. No
         static API key exists anywhere for the agent. The registry entry needs
         console.organization_id, workspace_id, service_account_id,
         federation_rule_id, issuer and subject.
      hee-pve-dispatch AGENT JOBDIR --dry-run

    positional arguments:
      agent                 a role (ci-triage) or hostname from the allocation
                            registry; must be kind: agent
      jobdir                directory holding job.yaml, the prompt and the inputs

    options:
      -h, --help            show this help message and exit
      --cred ACCOUNT        hee cred account holding the agent's Anthropic API
                            key; this tool re-runs itself under `hee cred -pass
                            ACCOUNT` so the key is never printed or on argv
      --cred-dir DIR        passed to hee cred -dir (default: its own default)
      --key-env VAR         read the key from this environment variable instead of
                            --cred (what the --cred re-exec uses: HEE_CRED_PASS).
                            Never pass a key on the command line.
      --wif                 federate instead of a static key: --cred is the lab
                            issuer's signing key; the registry's console: block
                            for the role supplies rule, org, service account,
                            workspace, issuer, subject
      --ticket ID           the hee ticket this dispatch works on; recorded, not
                            enforced
      --offline             with --dry-run: do not ask the pve node for the
                            container; take the registry's vmid (fixtures, CI)
      --collect JID         collect a job that already ran (or is still running)
                            in the container -- outputs, evidence, record --
                            without shipping or running anything. For a dispatcher
                            that died mid-job (kiosk killed one on low memory,
                            2026-09-11).
      --dry-run             resolve the agent, validate the job, print run.sh and
                            the file list; ship and run nothing
      --host HOST
      --allocations ALLOCATIONS
