---
name: device
description: Safely run commands, push models/binaries, and collect logs on a Qualcomm test device over adb or ssh, with a per-device lock and recorded evidence. Use whenever another loop skill needs to reproduce a bug, run a model, profile, or verify a fix on target hardware.
---

# device

Every on-device action in loop goes through this skill so that (a) two agents never drive the same device,
(b) nothing outside a scratch directory is modified, and (c) every run leaves evidence in the dossier.

## Device inventory

Devices are listed in `$LOOP_HOME/devices.yml` (copy `devices.example.yml`). Each entry names the transport
(`adb` serial or `ssh` host), SoC, Hexagon arch, build, and a scratch directory. Pick the entry matching the
ticket's SoC/arch; if none matches, say so instead of silently using a different chip.

## Lock

Hold the lock for the whole session on that device:

```bash
mkdir -p "$LOOP_HOME/locks"
exec 9>"$LOOP_HOME/locks/<device-id>.lock"
flock -n 9 || { echo "device <device-id> busy"; exit 1; }
```

If it is busy, wait or pick another matching device. Never break someone else's lock.

## Doctor (run first, and whenever results look odd)

```bash
# adb
adb -s <serial> get-state
adb -s <serial> shell getprop ro.build.fingerprint
adb -s <serial> shell getprop ro.soc.model
adb -s <serial> shell 'ls <scratch>' 
# ssh: the same checks via ssh <host> ...
```

Record the fingerprint in the run folder; a result from the wrong build is not evidence.

## Allowed

- Create and use `<scratch>/<KEY>/` (e.g. `/data/local/tmp/loop/<KEY>/`); push models, binaries, libraries there.
- Run binaries from scratch with `LD_LIBRARY_PATH` / `ADSP_LIBRARY_PATH` pointing into scratch.
- Read logs: `logcat`, `dmesg`, `/proc`, `/sys` reads, profiling output.
- `logcat -c` before a run so the log covers only that run.
- Set non-persistent debug properties needed for logging, and restore them afterwards.

## Needs the user's explicit OK

- Reboot, `adb root`/`remount`, `setenforce`, persistent `setprop persist.*`.
- Replacing anything under `/vendor`, `/system`, `/odm`, `/dsp` (e.g. trying a rebuilt DSP library in place).

## Never

- Flash (`fastboot`, `dd` to block devices), wipe, factory reset, or delete outside `<scratch>/<KEY>/`.

## Run recipe

Make one folder per run: `$LOOP_DOSSIER/<KEY>/device-runs/<YYYYMMDD-HHMMSS>-<slug>/`, containing:

- `device.txt` — device id, fingerprint, SoC, SDK/libraries used (with hashes of pushed files)
- `cmd.sh` — the exact commands, runnable again
- `stdout.txt`, `logcat.txt`, `dmesg.txt` — captured around the run
- `result.md` — one paragraph: expected, observed, reproduces yes/no, run N of M

```bash
RUN=$LOOP_DOSSIER/<KEY>/device-runs/$(date +%Y%m%d-%H%M%S)-<slug>; mkdir -p "$RUN"
adb -s <serial> logcat -c
adb -s <serial> shell 'cd <scratch>/<KEY> && <command>' 2>&1 | tee "$RUN/stdout.txt"
adb -s <serial> logcat -d > "$RUN/logcat.txt"
adb -s <serial> shell dmesg > "$RUN/dmesg.txt" 2>/dev/null || true
```

Flaky or intermittent bugs: run N times (state N) and report the rate; one pass proves little.

## Cleanup

Remove `<scratch>/<KEY>/` when the ticket is done (not between stages — the next stage may reuse it), restore any
property you changed, release the lock (`exec 9>&-`). Never delete the dossier run folders.
