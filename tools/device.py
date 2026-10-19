#!/usr/bin/env python3
"""Run things on test devices and record evidence. Cross-platform (runs on Windows or Linux), stdlib only.

Inventory: $LOOP_HOME/devices.toml (see devices.example.toml). Transports: adb (Android / Linux boards),
ssh to Windows (OpenSSH + PowerShell), ssh to Linux, and local (the machine this runs on; used for tests).

  device.py list
  device.py doctor <id> --key KEY                 print device identity (build, SoC, driver)
  device.py push   <id> --key KEY <file>...       copy into <scratch>/<KEY>/ and record sha256
  device.py pull   <id> --key KEY <remote> <dir>  copy <scratch>/<KEY>/<remote> to a local dir
  device.py run    <id> --key KEY --slug S [--repeat N] -- <command>
                                                  run in <scratch>/<KEY>/, capture stdout and platform logs into
                                                  $LOOP_DOSSIER/<KEY>/device-runs/<time>-<slug>/
  device.py clean  <id> --key KEY                 delete <scratch>/<KEY>/ on the device

Every command except `list` requires the lock `device-<id>` held by KEY (tools/lock.py).
"""

import argparse
import base64
import datetime
import hashlib
import json
import os
import pathlib
import platform
import shlex
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import lock  # noqa: E402

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    sys.exit("device.py needs Python 3.11+ (tomllib)")


def loop_home():
    return pathlib.Path(os.environ.get("LOOP_HOME", pathlib.Path(__file__).resolve().parent.parent))


def dossier_root():
    return pathlib.Path(os.environ.get("LOOP_DOSSIER") or loop_home() / "dossier")


def load_inventory(path=None):
    path = pathlib.Path(path or os.environ.get("LOOP_DEVICES") or loop_home() / "devices.toml")
    if not path.exists():
        sys.exit(f"device: no inventory at {path}; copy devices.example.toml")
    with open(path, "rb") as f:
        return {d["id"]: d for d in tomllib.load(f).get("device", [])}


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


