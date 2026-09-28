# GPT Prompting Guide

## Purpose

Standardize the way opers interact with GPT (primary session driver).

HEE strives for completely determined IN and OUT, given the same data.

IN <-> hee <-> OUT

Due to the nature of HEE (1st leg, 2nd leg, 3rd leg => Dog Food) INPUTs and OUTPUTs
will begin to become both IN and OUT after evidence suppots the object(s).
It is a lot of fun to watch the IN/OUT grow (number of stools) over time.

### INPUT

- session: a sourced input of reasoning and action
- evidence: data living as immutable evidence (ie. disk, dns, oid, etc.)
- policy: set of doctrine rattified by HEE
- doctrine: canonized HEE policy
- contract: binding rules of engagement between HEE objects
- blueprint: a set of plans and contracts needed to produce a useful HEE object
- plan: a Work Unit (WU) comprised of smaller, ordered, work units (wu)
- WU: one ordered phase in a plan
- wu: one ordered step in a WU
- step: one ordered step in a wu or WU (step -> wu -> WU -> PLAN -> BLUEPRINT)

### OUTPUT

- pill: a generic YAML file used to encapsulate session/idea/brainstorm data
- card: yaml files used to capture moments in time, and general knowledge
- ui: new
  - hee_epoch: 1770799033
    ~~~hee
    repo-only render; bind server to 127.0.0.1; uid/provenance planned; git_head=ecec43f
    HEE Battle Center
    v0: html render + tiny server. Next: registrar + trace_chain + gh_link.
    ~~~

## Prompts

### Quick Session (real example)

#### Purpose

Get in and out quickly and save all data to disk.

#### Chat Header

The chat header should be sent as k:v YAML.
These keys are specific to this chat, see [Errata](#errata) for more info.

~~~yaml
chat: market thesis
purpose: chit chat
oper: spencer
extra:
  - gpt-prompting-guide:
repo: [human-execution-engine, market-thesis]
inuid: 698b879b-b778-832c-9527-af25c2534c32
hee-epoch: date +%s at time of write from your pov # will always be ts: going forward
ts: {hee-epoch-date}
hee-obj(must be compliant hee-obj): https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/schemas/hee/v1/hee-object.schema.json
soa-compliant: https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/library/py/hee_hash/soa.py
repo-files-ghraw-link: https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/hee/evidence/index/repo.files.v1.json
current-handoff-policy: https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/pills/handoff/procedure.checkpoint-supergoldstar-handoff-v1.yaml
contract-gpt: dric
dric: https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/contracts/dric-v1.contract.yaml
~~~

##### Prompt

before we are done with this session (soon) I would like a card of this in the repo.

- files:
  - [../../hee/cards/gpt-prompting-guide.md](../../hee/cards/gpt-prompting-guide.md)
- ps1:
  - spencer@flippy ~/git/human-execution-engine (docs/formalize-gpt-prompts) $

---

#### Errata

- TODO(spencer): update below - gpt will do fun times here
  - sed -n '83,120' should do it
  - chat header
  - reconcile, merge and strip this bare and machgen a proper human facing doc, duh
    - preserve provenance, duh

##### Quick Reference Links

- inuid: `chat gpt URL ID | similar ID`
- hee-epoch: `date +%s`
- ts: {hee-epoch} (date +%s at time of write from your gpt PoV)
- hee-obj: <https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/schemas/hee/v1/hee-object.schema.json>
- soa: <https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/library/py/hee_hash/soa.py>
- repo-files: <https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/hee/evidence/index/repo.files.v1.json>
- canon-files: <https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/hee/evidence/index/canon.index.v1.json>
- handoff-policy: <https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/pills/handoff/procedure.checkpoint-supergoldstar-handoff-v1.yaml>
- dric: <https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/contracts/dric-v1.contract.yaml>
- contract: {dric} (or the exact contract the chat is under (still WiP))
- sub-contract: {GCIS} {dric} (needs ratification)
- gcic-spec: <https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/contracts/gcic-v1.contract.yaml>

##### QRL errata

- ts: {hee-epoch} is new and is meant to be a global epoch time
- hee-obj: is just now trying to assert authority, and a WiP
- soa: this is current on disk anchor and must be followed by all new process and policy
- repo-files: need plan to make sure it is up to day and useful
- canon-files: needs review, ideally all foundational docs are cannon (ie blueprints/ contracts/ schema/ plans/)
- handoff-policy: this is the current "checkpoint-supergoldstar-handoff" contract that still needs ratification
- dric: this is the old dric-v1 that needs to be updated so that sub.dric contracts can thrive (depends on GCIS)
- contract: the contract between the current gpt and the oper (dric,new TBD)
- sub-contract: this will be (proposed) {GCIS} -> {DRIC-v2} -> {gpt-oper-TBD}

##### Chat Header (needs ratification)

~~~yaml
# required
chat: "only used by chat-gpt"
purpose: "general pupose, can be vague/specific"

# to be added to the new chat as soon as INUID is created by chat-gpt-ui (quick)
inuid: "chatgpt.com/c/{INUID}"

# optional
oper: "oper name (typically, the value of $USER)"
repo: [list, of, repos, discussed]
ts: $(date +%s) {hee-epoch}
hee-obj: https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/schemas/hee/v1/hee-object.schema.json
soa: https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/library/py/hee_hash/soa.py
repo-files: https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/hee/evidence/index/repo.files.v1.json
handoff-policy: https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/pills/handoff/procedure.checkpoint-supergoldstar-handoff-v1.yaml
contrOact-gpt: {dric-v1} "the current contract used between oper<->gpt
dric-v1: https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/contracts/dric-v1.contract.yaml
gcic-spec-url: https://raw.githubusercontent.com/spencerbutler/human-execution-engine/refs/heads/main/contracts/gcic-v1.contract.yaml
~~~

---

~~~hee
# future

hee-footer:
    oper: spencer
    author: spencer
    ts: 1770760181
~~~
