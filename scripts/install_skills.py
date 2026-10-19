#!/usr/bin/env python3
"""Link loop skills into Codex and Claude Code user skill folders. Works on Windows and Linux.

  python scripts/install_skills.py [codex] [claude]     (default: both)

Linux/macOS: symlinks. Windows: symlink if allowed (Developer Mode), otherwise a directory junction (no admin
needed). Either way the installed skill follows this checkout, so `git pull` updates it.
"""

import os
import pathlib
import subprocess
import sys

LOOP_HOME = pathlib.Path(__file__).resolve().parent.parent
TARGETS = {
    "codex": pathlib.Path(os.environ.get("CODEX_HOME", pathlib.Path.home() / ".codex")) / "skills",
    "claude": pathlib.Path.home() / ".claude" / "skills",
}


def link(src, dest):
    if dest.is_symlink():
        dest.unlink()
    elif getattr(dest, "is_junction", lambda: False)():  # Python 3.12+
        os.rmdir(dest)  # removes the junction, not its target
    elif dest.exists():
        sys.exit(f"{dest} exists and is not a link; remove it first")
    try:
        os.symlink(src, dest, target_is_directory=True)
        return "symlink"
    except OSError:
        if os.name != "nt":
            raise
    subprocess.run(["cmd", "/c", "mklink", "/J", str(dest), str(src)], check=True, capture_output=True)
    return "junction"


def main(argv):
    names = argv or list(TARGETS)
    for name in names:
        if name not in TARGETS:
            sys.exit(f"unknown target {name}; choose from {', '.join(TARGETS)}")
        dest_root = TARGETS[name]
        dest_root.mkdir(parents=True, exist_ok=True)
        for skill in sorted((LOOP_HOME / "skills").iterdir()):
            if (skill / "SKILL.md").is_file():
                kind = link(skill, dest_root / skill.name)
                print(f"{name}: {dest_root / skill.name} -> {skill} ({kind})")
    shell_hint = "setx LOOP_HOME" if os.name == "nt" else "export LOOP_HOME="
    print(f"\nSet LOOP_HOME to {LOOP_HOME} (e.g. `{shell_hint} {LOOP_HOME}`), plus LOOP_KNOWLEDGE, LOOP_OWNED, JIRA_URL, JIRA_TOKEN.")


if __name__ == "__main__":
    main(sys.argv[1:])