class Device:
    def __init__(self, cfg, key):
        self.cfg, self.key = cfg, key
        self.os = cfg["os"]
        self.workdir = f"{cfg['scratch'].rstrip('/')}/{key}"

    # --- transport primitives: shell(command) -> CompletedProcess, copy_in, copy_out ---
    def shell(self, command, cwd=False):
        t = self.cfg["transport"]
        if t == "local":
            if cwd:
                return sh(command, shell=True, cwd=self.workdir)
            return sh(command, shell=True)
        if self.os == "windows":
            script = f"Set-Location '{self.workdir}'; {command}" if cwd else command
            encoded = base64.b64encode(script.encode("utf-16-le")).decode()
            return sh(["ssh", self.cfg["host"], f"powershell -NoProfile -NonInteractive -EncodedCommand {encoded}"])
        posix = f"cd {shlex.quote(self.workdir)} && {command}" if cwd else command
        if t == "adb":
            return sh(["adb", "-s", self.cfg["serial"], "shell", posix])
        if t == "ssh":
            return sh(["ssh", self.cfg["host"], posix])
        sys.exit(f"device: unknown transport {t}")

    def mkdir(self):
        if self.cfg["transport"] == "local":
            pathlib.Path(self.workdir).mkdir(parents=True, exist_ok=True)
            return None
        if self.os == "windows":
            return self.shell(f"New-Item -ItemType Directory -Force -Path '{self.workdir}' | Out-Null")
        return self.shell(f"mkdir -p {shlex.quote(self.workdir)}")

    def copy_in(self, local):
        t = self.cfg["transport"]
        if t == "adb":
            return sh(["adb", "-s", self.cfg["serial"], "push", str(local), self.workdir + "/"])
        if t == "ssh":
            return sh(["scp", "-r", str(local), f"{self.cfg['host']}:{self.workdir}/"])
        return _local_copy(pathlib.Path(local), pathlib.Path(self.workdir))

    def copy_out(self, remote, local_dir):
        src = f"{self.workdir}/{remote}"
        t = self.cfg["transport"]
        if t == "adb":
            return sh(["adb", "-s", self.cfg["serial"], "pull", src, str(local_dir)])
        if t == "ssh":
            return sh(["scp", "-r", f"{self.cfg['host']}:{src}", str(local_dir)])
        return _local_copy(pathlib.Path(src), pathlib.Path(local_dir))

    # --- platform knowledge ---
    def doctor_commands(self):
        if self.cfg["transport"] == "local":
            return []
        if self.os == "windows":
            return [
                "Get-CimInstance Win32_OperatingSystem | Format-List Caption,Version,BuildNumber,OSArchitecture",
                "Get-CimInstance Win32_Processor | Format-List Name",
                "Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.DeviceName -match 'Hexagon|NPU|Qualcomm' }"
                " | Format-Table DeviceName,DriverVersion,DriverDate -AutoSize | Out-String -Width 200",
            ]
        if self.os == "android":
            return ["getprop ro.build.fingerprint", "getprop ro.soc.model", "getprop ro.board.platform"]
        return ["uname -a", "cat /etc/os-release 2>/dev/null | head -5", "cat /proc/device-tree/model 2>/dev/null; echo"]

    def clock(self):
        if self.cfg["transport"] == "local":
            return datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        cmd = "(Get-Date).ToString('o')" if self.os == "windows" else "date -u +%Y-%m-%dT%H:%M:%SZ"
        return self.shell(cmd).stdout.strip()

    def clear_logs(self):
        if self.os == "android":
            self.shell("logcat -c")

    def collect_logs(self, run_dir, since):
        logs = {}
        if self.os == "android":
            logs["logcat.txt"] = self.shell("logcat -d").stdout
            logs["dmesg.txt"] = self.shell("dmesg 2>/dev/null").stdout
        elif self.os == "windows":
            logs["events.txt"] = self.shell(
                f"Get-WinEvent -FilterHashtable @{{LogName='System','Application'; StartTime=[datetime]'{since}'}}"
                " -ErrorAction SilentlyContinue | Format-List TimeCreated,ProviderName,Id,LevelDisplayName,Message"
                " | Out-String -Width 300"
            ).stdout
        elif self.cfg["transport"] != "local":
            logs["dmesg.txt"] = self.shell("dmesg 2>/dev/null | tail -500").stdout
            logs["journal.txt"] = self.shell(f"journalctl --since '{since}' --no-pager 2>/dev/null | tail -2000").stdout
        for name, text in logs.items():
            (run_dir / name).write_text(text, encoding="utf-8")


def _local_copy(src, dest_dir):
    try:
        if src.is_dir():
            shutil.copytree(src, dest_dir / src.name, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dest_dir / src.name)
        return subprocess.CompletedProcess([], 0, "", "")
    except OSError as e:
        return subprocess.CompletedProcess([], 1, "", str(e))


def state_file(key, dev_id):
    return dossier_root() / key / "device-state" / f"{dev_id}.json"


def sha256(path):
    h = hashlib.sha256()
    for f in sorted(p for p in ([path] if path.is_file() else path.rglob("*")) if p.is_file()):
        h.update(f.read_bytes())
    return h.hexdigest()


def cmd_list(inv, args):
    for d in inv.values():
        held = lock.read(f"device-{d['id']}")
        who = f"locked by {held['owner']}" if held else "free"
        print(f"{d['id']}\t{d['os']}\t{d['transport']}\t{d.get('soc', '')}\t{d.get('hexagon_arch', '')}\t{who}")


def cmd_doctor(dev, args):
    out = [f"local: {platform.platform()} {platform.machine()}"] if dev.cfg["transport"] == "local" else []
    for c in dev.doctor_commands():
        r = dev.shell(c)
        out.append(f"$ {c}\n{r.stdout}{r.stderr}")
    text = "\n".join(out)
    print(text)
    return text


def cmd_push(dev, args):
    dev.mkdir()
    sf = state_file(args.key, dev.cfg["id"])
    sf.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(sf.read_text()) if sf.exists() else {"pushed": {}}
    for f in map(pathlib.Path, args.files):
        r = dev.copy_in(f)
        if r.returncode:
            sys.exit(f"device: push {f} failed: {r.stderr.strip()}")
        state["pushed"][f.name] = {"source": str(f.resolve()), "sha256": sha256(f), "at": now_iso()}
        print(f"pushed {f} -> {dev.workdir}/")
    sf.write_text(json.dumps(state, indent=2), encoding="utf-8")


