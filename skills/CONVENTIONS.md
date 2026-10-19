# loop conventions (read before running any loop skill)

You are one stage in a pipeline that turns Jira tickets into analysis, Gerrit changes, and reports for a
Qualcomm AI / NPU framework team (QNN, SNPE, Hexagon NN, ExecuTorch QNN backend, ONNX Runtime QNN EP, FastRPC).
Another agent — or a human — picks up after you, reading only Jira and the dossier. Write for them.

## Environment

| Variable | Meaning |
|---|---|
| `LOOP_HOME` | checkout of the loop repo (tools, skills) |
| `LOOP_DOSSIER` | dossier root, default `$LOOP_HOME/dossier` (local, never pushed) |
| `LOOP_KNOWLEDGE` | knowledge repo checkout (internal git; layout from `$LOOP_HOME/knowledge-template`) |
| `JIRA_URL`, `JIRA_TOKEN`, `JIRA_EMAIL` | used by `$LOOP_HOME/tools/jira.py` |
| `LOOP_OWNED` | space-separated repo-relative paths of the gits you may modify |

## Sources of truth, in the order you consult them

1. **Jira** — `python3 $LOOP_HOME/tools/jira.py fetch <KEY>` puts `ticket.md` and attachments in `$LOOP_DOSSIER/<KEY>/`.
2. **Dossier** — `$LOOP_DOSSIER/<KEY>/HANDOFF.md` says what previous stages did. Read it first if it exists.
3. **Knowledge repo** — `$LOOP_KNOWLEDGE/index.md`, then `lessons/`, `ops/`, `repos/<git>/`. Grep for the error
   string, op name, or symbol before you start reasoning from scratch.
4. **CodeAtlas MCP** — code graph, callers/callees, semantic search across the whole manifest. Prefer it over
   blind `grep -r` on the Android tree; use grep to confirm a specific file.
5. **Confluence / shared folder / internal GitHub** — design docs, SDK release notes, op support tables. Cite the
   page URL or file path you used.

## Hard rules

- Write code only inside `$LOOP_OWNED` gits, on a branch named `loop/<KEY>`. Read anything.
- Never `+2`, submit, or abandon a Gerrit change; never force-push; never `repo sync` a tree another stage is using.
- Jira writes go through `jira.py`, which is dry-run by default. Show the user the dry-run output and add
  `--apply` only after they agree, unless `LOOP_AUTONOMY` contains the stage name (e.g. `bug-analyze`).
- Device access only through the `device` skill (it takes the lock and keeps you out of protected partitions).
- Every claim in an output document cites evidence: a log file and line, a command and its output, a code
  location (`path:line` at a revision), or a doc link. Unverified ideas go under "Hypotheses", never "Root cause".
- When you cannot proceed (missing log, no device, ambiguous requirement), stop, write what is missing into
  HANDOFF.md, and propose `agent:blocked` or `agent:needs-info`. A clear block beats a guess.

## Dossier layout

```
$LOOP_DOSSIER/<KEY>/
  ticket.md ticket.json attachments/   # from jira.py fetch
  HANDOFF.md        # every stage updates: Status, What I did, Evidence, Next action, Open questions
  analysis.md       # bug-analyze
  SPEC.md DESIGN.md IMPLEMENTATION-GUIDE.md   # feature-spec / model-enable
  op-gap.md         # model-enable
  device-runs/      # device skill: one folder per run with cmd, stdout, logcat, artifacts
  review-notes.md   # review-prep
  runs/<date>-<stage>.md   # short run summary for reflect
```

## HANDOFF.md format

```markdown
# <KEY> handoff
**Stage:** <skill name>  **Updated:** <date>  **Status:** done | blocked | needs-info | in-progress
## What I did
## Evidence (links into this dossier)
## Next action (who/which stage, exact command)
## Open questions
```

## Before you finish

1. Update HANDOFF.md.
2. Write `runs/<YYYY-MM-DD>-<stage>.md`: goal, outcome, time spent per phase, what was slow or wrong, and what knowledge would have saved time.
3. Propose (do not silently apply) the Jira comment and label change via `jira.py` dry-run.
4. If you learned something reusable (error signature → cause, op → rewrite recipe), propose an entry for `$LOOP_KNOWLEDGE` in the run summary.
