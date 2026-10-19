---
name: repo-onboard
description: Learn how one owned git in the manifest is built, tested, and released — from its Jenkinsfile, CMake / Android.bp / pyproject / build scripts, and CodeAtlas — and write the knowledge page repos/<git>/overview.md that other loop skills use as their build and test gates. Use for "/repo-onboard <git path>", "onboard this repo", or when another skill finds no overview for a git it must change.
---

# repo-onboard

Input: a git path inside the synced tree. Output: `$LOOP_KNOWLEDGE/repos/<git>/overview.md` (template:
`$LOOP_HOME/knowledge-template/repos/_TEMPLATE.md`), marked `reviewed_by: unreviewed` until the engineer confirms.
Read `$LOOP_HOME/skills/CONVENTIONS.md` first. This skill only reads code and runs build/test commands; it never
changes the git.

The engineer may not know every command by heart; the CI definition does. Treat **Jenkins as the source of
truth**, and the engineer as the reviewer of what you found.

## 1. Read what CI runs

1. Find the CI definition: `Jenkinsfile*`, `ci/`, `.jenkins/`, `jenkins/`, groovy shared-library calls, or scripts
   those call (`build.sh`, `run_tests.py`, `Makefile` targets). If the Jenkinsfile lives elsewhere (shared job
   repo), search for the git name with `search_semantic` / `find_doc`.
2. For each CI stage, record: name, target platform, the exact command, the container/toolchain it needs, and
   whether it needs hardware (device, DSP simulator).

## 2. Read the build system

- C++: `CMakeLists.txt` / `CMakePresets.json`, toolchain files, Bazel `BUILD`, Hexagon SDK makefiles, Visual
  Studio / MSBuild files. For each target (`linux-x64`, `linux-arm64`, `windows-x64`, `windows-arm64`, Hexagon)
  record **which build host** builds it (Linux x64 or Windows x64 — see `skills/references/build-hosts.md`), the
  toolchain and environment setup (toolchain file, sysroot, `vcvarsall.bat x64_arm64`), and options that select
  backend (HTP / CPU / GPU).
- Python: `pyproject.toml` / `setup.py` / `requirements*.txt`, test config (`pytest.ini`, `conftest.py`, `tox.ini`),
  lint config (`ruff.toml`, `.flake8`, `mypy.ini`), extension builds (pybind11 / nanobind).
- Style: `.clang-format`, `.clang-tidy`, `.editorconfig`, pre-commit config.

## 3. Map the module

Use CodeAtlas: `search_semantic` for the git's main responsibilities, `find_symbol` / `get_references` on its
public API to learn who consumes it (other gits, frameworks), and `get_callees` from the main entry points to see
which other gits it depends on. Record the top-level directories and what each is for.

## 4. Prove the commands

Run the cheapest command for each gate on the build host that owns it — the incremental build of one target per
host, one unit test file on the x64 native build, the formatter in check mode. The Windows host is driven over ssh
as described in `build-hosts.md`. Record wall-clock time. A command you did not run is
written as `unverified:` in the page. Do not run anything that needs a device here; list it for the `device`
skill instead.

## 5. Write overview.md

Sections (from the template): what it is and who consumes it; module map; **Build** (per target: command, time,
prerequisites); **Test** (host unit tests, Python tests, on-device tests — each with exact command and whether
verified); **Gates** (the ordered list `implement` must pass, cheapest first, mapped to
`skills/references/cpp-python-gates.md`); pitfalls (anything slow, flaky, or surprising you hit).

Then show the page to the engineer, ask them to correct it, and set `reviewed_by` when they confirm. Add it to
`index.md` and append to `log.md`.