def cmd_pull(dev, args):
    pathlib.Path(args.dest).mkdir(parents=True, exist_ok=True)
    r = dev.copy_out(args.remote, args.dest)
    if r.returncode:
        sys.exit(f"device: pull failed: {r.stderr.strip()}")
    print(f"pulled {dev.workdir}/{args.remote} -> {args.dest}")


def cmd_run(dev, args):
    if not args.command:
        sys.exit("device: run needs a command after --")
    command = " ".join(args.command)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = dossier_root() / args.key / "device-runs" / f"{stamp}-{args.slug}"
    run_dir.mkdir(parents=True, exist_ok=False)
    dev.mkdir()

    sf = state_file(args.key, dev.cfg["id"])
    pushed = json.loads(sf.read_text())["pushed"] if sf.exists() else {}
    doctor = cmd_doctor(dev, args)
    (run_dir / "device.txt").write_text(
        f"device: {json.dumps(dev.cfg)}\nworkdir: {dev.workdir}\n\n## doctor\n{doctor}\n"
        f"## pushed artifacts\n{json.dumps(pushed, indent=2)}\n", encoding="utf-8")
    (run_dir / "cmd.txt").write_text(
        f"python tools/device.py run {dev.cfg['id']} --key {args.key} --slug {args.slug} --repeat {args.repeat} -- {command}\n",
        encoding="utf-8")

    since = dev.clock()
    dev.clear_logs()
    results = []
    for i in range(1, args.repeat + 1):
        t0 = time.monotonic()
        r = dev.shell(command, cwd=True)
        results.append({"run": i, "exit": r.returncode, "seconds": round(time.monotonic() - t0, 3)})
        (run_dir / f"stdout-{i}.txt").write_text(r.stdout + ("\n--- stderr ---\n" + r.stderr if r.stderr else ""),
                                                 encoding="utf-8")
        print(f"run {i}/{args.repeat}: exit {r.returncode} in {results[-1]['seconds']}s")
    dev.collect_logs(run_dir, since)
    (run_dir / "result.json").write_text(json.dumps({"command": command, "since": since, "runs": results}, indent=2),
                                         encoding="utf-8")
    failed = sum(1 for x in results if x["exit"])
    print(f"{failed}/{len(results)} runs exited non-zero; evidence in {run_dir}")
    print("write result.md there: expected, observed, reproduces yes/no, rate")


def cmd_clean(dev, args):
    if dev.cfg["transport"] == "local":
        shutil.rmtree(dev.workdir, ignore_errors=True)
        print(f"cleaned {dev.workdir}")
        return
    if dev.os == "windows":
        r = dev.shell(f"Remove-Item -Recurse -Force '{dev.workdir}' -ErrorAction SilentlyContinue")
    else:
        r = dev.shell(f"rm -rf {shlex.quote(dev.workdir)}")
    print(f"cleaned {dev.workdir} (exit {r.returncode})")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    p = argparse.ArgumentParser(prog="device", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--inventory")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    for name in ("doctor", "push", "pull", "run", "clean"):
        s = sub.add_parser(name)
        s.add_argument("id")
        s.add_argument("--key", required=True)
        if name == "push":
            s.add_argument("files", nargs="+")
        if name == "pull":
            s.add_argument("remote")
            s.add_argument("dest")
        if name == "run":
            s.add_argument("--slug", required=True)
            s.add_argument("--repeat", type=int, default=1)
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    if "--" in argv:
        i = argv.index("--")
        argv, command = argv[:i], argv[i + 1:]
    args = p.parse_args(argv)
    args.command = command

    inv = load_inventory(args.inventory)
    if args.cmd == "list":
        return cmd_list(inv, args)
    if args.id not in inv:
        sys.exit(f"device: unknown id {args.id}; known: {', '.join(inv)}")
    lock.require(f"device-{args.id}", args.key)
    dev = Device(inv[args.id], args.key)
    {"doctor": cmd_doctor, "push": cmd_push, "pull": cmd_pull, "run": cmd_run, "clean": cmd_clean}[args.cmd](dev, args)


if __name__ == "__main__":
    main()
