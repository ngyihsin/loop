---
name: model-enable
description: Enable a model on the Qualcomm NPU (HTP) through QNN / SNPE / ExecuTorch QNN backend / ONNX Runtime QNN EP — find the ops that are unsupported or fall back, choose a rewrite (decomposition into supported ops, builder mapping, op package), implement it, and prove accuracy and performance on device. Use for "/model-enable <JIRA-KEY>", "enable model X on HTP", "op Y is not supported".
---

# model-enable

Input: a Jira key for a model-enablement request. Output in `$LOOP_DOSSIER/<KEY>/`: `SPEC.md` (target and
acceptance), `op-gap.md` (every unsupported op and its decision), then the change itself via the `implement`
stage, with accuracy and perf evidence. Read `$LOOP_HOME/skills/CONVENTIONS.md` first.

The goal is the model running **fully on HTP within the accuracy and latency budget**, with the smallest change.
A rewrite that runs but silently loses accuracy is a failure, so numerical verification is part of done.

## 1. Pin the target (SPEC.md)

Ask the user or reporter only what the ticket does not say; propose defaults and let them correct:

- Model, source format (PyTorch / ONNX / TFLite), file location, input shapes (static? dynamic dims?)
- Path: QNN direct, SNPE, ExecuTorch QNN backend, or ORT QNN EP — and the SDK version
- SoC / Hexagon arch, precision (fp16, int8/int16 with which calibration data), batch
- Acceptance: accuracy metric and threshold vs. the fp32 reference (e.g. cosine similarity / max-abs-error per
  output, or task metric), latency target, "no CPU fallback" or an allowed fallback list
- Reference implementation to compare against (CPU EP, PyTorch eager, fp32 QNN CPU backend)

Write these as SPEC.md (docforge structure: Goals, Non-Goals, Requirements, Success Criteria, Open Questions).
Do not start step 2 with open questions that change the target.

## 2. Find the gap (op-gap.md)

Run the conversion / lowering for the chosen path with verbose logging and collect, per op:

- Ops the converter or partitioner rejects, and ops left on CPU (fallback / partition breaks).
- Ops that convert but fail graph finalize on HTP for this arch (shape rank, dtype, attribute limits).
- Ops that run but cause layout conversions or partition splits that dominate latency.

Then for each distinct op, check before designing anything:
1. `$LOOP_KNOWLEDGE/ops/<op>.md` — has the team already solved this op? Reuse the recipe.
2. The SDK op definitions / supported-op tables for this arch and version (Confluence / SDK docs) — maybe a
   newer SDK or a different attribute combination is supported.
3. Upstream: has ExecuTorch / ORT already added a builder or decomposition in a newer version? (CodeAtlas or
   internal GitHub search.)

## 3. Decide per op — cheapest viable rung first

| Rung | What | When |
|---|---|---|
| 0 | Config / version change (newer SDK, different precision, static shapes, export option) | the op is supported under other settings |
| 1 | Builder mapping: map the framework op to an existing QNN op with translated params/layout | a QNN op exists with equivalent semantics |
| 2 | Graph rewrite / decomposition into supported ops (math-equivalent) | no single QNN op, but a composition exists |
| 3 | Custom op package (HTP op package / SNPE UDO) | no reasonable composition, or composition too slow |
| 4 | Allowed CPU fallback | only if SPEC allows it and latency still meets target |

Where the code for rungs 1–2 typically lives (confirm in your tree with CodeAtlas — paths move between versions):
- ExecuTorch QNN backend: op builders under `backends/qualcomm/builders/`, graph passes / decompositions under
  `backends/qualcomm/_passes/`, partitioner support lists.
- ONNX Runtime QNN EP: op builders under `onnxruntime/core/providers/qnn/builder/opbuilder/`.
- QNN / SNPE converters: converter op translations, or a model-level rewrite before conversion (e.g. ONNX graph
  surgery script kept with the model).

For each op write in `op-gap.md`: op, attributes/shapes seen in this model, rung chosen, the exact equivalence
(formula), expected numeric effect (exact, or bounded error from e.g. fp16 accumulation), perf expectation,
and why cheaper rungs do not work. A decomposition must state its edge cases: broadcasting, negative axes,
dtype promotion, quantization encodings of intermediate tensors, dynamic shapes.

## 4. Prove each rewrite in isolation, then the model

1. **Unit:** a single-op (or tiny subgraph) test that compares the rewritten graph against the reference on random
   and edge-case inputs, using the repo's existing test pattern (e.g. the framework's per-op tests). This is the
   regression test that lands with the change.
2. **Model accuracy on device** (via the `device` skill): full model vs. reference with the SPEC metric. If it
   misses, dump per-layer outputs and find the first diverging layer before changing anything.
3. **Performance on device:** latency (state warm-up and iteration count), number of partitions / CPU ops (target: 0
   unless allowed), and profiling output for the rewritten region.

## 5. Implement and hand off

Implementation follows the `implement` stage rules (owned git only, branch `loop/<KEY>`, Gerrit WIP upload, topic
`<KEY>`). If the fix spans several gits (e.g. builder in one, test model in another), use one Gerrit topic.

Finish with:
- `HANDOFF.md` with the evidence table (op → rung → unit test → accuracy → latency), next action.
- A knowledge entry per newly solved op: `$LOOP_KNOWLEDGE/ops/<op>.md` (template in
  `knowledge-template/ops/_TEMPLATE.md`) — this is the most valuable reusable asset this skill produces.
- Proposed Jira comment + labels via `jira.py` (dry-run first).
