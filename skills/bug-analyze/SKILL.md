---
name: bug-analyze
description: Root-cause a Jira bug in the Qualcomm NPU stack (QNN / SNPE / Hexagon NN / ExecuTorch QNN backend / ONNX Runtime QNN EP / FastRPC; C++ and Python; Android and Windows on Snapdragon) from logs, code, and on-device reproduction, and write an evidence-backed analysis.md. Read-only on code. Use for "/bug-analyze <JIRA-KEY>", "analyze this bug", "find the root cause of <KEY>".
---

# bug-analyze

Input: one Jira key. Output: `$LOOP_DOSSIER/<KEY>/analysis.md`, an updated `HANDOFF.md`, and a proposed Jira
comment. You do not change product code. Read `$LOOP_HOME/skills/CONVENTIONS.md` first.

The finding is the root cause, not the symptom. "HTP graph finalize fails" is a symptom; "op Foo's builder emits
a rank-5 tensor, HTP supports rank ≤ 4 for Foo since SDK x.y, see `path:line`" is a root cause.

## 1. Collect

1. `python $LOOP_HOME/tools/jira.py fetch <KEY>`; read `ticket.md`, then `HANDOFF.md` if a prior stage left one.
2. Pin the environment. Fill this table from the ticket, attachments, or by asking the reporter
   (propose `agent:needs-info` if anything critical is missing):

   | Field | Value | Source |
   |---|---|---|
   | OS: Android (build fingerprint) or Windows on Snapdragon (OS build, NPU driver version) | | |
   | SoC / Hexagon arch (e.g. v73/v75/v79) | | |
   | Device build / meta build | | |
   | SDK + version (QNN / SNPE / Hexagon SDK) | | |
   | Framework path (QNN direct, SNPE, ExecuTorch, ORT QNN EP, Hexagon NN) | | |
   | Backend (HTP / CPU / GPU / DSP) and precision (fp16 / int8 / int16 / mixed) | | |
   | Model + where to get it | | |
   | Exact command / app and repro rate | | |
   | Last known good version | | |

3. Search what the team already knows before reading code:
   - CodeAtlas `find_case` with the error string and symptom — past cases with the same signature.
   - CodeAtlas `find_knowledge` / `find_doc` for the failing API, op, or feature (known limitations, SDK notes).
   - grep `$LOOP_KNOWLEDGE/lessons/` and `$LOOP_KNOWLEDGE/ops/` for the error string, op name, and API.
   - Jira duplicates: `jira.py search 'text ~ "<error string>" ORDER BY updated DESC' --limit 20`.

## 2. Classify the failure layer

Pick the layer from evidence in the logs; it decides where you read code. If the logs cannot tell, that is
the first thing to fix (step 3, raise log level).

| Layer | Typical evidence | Where to look |
|---|---|---|
| Python front end / tooling | Python traceback in converter, quantizer, export, or test scripts | the Python package named in the traceback; check the Python and dependency versions first |
| Model conversion / export | converter traceback, "not supported" during `qnn-*-converter`, `snpe-*-to-dlc`, ExecuTorch `to_edge`/`to_backend`, ORT session creation | converter / op builder / partitioner code |
| Partitioning / delegation | ops falling back to CPU, graph split into many partitions, unexpected latency | ExecuTorch QNN partitioner + op builders; ORT QNN EP op builders and capability checks |
| Graph build / finalize | `QnnGraph_finalize` / `graphFinalize` errors, op validation failures, VTCM or spill-fill messages | op parameters and tensor shapes/dtypes the builder emits vs. QNN op definition for that arch |
| Execution / runtime | `graphExecute` errors, timeouts, wrong output only on device | runtime glue, buffer registration, shared memory (rpcmem / dmabuf) |
| FastRPC / DSP transport | Android: `adsprpc`/`cdsprpc` errors in logcat; Windows: errors from the FastRPC / NPU driver in the System event log; `remote_handle*_open` failures, session errors | IDL, stub/skel, PD type (signed/unsigned), DSP library search path (`ADSP_LIBRARY_PATH` on Android; DLL / skel location on Windows) |
| DSP crash | Android: subsystem restart (SSR) / cDSP crash in `dmesg`; Windows: driver reset / device error events, call hangs then fails | DSP-side skel / op package; get the crash dump and symbolize |
| Host native crash | Android: tombstone; Windows: WER dump / access violation exit code (`0xC0000005`) | symbolize with the matching build's symbols (PDB on Windows), then read the frame |
| Platform difference | works on Android, fails on Windows (or vice versa) | path / DLL loading, `#ifdef _WIN32` branches, `size_t`/`long` width (LLP64 on Windows), file encoding, line endings |
| Numerical accuracy | output mismatch vs. CPU/fp32 reference, quantized model drift | quantization encodings, per-layer diff, op precision |
| Performance | latency regression, power | profiling output, clock / power votes, partition count, data layout conversions |

