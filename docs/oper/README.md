# Operations Documentation

This directory contains runtime, logging, and failure handling documentation for HEE (Human Execution Engine) operations.

## Operator Contract

**MUST:**

- Operate from repo root; paths are repo-relative
- Use imperative voice in all documentation
- Keep tone authoritative, terse, experience-backed
- Follow PLAN vs ACT discipline strictly
- Capture evidence before making changes
- Stop immediately on hard gate failures

**MUST NOT:**

- Write files outside `doc/oper/**`
- Ask questions during ACT mode execution
- Modify tooling, validators, CI, or schemas
- Continue after a hard gate fails
- Force push to main branch
- Edit YAML by hand for quick fixes

## PLAN vs ACT Discipline

### PLAN Mode

- Design-only, no execution
- Produces patch-plan, run prompt, and checklist
- Used for gathering context and creating implementation strategy
- Zero questions to user during execution

### ACT Mode

- Executes steps, writes files, runs commands
- Zero questions; smallest-safe assumption for missing information
- Follows pre-defined checklist strictly
- Stops immediately on any deviation from expected output

**Hard Rule:** Don't mix modes. If you need design, stop ACT and switch to PLAN.

## Expected Workflow After Pressing Enter in ACT Mode

1. **Preflight Gates**
   - Verify clean main branch
   - Confirm branch creation
   - Check file paths are correct

2. **Execution**
   - Run commands in sequence
   - Monitor output for deviations
   - Capture evidence of each step

3. **Validation**
   - Verify file changes are correct
   - Check git status
   - Ensure only `doc/oper/**` files changed

4. **Commit**
   - Create commit with required message format
   - Verify commit contains only intended changes

5. **Report**
   - Generate run report with required fields
   - Include commands executed and summary

## Logging and Evidence Posture

See [logs-and-artifacts.md](./logs-and-artifacts.md) for detailed logging requirements.

## Failure Handling Posture

See [failure-playbook.md](./failure-playbook.md) for detailed failure response procedures.

## Related Documentation

- [Agent Environment Cheatsheet](./agent-env-cheatsheet.md)
- [Logs and Artifacts](./logs-and-artifacts.md)
- [Failure Playbook](./failure-playbook.md)
- [Glossary](#glossary)

---

## Glossary

### Pill

A self-contained unit of work in HEE that encapsulates a specific task or operation. Pills are atomic and can be executed independently.

### Capsule

A collection of related pills that work together to accomplish a larger objective. Capsules provide context and coordination between multiple pills.

### Jump Capsule

A special type of capsule used to transition between different phases or modes of operation. Jump capsules handle state transitions and context switching.

### Run Prompt

The initial command or set of instructions that triggers an HEE execution run. Run prompts define the scope and parameters of the operation.

### Run Report

A structured output generated at the end of an HEE execution run. Contains status, summary, commands executed, and operator notes.

### Design Thread

The planning phase of an HEE operation where requirements are analyzed and implementation strategy is developed before execution begins.

### Execution Run

The active phase where HEE performs the actual work defined in the design thread. All file modifications and command executions happen during this phase.

### FIN

The successful completion status of an HEE operation. Indicates all requirements were met and the task was completed successfully.

### FAIL

The failure status of an HEE operation. Indicates one or more hard gates failed or requirements could not be met. Requires investigation and corrective action.

### Disk / permanent state of record

HEE's preferred store for anything that needs to be a durable, checked-in
fact: a file on disk in a git repo, not a remote/hosted service. "Disk"
isn't literally "spinning rust" — it means the checked-in, versioned file
itself is the source of truth, wherever it physically lives. This holds at
every scale HEE runs at, hyperscaler to the pencil: the same technical
declaration must stay correct whether a cloud unikernel gate reads it or a
human reads it printed on paper. Added per
[human-execution-engine#245](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/pull/245)'s
review of `hee/docs/hee-66550.mib`'s `contractFileName`.

### Leg / duople / stool (`hee-soa.v1`)

HEE's real identity-anchoring hash chain, implemented in
[`library/py/hee_hash/soa.py`](../../library/py/hee_hash/soa.py). Three
**legs** (`leg.home_fs`, `leg.repo_fs`, `leg.user`) each hash independently;
the three legs combine pairwise into three **duoples**; the three duoples
combine into one **stool** root hash — 3 legs and a seat make a stool. The
expected stool hash is meant to live at `~/.hee/index/_.yaml#hee-soa.v1`
(the **SOA anchor**) — as of this writing, no identity in the fleet has that
file yet (see [`prompts/INIT.md`](../../prompts/INIT.md)), so the chain is
implemented and real, but not yet load-bearing anywhere. Don't claim
otherwise until it is.

### Long value, short display

The codebase's existing convention for showing a long value (a 64-char
sha256 stool hash, a long path) in a UI or log without truncating
ambiguously: keep both ends, elide the middle — `f"{v[:8]}..{v[-8:]}"`.
See `_show()` in `library/py/hee_hash/soa.py`. Not yet applied outside the
hash chain; noted here so a future field (e.g. `contractFileName`) can reuse
it deliberately instead of reinventing a truncation scheme.
