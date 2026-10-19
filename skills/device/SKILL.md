---
name: device
description: Safely run commands, copy models/binaries, and collect logs on Qualcomm test devices — Windows on Snapdragon (arm64) over ssh, arm64 Linux boards over ssh or adb, Android over adb — through tools/device.py, with a per-device lock and recorded evidence. Works from a Windows or Linux workstation. Use whenever another loop skill needs to reproduce a bug, run a model, profile, or verify a fix on target hardware.
---

# device

Every on-device action in loop goes through `$LOOP_HOME/tools/device.py` so that (a) two agents never drive the
same device, (b) nothing outside `<scratch>/<KEY>/` is modified, and (c) every run leaves evidence in the dossier.
The tool works the same from a Windows x64 or Linux x64 machine (it needs `ssh`/`scp` and/or `adb` on PATH).

Commands below are written for any shell; on Windows use `python` (or `py -3`), on Linux `python3`, and
`$env:LOOP_HOME` instead of `$LOOP_HOME` in PowerShell.

## 1. Pick and lock a device

```
python $LOOP_HOME/tools/device.py list
python $LOOP_HOME/tools/lock.py acquire device-<id> --owner <KEY>
```

Pick the entry matching the ticket's OS, SoC, and Hexagon arch (`devices.toml`). If none matches, say so instead of
silently using a different chip. If the lock is busy, wait or pick another matching device; never break a live lock
(`--steal-expired` only takes over a lock past its TTL).

## 2. Doctor

```
python $LOOP_HOME/tools/device.py doctor <id> --key <KEY>
```

Prints OS build, SoC, and (Windows) NPU / Hexagon driver versions. Check they match the ticket; a result from the
wrong build or driver is not evidence. `run` repeats the doctor and stores it with every run.

## 3. Copy artifacts in

```
python $LOOP_HOME/tools/device.py push <id> --key <KEY> <model.bin> <build-output-dir> ...
```

Files land in `<scratch>/<KEY>/`; the sha256 of each is recorded and copied into every later run's `device.txt`.
Push the exact artifacts the build produced (see `skills/references/build-hosts.md` for provenance).

## 4. Run

```
python $LOOP_HOME/tools/device.py run <id> --key <KEY> --slug <short-name> --repeat <N> -- <command>
```

The command runs inside `<scratch>/<KEY>/` — PowerShell on Windows devices, sh on Linux / Android. The tool writes
`$LOOP_DOSSIER/<KEY>/device-runs/<time>-<slug>/` with `cmd.txt`, `device.txt` (doctor + artifact hashes),
`stdout-<i>.txt`, `result.json` (exit code and duration per run), and platform logs:

| OS | Logs collected |
|---|---|
| Windows | System + Application events since the run started (`events.txt`) |
| Android | `logcat.txt` (cleared before the run), `dmesg.txt` |
| Linux | `dmesg.txt`, `journal.txt` |

Framework log files written into the work dir: fetch them with
`device.py pull <id> --key <KEY> <path-in-workdir> <run-dir>`.

Then write `result.md` in the run folder: expected, observed, reproduces yes/no, rate (`--repeat` > 1 for flaky
bugs; one pass proves little). For performance: warm-up runs, iteration count, power mode, and whether a laptop was
on AC power.

Library search paths go in the command itself so they apply to that process only — PowerShell:
`$env:PATH = "$PWD;$env:PATH"; .\qnn-net-run.exe ...`; sh: `LD_LIBRARY_PATH=$PWD ADSP_LIBRARY_PATH=$PWD ./qnn-net-run ...`.

## Needs the user's explicit OK

- Windows: reboot, installing / updating / removing drivers (`pnputil`), registry writes under `HKLM`, system-wide
  ETW / WPR traces, power plan changes, writing outside the scratch dir.
- Android / Linux: reboot, `adb root` / `remount`, `setenforce`, persistent properties, replacing anything under
  `/vendor`, `/system`, `/odm`, `/dsp`, `/usr/lib`.

## Never

Flash, wipe, factory reset, `bcdedit`, disable driver signing, or delete outside `<scratch>/<KEY>/`.

## 5. Finish

When the ticket is done (not between stages — the next stage may reuse the files):

```
python $LOOP_HOME/tools/device.py clean <id> --key <KEY>
python $LOOP_HOME/tools/lock.py release device-<id> --owner <KEY>
```

Between stages within a ticket, release the lock anyway if you stop working, so others can use the device.
Never delete dossier run folders.