## 3. Reproduce (when the ticket has repro steps)

Use the `device` skill for all adb/ssh work. Reproduce on the closest matching device and SDK version before
reasoning about code — a reproduction turns guesses into experiments.

- Reproduce at the reported version first. If it does not reproduce, record that with the exact command and
  output, then check environment differences (build, SDK, model file hash) before concluding anything.
- Raise log verbosity on the failing layer (the framework's log-level option, ORT verbose logging, profiling level
  detailed) and capture the platform logs around the run (the device skill does this for Android and Windows).
- For regressions with a known good version: bisect versions or commits; that is often faster than reading code.
- For accuracy bugs: dump per-layer outputs on device and on the reference, and find the first diverging layer.

Store every run under `device-runs/` (the device skill does this). If no device is available, say so in
HANDOFF.md and continue with log + code analysis, marking conclusions as lower confidence.

## 4. Narrow down

Work like a scientist, not a reader of code:

1. List candidate hypotheses (3–5), each with the observation that would confirm or kill it.
2. Pick the experiment that splits the remaining space the most; run it; record the result.
3. Trace with CodeAtlas: `search_semantic` for the log message → `find_symbol` on the function that emits it →
   `get_call_chain` from the API the user called → `get_source` on each hop; `get_references` to see other
   callers that would hit the same bug. Record `path:line@revision` for each hop.
4. For Python: reproduce the traceback on the workstation first if possible — it is much faster than a device.
   For C++: a host build with ASan/UBSan of the failing unit or a minimal reproducer often turns a device crash into
   a precise stack trace.
5. Stop when one mechanism explains all observations, and you can name the code that causes it.

## 5. Write analysis.md

```markdown
# <KEY> analysis
**Confidence:** high | medium | low — why
**Layer:** <from step 2>   **Owned git affected:** <path or "not ours: <team/git>">

## Environment        (the table from step 1)
## Symptom            (exact error lines, with attachment file:line)
## Reproduction       (command, result, link to device-runs/<run>; or "not reproduced: ...")
## Root cause         (mechanism + code location; only verified facts)
## Evidence           (numbered; each item = observation + where it came from)
## Hypotheses ruled out (and the evidence that ruled each out)
## Proposed fix       (minimal change, files, risk, how to verify; alternatives if any)
## Test plan          (the repro that must pass after the fix + regression tests)
## Not ours?          (if the cause is in another team's git: which, and what to tell them)
```

## 6. Hand off

1. Update `HANDOFF.md` (Next action: `implement` for an owned-git fix, or route to the owning team).
2. Propose the Jira comment (in English) — a short summary of root cause, confidence, and proposed fix with a pointer to the
   analysis — via `jira.py comment <KEY> --file <summary.md>` (dry-run first).
3. Propose labels: `--remove agent:analyze --add agent:fix-ready` (or `agent:needs-info` / `agent:blocked`).
4. Write `runs/<date>-bug-analyze.md` and a candidate `lessons/` entry for the knowledge repo.
