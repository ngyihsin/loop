# Build hosts and cross-compilation

Two kinds of build server, each cross-compiling for arm64:

| Build host | Native build (runs unit tests here) | Cross targets | Typical toolchain (confirm per git in `repos/<git>/overview.md`) |
|---|---|---|---|
| **Linux x64** | `linux-x64` | `linux-arm64` (+ Hexagon DSP if the git has DSP code) | `aarch64-linux-gnu-*` GCC or `clang --target=aarch64-linux-gnu` with a sysroot; CMake `-DCMAKE_TOOLCHAIN_FILE=...`; Hexagon SDK tools |
| **Windows x64** | `windows-x64` | `windows-arm64` | MSVC ARM64 cross tools (`vcvarsall.bat x64_arm64`, CMake `-A ARM64`) or `clang-cl --target=aarch64-pc-windows-msvc` |

Hosts are listed in `$LOOP_HOME/build-hosts.yml` (copy `build-hosts.example.yml`).

## Where each gate runs

- **Format, lint, Python tests (pure Python), C++ unit tests:** on the host-native x64 build. Fastest, and catches
  logic bugs. Use it as the first gate whenever the git can build its tests for x64.
- **arm64 build:** on the host that owns that target (Linux → `linux-arm64`, Windows → `windows-arm64`). It must
  compile and link cleanly; it cannot run there.
- **arm64 execution:** on a device through the `device` skill. `linux-arm64` tests may also run under
  `qemu-aarch64` user mode with the sysroot if the host has it (`CMAKE_CROSSCOMPILING_EMULATOR`); it is useful for
  unit tests but never counts as on-device evidence for NPU/DSP behavior. `windows-arm64` has no emulator on x64:
  use a Windows on Snapdragon device.
- **Python with native extensions:** pure-Python logic is tested on x64; the arm64 extension (wheel tag
  `linux_aarch64` / `win_arm64`) is cross-built and tested on device.

A change in shared code (headers, common C++ libraries, Python packages used on both OSes) reaches **both** hosts:
build it on both before uploading.

## Driving the Windows build host

The agent runs on the Linux side (workstation or Linux build server); the Windows build host is driven over
OpenSSH + PowerShell, like Windows devices.

- Keep a checkout on the Windows host at the **same base revision** as the agent's tree. Move the change as a
  patch, not by copying files: `git diff <base>..loop/<KEY> > <KEY>.patch`, `scp` it, then on Windows
  `git apply --check` and `git apply` on a clean branch `loop/<KEY>`. Record the patch sha256.
- Load the MSVC environment in the **same** command that builds, since each ssh call is a new process:
  `cmd /c "call vcvarsall.bat x64_arm64 && cmake --build build-arm64 --target <target>"`.
- Take a lock for the host's checkout (`$LOOP_HOME/locks/<host-id>.lock`, same `flock` pattern as the device skill).
- Clean up: `git checkout <base> && git branch -D loop/<KEY>` on the Windows checkout when the ticket is done.

## Artifacts to devices

Copy build outputs to the device from the build host, or through the agent machine. Record in the device run's
`device.txt`: build host, toolchain version, base revision + patch sha256, and the sha256 of every copied binary.
A device result is evidence only for the artifact it names.

## Cross-platform pitfalls to check in review

- Windows is LLP64 (`long` is 32-bit); use fixed-width types for anything crossing an API, file, or RPC boundary.
- Symbol export (`__declspec(dllexport)` / visibility attributes) and calling conventions; `.def` files.
- Paths: separators, case-insensitive file systems, `MAX_PATH` (enable long paths on the build host), CRLF line
  endings (`core.autocrlf`) in generated or checked-in test data.
- `#ifdef _WIN32` / `__linux__` / `__aarch64__` / `_M_ARM64` branches: the change must compile on every branch it
  touches.
- Cross-compiled test binaries must not be registered to run on the build host unless an emulator is configured.
