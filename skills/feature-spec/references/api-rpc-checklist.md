# API / FastRPC change checklist

Answer each item in DESIGN.md. "N/A because ..." is fine; silence is not.

## Interface
- [ ] Exact signature(s), including ownership of every pointer/buffer and who frees it.
- [ ] Error model: return codes, which are new, how they map to framework-level errors and messages.
- [ ] Threading: which threads may call it, re-entrancy, locking, cancellation.
- [ ] Versioning: how a caller detects support (capability query / version bump); behavior on old DSP images or old host libs.

## FastRPC specifics (when a new remote method or interface is added)
- [ ] IDL change: new method vs. new interface; argument directions (in / rout / inrout), sequence/buffer sizes.
- [ ] Stub/skel regeneration and where generated files live; both sides built from the same IDL revision.
- [ ] Host ↔ DSP version skew: new host + old skel and old host + new skel — what happens, and is it tested?
- [ ] Domain and PD: which DSP (cDSP / aDSP / …), signed vs. unsigned PD, session/handle lifecycle (open/close, multiple handles).
- [ ] Memory: copies vs. shared buffers (rpcmem / dmabuf), cache maintenance, alignment, max sizes, zero-copy expectations.
- [ ] Latency budget per call; batching if called per inference / per layer.
- [ ] Failure: DSP restart (SSR) mid-call, timeouts, what the host returns, and how the session recovers.

## Compatibility and rollout
- [ ] ABI stability of exported symbols; header changes; deprecations.
- [ ] Which frameworks consume it (QNN / SNPE / ExecuTorch / ORT EP) and in which order they adopt it.
- [ ] Feature flag or config gate, default value.

## Verification
- [ ] Unit tests on each side; a host-to-DSP end-to-end test via the `device` skill.
- [ ] Negative tests: bad args, oversized buffers, closed handle, unsupported version.
- [ ] Perf measurement method (iterations, warm-up, clocks) and the number it must meet.
- [ ] Security: input validation on the DSP side for all host-provided sizes and offsets.
