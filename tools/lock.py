#!/usr/bin/env python3
"""Cross-platform named locks for loop (devices, build-host checkouts, tree slots). Stdlib only.

A lock is a file created atomically under $LOOP_HOME/locks/<name>.lock that records its owner (a Jira key).
It survives across separate shell invocations, which agent tool calls are, and works on Windows and Linux.

  lock.py acquire <name> --owner KEY [--ttl-min 240]   exit 0 if acquired or already held by KEY, 1 if busy
  lock.py release <name> --owner KEY
  lock.py status [<name>]

An expired lock (older than its TTL) can be taken over with --steal-expired; a live lock is never broken.
"""

import argparse
import json
import os
import pathlib
import socket
import sys
import time


def lock_dir():
    return pathlib.Path(os.environ.get("LOOP_LOCKS") or pathlib.Path(os.environ.get("LOOP_HOME", ".")) / "locks")


def _path(name):
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    return lock_dir() / f"{safe}.lock"


def read(name):
    try:
        return json.loads(_path(name).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def expired(info, now=None):
    return (now or time.time()) > info["acquired"] + info["ttl_min"] * 60


def acquire(name, owner, ttl_min=240, steal_expired=False):
    """Return (ok, info). Re-acquiring a lock you hold refreshes it."""
    path = _path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    info = {"name": name, "owner": owner, "host": socket.gethostname(), "acquired": time.time(), "ttl_min": ttl_min}
    current = read(name)
    if current and (current["owner"] == owner or (steal_expired and expired(current))):
        path.write_text(json.dumps(info), encoding="utf-8")
        return True, info
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False, read(name)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(info, f)
    return True, info


def release(name, owner):
    current = read(name)
    if current is None:
        return True
    if current["owner"] != owner:
        return False
    _path(name).unlink()
    return True


def require(name, owner):
    """Exit unless `owner` holds lock `name`. Used by other tools before touching a shared resource."""
    current = read(name)
    if not current or current["owner"] != owner:
        held = f"held by {current['owner']}" if current else "not held"
        sys.exit(f"lock {name} is {held}; run: python tools/lock.py acquire {name} --owner {owner}")


def describe(info):
    age = (time.time() - info["acquired"]) / 60
    state = "EXPIRED" if expired(info) else "held"
    return f"{info['name']}\t{state}\towner={info['owner']}\thost={info['host']}\tage={age:.0f}m\tttl={info['ttl_min']}m"


def main(argv=None):
    p = argparse.ArgumentParser(prog="lock", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("acquire")
    s.add_argument("name")
    s.add_argument("--owner", required=True)
    s.add_argument("--ttl-min", type=int, default=240)
    s.add_argument("--steal-expired", action="store_true")
    s = sub.add_parser("release")
    s.add_argument("name")
    s.add_argument("--owner", required=True)
    s = sub.add_parser("status")
    s.add_argument("name", nargs="?")
    args = p.parse_args(argv)

    if args.cmd == "acquire":
        ok, info = acquire(args.name, args.owner, args.ttl_min, args.steal_expired)
        print(("acquired " if ok else "busy     ") + describe(info))
        return 0 if ok else 1
    if args.cmd == "release":
        if release(args.name, args.owner):
            print(f"released {args.name}")
            return 0
        print(f"not released: {describe(read(args.name))}")
        return 1
    names = [args.name] if args.name else sorted(f.stem for f in lock_dir().glob("*.lock"))
    for n in names:
        info = read(n)
        print(describe(info) if info else f"{n}\tfree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
