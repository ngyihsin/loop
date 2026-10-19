# C++ / Python change gates

The authoritative commands for a git come from its `repos/<git>/overview.md` (derived from the Jenkinsfile). This
list says what those commands must cover and what to look for when reading a diff. Run the cheap gates first.

## Both languages
- [ ] The repro / acceptance test fails before the change and passes after (keep both outputs in the dossier).
- [ ] Only files in `$LOOP_OWNED` changed; no unrelated formatting churn (`git diff --stat` is small and on-topic).
- [ ] The same checks Jenkins runs for this git pass locally on the committed head — at least the stages that
      do not need special hardware.

## C++
- [ ] Builds for **every target the change reaches**, not only the host. Typical targets in this stack: Linux
      x86_64 host tools, Android aarch64 (NDK), Windows ARM64 (MSVC or clang-cl), Hexagon DSP (Hexagon SDK
      toolchain). A change under a shared header usually reaches all of them.
- [ ] Compiler warnings: no new warnings at the git's warning level (`-Werror` often only in CI).
- [ ] `clang-format` with the git's `.clang-format`, limited to changed lines (`git clang-format`).
- [ ] `clang-tidy` if the git has a config.
- [ ] Unit tests (gtest / catch2 / ctest — whatever the git uses) on host; on-device tests via the `device` skill
      when the code only runs on target.
- [ ] Sanitizers (ASan / UBSan) on host tests if the git supports a sanitizer build — the cheapest way to catch
      buffer-size and lifetime bugs before the device does.
- [ ] ABI: exported symbols and public headers unchanged unless the ticket asks for it (compare `nm -D` /
      `dumpbin /exports` output, or the git's ABI check).
- [ ] DSP-side code: no dynamic allocation in hot paths, alignment and VTCM limits respected, sizes from the host
      validated.

## Python
- [ ] Formatter and linter the git uses (`ruff` / `black` / `flake8` / `pylint`), changed files only.
- [ ] Type checker if configured (`mypy` / `pyright`).
- [ ] `pytest` for the touched package; for converter / partitioner / op-builder changes, the per-op tests plus
      at least one model-level test.
- [ ] Python version(s) the git supports (check `pyproject.toml` / CI matrix); no new dependencies without a
      reason in the commit message.
- [ ] C++ extension modules (pybind11 / nanobind): rebuild the extension and run its Python tests — a header
      change can break the binding without breaking the C++ build.

## Commit message (Gerrit)
```
[<KEY>] <imperative summary, <= 72 chars>

<why, and the approach if non-obvious>

Bug: <KEY>
Test: <exact commands that were run and passed>
Change-Id: <kept by the commit-msg hook; never edit>
```
