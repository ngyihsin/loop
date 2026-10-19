# Build hosts and cross-compilation

Two kinds of build server, each cross-compiling for arm64:

| Build host | Native build (runs unit tests here) | Cross targets | Typical toolchain (confirm per git in `repos/<git>/overview.md`) |
|---|---|---|---|
| **Windows x64** | `windows-x64` | `windows-arm64` | MSVC ARM64 cross tools (`vcvarsall.bat x64_arm64`, CMake `-A ARM64`) or `clang-cl --target=aarch64-pc-windows-msvc` |
| **Linux x64** | `linux-x64` | `linux-arm64` (+ Hexagon DSP if the git has DSP code) | `aarch64-linux-gnu-*` GCC or `clang --target=aarch64-linux-gnu` with a sysroot; CMake `-DCMAKE_TOOLCHAIN_FILE=...`; Hexagon SDK tools |

Hosts are listed in `$LOOP_HOME/build-hosts.toml` (copy `build-hosts.example.toml`). The host the agent runs on
has `transport = "local"`; the other one is driven over ssh. Development starts on **Windows x64**; the Linux x64
host is added later.

## Where each gate runs

- **Format, lint, Python tests (pure Python), C++ unit tests:** on the host-native x64 build. Fastest, and catches
  logic bugs. Use it as the first gate whenever the git can build its tests for x64.
- **arm64 build:** on the host that owns that target (Windows → `windows-arm64`, Linux → `linux-arm64`). It must
  compile and link cleanly; it cannot run there.
- **arm64 execution:** on a device through the `device` skill. `windows-arm64` has no emulator on x64: use a
  Windows on Snapdragon device. `linux-arm64` unit tests may also run under `qemu-aarch64` user mode on the Linux
  host (`CMAKE_CROSSCOMPILING_EMULATOR`); useful, but never on-device evidence for NPU/DSP behavior.
- **Python with native extensions:** pure-Python logic is tested on x64; the arm64 extension (wheel tag
  `win_arm64` / `linux_aarch64`) is cross-built and tested on device.

A change in shared code (headers, common C++ libraries, Python packages used on both OSes) reaches **both** hosts.
While only the Windows host is set up, record in HANDOFF.md that the Linux build is still owed, and do not mark
the change ready for review until it is done (or the engineer waives it).

## Working on the Windows x64 host (agent runs here)

- Shell: Codex / Claude Code run PowerShell. Write commands for PowerShell (`$env:VAR`, `;` instead of `&&` on
  Windows PowerShell 5, backslashes or forward slashes in paths). Use `python` (or `py -3`).
- Source: the `repo` launcher has limited Windows support, so owned gits are usually plain `git` clones (or
  checked out by the team's own sync script). Branch with `git switch -c loop/<KEY>`; upload to Gerrit with
  `git push origin HEAD:refs/for/<target-branch>%wip,topic=<KEY>` (the `commit-msg` hook adds `Change-Id`;
  install it once per clone).
- MSVC: load the environment in the **same** command that builds, because each tool call is a new process:
  `cmd /c "call ""<path>\vcvarsall.bat"" x64_arm64 && cmake --build build-arm64 --target <target>"`.
  For the x64 native build use `x64` instead of `x64_arm64`.
- Long paths and line endings: enable long paths (`git config core.longpaths true`) and keep the repo's
  `core.autocrlf` setting as the team uses it; never commit CRLF churn.

## Driving the other host over ssh

Whichever host the agent is not on (Linux x64 now; Windows x64 if the agent later moves to Linux):

- Keep a checkout on that host at the **same base revision**. Move the change as a patch, not by copying files:
  `git diff <base>..loop/<KEY> > <KEY>.patch`, `scp` it, then on the remote `git apply --check` and `git apply` on a
  clean branch `loop/<KEY>`. Record the patch sha256 in the dossier.
- Lock the remote checkout: `python tools/lock.py acquire build-<host-id> --owner <KEY>`.
- Windows remote: OpenSSH + PowerShell, same rules as above. Linux remote: plain sh over ssh.
- Clean up when the ticket is done: on the remote, `git switch <base-branch> && git branch -D loop/<KEY>`; release
  the lock.

## Artifacts to devices

Push build outputs with `device.py push`; it records each file's sha256. Also record in the run's `result.md`:
build host, toolchain version, base revision + patch sha256. A device result is evidence only for the artifact it
names.

## Cross-platform pitfalls to check in review

- Windows is LLP64 (`long` is 32-bit); use fixed-width types for anything crossing an API, file, or RPC boundary.
- Symbol export (`__declspec(dllexport)` / visibility attributes) and calling conventions; `.def` files.
- Paths: separators, case-insensitive file systems, `MAX_PATH`, CRLF line endings in generated or checked-in test
  data.
- `#ifdef _WIN32` / `__linux__` / `__aarch64__` / `_M_ARM64` branches: the change must compile on every branch it
  touches.
- Cross-compiled test binaries must not be registered to run on the build host unless an emulator is configured.
