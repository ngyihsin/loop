# Design: loop

**Created:** 2026-10-19
**Status:** Draft v3

**Project Docs:** [README](../README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) *(you are here)* | [references](references.md) | [HANDOFF](../HANDOFF.md)

---

## Design Philosophy

1. **Jira is the source of truth** (from autopilot). No work without a ticket; every state change goes back to Jira.
2. **Skills are the product** (autopilot: "prompts are the product"). The orchestrator is thin plumbing; quality
   comes from the skills.
3. **Skill first, automation later.** Each agent is a `SKILL.md` you can run by hand (`/bug-analyze NPU-123`) in
   Claude Code or Codex. The orchestrator schedules it only after it has proven itself, so Phase 0 is useful on
   day one.
4. **The dossier is the only hand-off** (from docforge's HANDOFF). The next agent reads the dossier and Jira, never
   the previous agent's transcript.
5. **Evidence first** (from pstack's bug-fix playbook). Every changed line traces to a log, a reproduction, or a
   test. No "might help" changes.
6. **Humans gate the decisive points:** spec approval, Gerrit +2, sending a report. When unsure, an agent blocks
   and says what is missing (autopilot: "when in doubt, block").

---

## Architecture Overview

```
           ┌──────────────────────────── Jira (source of truth) ─────────────────────────────┐
           │  Bug / Story / Task  +  labels agent:*, comments, attachments (logs, dumps)       │
           └──────▲──────────────────────────┬────────────────────────────────────▲─────────┘
                  │ comments / labels         │ JQL poll                            │
           ┌──────┴────────────────── Orchestrator (thin, Python) ────────────────┴─────────┐
           │  (issue type, label) → route table → skill → workspace slot / device lock       │
           │  timeouts, retry caps, parallelism, circuit breaker; runner: claude -p | codex   │
           └──┬─────────┬───────────┬────────────┬────────────┬────────────┬───────────┬────┘
              ▼         ▼           ▼            ▼            ▼            ▼           ▼
           triage  bug-analyze  model-enable  feature-spec  implement  review-prep  report
                                                           (+ fixer,   / respond   (open-slide)
                                                          repo-onboard)
              └─────────┴───────────┴─────┬──────┴────────────┴────────────┴───────────┘
                                          ▼
           ┌────────────── dossier/<KEY>/ ──────────────┐     ┌──────────── Knowledge ─────────────┐
           │ ticket.md analysis.md op-gap.md SPEC.md    │ ◀─▶ │ CodeAtlas MCP (code graph, cases,  │
           │ HANDOFF.md device-runs/ review-notes.md    │     │   docs) · Confluence · shared dirs │
           │ deck/ runs/                                │     │ knowledge repo: ops/ lessons/ repos/│
           └────────────────────────────────────────────┘     └─────────────────────────────────────┘
                    │                                │
                    ▼                                ▼
     synced tree: branch loop/<KEY> in owned gits    devices: Android (adb) · Windows on Snapdragon (ssh)
                    │
                    ▼  repo upload --wip (topic = KEY)
                 Gerrit ── Jenkins Verified / Code-Review ──▶ monitor loop (fixer, review-respond)
```

---

## Agents and Routing

Each agent is one skill with explicit inputs, outputs, and permissions.

| Agent (skill) | Trigger (default) | Reads | Writes | Changes code? | Then |
|---|---|---|---|---|---|
| `triage` | new ticket, no `agent:*` label | Jira, `find_case` | Jira comment, label | no | `agent:analyze` or `agent:needs-info` |
| `bug-analyze` ✅ | `agent:analyze` | attachments, whole tree, CodeAtlas, knowledge | `analysis.md`, Jira comment | no | `agent:fix-ready` (human-reviewable) |
| `model-enable` ✅ | Story + `agent:model` | model, converter/partitioner logs, `ops/`, SDK op tables | `SPEC.md`, `op-gap.md` → `implement` | via implement | on-device accuracy + latency evidence |
| `feature-spec` ✅ | Story + `agent:spec` | Jira, Confluence, CodeAtlas | `SPEC.md`, `DESIGN.md`, `IMPLEMENTATION-GUIDE.md`, sub-tasks | no | sub-tasks get `agent:ready` **after human approval** |
| `repo-onboard` ✅ | no overview for an owned git | Jenkinsfile, build files, CodeAtlas | `repos/<git>/overview.md` | no | engineer reviews |
| `implement` | `agent:ready` / `agent:fix-ready` | dossier, overview gates | branch in owned git, Gerrit change | **yes** | `agent:in-review` |
| `review-prep` | change uploaded | diff, dossier | `review-notes.md`, change description | no | reviewers notified |
| `review-respond` / `fixer` | new Gerrit comment / Verified -1 / conflict | Gerrit, Jenkins console log | new patchset on the same change | **yes** | stays `agent:in-review` or `agent:blocked` |
| `report` | manual, or epic done | dossier, Jira, git log | `deck/` (open-slide) | no | human reviews slides |
| `reflect` | end of every run | run summary, dossier | knowledge repo proposals | no | — |

✅ = skill exists in `skills/` (Phase 0).

### Why split bug-analyze from implement?

In this stack the hard part is the **root cause**, not the edit. Splitting them means Phase 1 can run analysis
read-only (zero risk) and measure agent judgment; a human can review between analysis and change; and `reflect`
learns from analysis failures separately from build failures.

---

## Jira State Machine (label-driven)

Agent state lives in labels so no Jira admin change is needed; the Jira status is synced only coarsely.

```
(new) ──triage──▶ agent:needs-info ──(human adds info, removes label)──▶ (triage again)
  │
  └──▶ agent:analyze ──bug-analyze──▶ agent:fix-ready ──implement──▶ agent:in-review ──(merged)──▶ Resolved
                             │                    │                        │
                             └──────────┬─────────┴────────────────────────┘
                                        ▼
                                  agent:blocked (comment says what is missing; human sets the previous label back)

Story ──agent:spec──▶ feature-spec (rounds of Q&A) ──human approves──▶ sub-tasks, each agent:ready ──▶ implement
Story ──agent:model─▶ model-enable (SPEC + op-gap) ──human approves plan──▶ implement ──▶ device verification
```

Rules:
- At most one `agent:*` stage label per ticket; the orchestrator swaps labels in one update.
- A running agent adds `agent:running` and removes it at the end; after a crash the orchestrator clears it on
  timeout (idempotent restarts).
- Only tickets matching the base JQL (assignee or component) are touched.

---

## Workspace

autopilot creates a git worktree per issue; a full Android-manifest tree is too large for that.

```
~/loop-work/
  slots/slot-1/     # full synced tree + build output dirs (kept for incremental builds)
  slots/slot-2/     # writable parallelism = number of slots; start with 1
```

- At task start: `repo start loop/<KEY> <owned project>`; other gits stay at the manifest revision.
- At task end: `repo abandon loop/<KEY>` (after the Gerrit change exists), slot released, build output kept.
- Write access: only owned gits in the slot, its build output, and `dossier/<KEY>/`.
- Read-only stages (triage, bug-analyze, model-enable gap analysis) can share one tree without taking a slot.

### C++ / Python build and test gates

The stack is C++ (runtime, EP op builders, DSP code, FastRPC) and Python (converters, quantizers, ExecuTorch export
and passes, tests).

### Build hosts

```
                 agent (Linux workstation / Linux build host)
                    │ local                         │ ssh + PowerShell, change sent as a patch
                    ▼                               ▼
     Linux x64 build host                    Windows x64 build host
       linux-x64   (native: unit tests)        windows-x64   (native: unit tests)
       linux-arm64 (cross)                     windows-arm64 (cross: vcvarsall x64_arm64 / clang-cl)
       hexagon     (Hexagon SDK)
                    │ artifacts + sha256            │
                    ▼                               ▼
            arm64 Linux devices (adb / ssh)   Windows on Snapdragon devices (ssh)
```

- Fast gates (format, lint, Python tests, C++ unit tests) run on the x64 native build of the host.
- arm64 targets are cross-built on their host; they can only be executed on a device (qemu user mode for
  `linux-arm64` unit tests is optional and never counts as NPU evidence).
- A change in shared code is built on **both** hosts before upload.
- The Windows host keeps its own checkout at the same base revision; the change travels as a patch with a recorded
  hash, so the artifact on the device is traceable to an exact source state.
- Details and pitfalls (LLP64, symbol export, paths, line endings): `skills/references/build-hosts.md`; hosts are
  listed in `build-hosts.yml`.

- Gates are **per git**, discovered by `repo-onboard` from the Jenkinsfile and build files, verified by running
  them, and stored in `knowledge/repos/<git>/overview.md`. Agents never invent build commands.
- `skills/references/cpp-python-gates.md` defines what the gates must cover: every reached target builds, format
  and lint on changed lines (`git clang-format`, ruff/black), clang-tidy / mypy if configured, unit tests (gtest,
  pytest), sanitizer builds when available, ABI check for exported symbols, pybind/nanobind extension rebuilds.
- On-device tests run through the `device` skill.

---

## Gerrit + Jenkins

| autopilot (GitHub) | loop (Gerrit) |
|---|---|
| open a PR | `repo upload --cbr --wip -t` (topic = KEY) |
| cross-repo change | several changes sharing one topic |
| CI checks | Jenkins Verified vote; failure details from the Jenkins console log |
| auto-merge | **never**; a human +2s and submits |
| fixer merges main, never force-pushes | new patchset (amend, keep Change-Id); rebase via Gerrit |
| review comments | Gerrit REST: unresolved comments → reply → resolve |

Commit message: `[KEY] <summary>`, with `Bug: KEY`, `Test: <commands run>`, and the `Change-Id` from the hook.

---

## Dossier

```
dossier/NPU-123/
  ticket.md ticket.json attachments/   # jira.py fetch
  HANDOFF.md        # state, next action, last stage — updated by every stage
  analysis.md       # bug-analyze: symptom, evidence, root cause, proposed fix, confidence
  SPEC.md DESIGN.md IMPLEMENTATION-GUIDE.md   # feature-spec / model-enable (docforge format)
  op-gap.md         # model-enable: op → rung → evidence
  device-runs/      # device skill: one folder per run
  review-notes.md   # review-prep
  deck/             # report (open-slide)
  runs/             # per-run summaries for reflect
```

Dossiers stay on the workstation (`$LOOP_DOSSIER`, git-ignored). Summaries go to Jira; reusable lessons go to the
internal knowledge repo.

---

## Knowledge

loop does not rebuild what the company already has. It adds only the distilled-experience layer.

| Source | Use | How agents use it |
|---|---|---|
| **CodeAtlas MCP** | code graph, semantic search, past cases, docs | `find_case` for similar past bugs; `search_semantic` → `find_symbol` → `get_call_chain` / `get_callees` → `get_source` to trace errors; `get_references` for impact analysis; `find_doc` / `find_knowledge` for design docs |
| **Confluence** | designs, SDK release notes, op support tables | via CodeAtlas `find_doc` or Confluence REST; cite the page URL |
| **Shared folders** | models, test data, old reports | read-only mounts; cite the path |
| **Internal GitHub** | upstream and other teams' code; the knowledge repo itself | git / GitHub MCP |
| **Knowledge repo** (new, internal git) | `ops/` op recipes, `lessons/` bug lessons, `repos/` per-git overviews and gates | every skill greps it first and proposes new pages at the end |

The knowledge repo follows the Karpathy LLM-Wiki / llm_wiki layout (`purpose.md`, `schema.md`, `index.md`,
`log.md`, frontmatter with `sources:`); the template is in `knowledge-template/`. TencentDB Memory Hub is not adopted:
CodeAtlas already covers the code graph, and a file-based knowledge repo is enough for distilled lessons until
multi-user access control is needed.

---

## Devices

- Inventory in `devices.yml`: `os` (android / windows), transport (adb serial / ssh host), SoC, Hexagon arch,
  build or driver version, scratch dir.
- One `flock` lock per device; one agent at a time.
- **Android:** `adb push`/`shell`/`pull`, `LD_LIBRARY_PATH` / `ADSP_LIBRARY_PATH` into scratch, `logcat` + `dmesg`.
- **Windows on Snapdragon:** OpenSSH + PowerShell, `scp` into `C:/loop/<KEY>`, process-scoped `PATH`, `Get-WinEvent`
  for the run's time window, WER dumps; doctor records OS build and NPU driver version.
- Allowed / needs-OK / never lists per OS (e.g. driver install and reboot need OK; flashing, `bcdedit` never).
- Each run leaves `device-runs/<time>-<slug>/` with commands, doctor output, stdout, logs, and a result note.

---

## Orchestrator

Smallest useful version of autopilot's loop:

```
loop:
  for route in config.routes:                       # priority order
    for issue in jira.search(route.jql) not running:
      if route.needs_slot and no free slot: continue
      if route.needs_device and no matching free device: continue
      run_skill(route.skill, issue, slot, runner)   # `claude -p` or `codex exec`, with timeout
  monitor_gerrit()                                  # in-review changes: Verified -1 / new comments / conflicts → fixer
  sleep(poll_interval)
```

- Python, stdlib first, so it runs on the workstation or build server with nothing extra installed
  (`tools/jira.py` already follows this).
- The runner is switchable (`claude -p` / `codex exec`); the skills are the same files.
- Borrowed from autopilot: circuit breaker, retry, timeout + abort, activity log, prompt templating.

---

## Roadmap

| Phase | Content | Automation | Value |
|---|---|---|---|
| **0** | `jira.py`; skills `bug-analyze`, `device`, `model-enable`, `feature-spec`, `repo-onboard`; knowledge template — **all run by hand** (in progress) | manual | usable now; measures skill quality |
| **1** | Orchestrator runs `triage` + `bug-analyze` automatically (read-only, comments only) | read-only auto | zero-risk check of agent judgment |
| **2** | `implement`: change code, pass gates, `repo upload --wip` | write auto | first ticket → change |
| **3** | Gerrit / Jenkins monitor: Verified -1 fixes, review responses, rebases | write auto | fewer review round-trips |
| **4** | `feature-spec` → sub-tasks, `report` slides, `review-prep` | semi-auto (human answers) | full feature flow |
| **5** | `reflect` improves skills; optional planning; optional Memory Hub | self-improving | long-term compounding |
