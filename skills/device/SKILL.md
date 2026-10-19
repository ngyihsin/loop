---
name: device
description: Safely run commands, copy models/binaries, and collect logs on a Qualcomm test device — Android over adb, or Windows on Snapdragon (arm64) laptops over ssh — with a per-device lock and recorded evidence. Use whenever another loop skill needs to reproduce a bug, run a model, profile, or verify a fix on target hardware.
---

# device

Every on-device action in loop goes through this skill so that (a) two agents never drive the same device,
(b) nothing outside a scratch directory is modified, and (c) every run leaves evidence in the dossier.

## Device inventory

Devices are listed in `$LOOP_HOME/devices.yml` (copy `devices.example.yml`). Each entry names the `os`
(`android` or `windows`), transport (`adb` serial or `ssh` host), SoC, Hexagon arch, build, and a scratch
directory. Pick the entry matching the ticket's SoC / arch / OS; if none matches, say so instead of silently using
a different chip.

## Lock

Hold the lock for the whole session on that device:

```bash
mkdir -p "$LOOP_HOME/locks"
exec 9>"$LOOP_HOME/locks/<device-id>.lock"
flock -n 9 || { echo "device <device-id> busy"; exit 1; }
```

If it is busy, wait or pick another matching device. Never break someone else's lock.

## Doctor (run first, and whenever results look odd)

Record the output in the run folder; a result from the wrong build or driver is not evidence.

Android (adb):
```bash
adb -s <serial> get-state
adb -s <serial> shell getprop ro.build.fingerprint
adb -s <serial> shell getprop ro.soc.model
```

Windows on Snapdragon (ssh, OpenSSH server with PowerShell; wrap commands in `powershell -NoProfile -Command`
if the default shell is cmd):
```bash
ssh <host> 'powershell -NoProfile -Command "Get-CimInstance Win32_OperatingSystem | Select Caption,Version,BuildNumber,OSArchitecture"'
ssh <host> 'powershell -NoProfile -Command "Get-CimInstance Win32_Processor | Select Name"'
# NPU / DSP driver versions (names vary by platform; filter on Qualcomm / Hexagon / NPU)
ssh <host> 'powershell -NoProfile -Command "Get-CimInstance Win32_PnPSignedDriver | ? { $_.DeviceName -match ''Hexagon|NPU|Qualcomm'' } | Select DeviceName,DriverVersion,DriverDate"'
```

## Allowed

| | Android | Windows |
|---|---|---|
| Scratch dir | `<scratch>/<KEY>/` e.g. `/data/local/tmp/loop/<KEY>` | `<scratch>\<KEY>\` e.g. `C:\loop\<KEY>` |
| Copy files in/out | `adb push` / `adb pull` | `scp` (use forward slashes: `<host>:C:/loop/<KEY>/`) |
| Library search path | `LD_LIBRARY_PATH`, `ADSP_LIBRARY_PATH` pointing into scratch | `$env:PATH` set for the one process; DLLs next to the exe in scratch |
| Logs | `logcat -c` then `logcat -d`, `dmesg` | stdout/stderr, framework log files, `Get-WinEvent` (System / Application, filtered to the run's time window), WER crash dumps if enabled |
| Debug settings | non-persistent `setprop`, restored afterwards | process-scoped environment variables only |

## Needs the user's explicit OK

- Android: reboot, `adb root` / `remount`, `setenforce`, persistent `setprop persist.*`, replacing anything under
  `/vendor`, `/system`, `/odm`, `/dsp`.
- Windows: reboot, installing / updating / removing drivers (`pnputil`), registry writes under `HKLM`, enabling
  ETW / WPR traces system-wide, changing power plans, copying into `C:\Windows` or driver store.

## Never

- Flash, wipe, factory reset, `bcdedit`, disable driver signing, or delete outside `<scratch>/<KEY>/`.

## Run recipe

Make one folder per run: `$LOOP_DOSSIER/<KEY>/device-runs/<YYYYMMDD-HHMMSS>-<slug>/`, containing:

- `device.txt` — device id, doctor output, SDK / libraries used (with hashes of copied files)
- `cmd.sh` — the exact commands, runnable again
- `stdout.txt` plus the platform logs (`logcat.txt`, `dmesg.txt` / `events.txt`, framework log files)
- `result.md` — expected, observed, reproduces yes/no, run N of M

Android:
```bash
RUN=$LOOP_DOSSIER/<KEY>/device-runs/$(date +%Y%m%d-%H%M%S)-<slug>; mkdir -p "$RUN"
adb -s <serial> logcat -c
adb -s <serial> shell 'cd <scratch>/<KEY> && <command>' 2>&1 | tee "$RUN/stdout.txt"
adb -s <serial> logcat -d > "$RUN/logcat.txt"
adb -s <serial> shell dmesg > "$RUN/dmesg.txt" 2>/dev/null || true
```

Windows:
```bash
RUN=$LOOP_DOSSIER/<KEY>/device-runs/$(date +%Y%m%d-%H%M%S)-<slug>; mkdir -p "$RUN"
START=$(ssh <host> 'powershell -NoProfile -Command "(Get-Date).ToString(''o'')"' | tr -d '\r')
ssh <host> "powershell -NoProfile -Command \"cd C:/loop/<KEY>; <command>\"" 2>&1 | tee "$RUN/stdout.txt"
ssh <host> "powershell -NoProfile -Command \"Get-WinEvent -FilterHashtable @{LogName='System','Application'; StartTime='$START'} -ErrorAction SilentlyContinue | Format-List TimeCreated,ProviderName,Id,LevelDisplayName,Message\"" > "$RUN/events.txt"
scp -r "<host>:C:/loop/<KEY>/logs" "$RUN/" 2>/dev/null || true
```

Flaky or intermittent bugs: run N times (state N) and report the rate; one pass proves little.
Performance numbers: state warm-up runs, iteration count, power mode, and whether the laptop was on AC power.

## Cleanup

Remove `<scratch>/<KEY>/` when the ticket is done (not between stages — the next stage may reuse it), restore any
setting you changed, release the lock (`exec 9>&-`). Never delete the dossier run folders.
