#!/usr/bin/env python3
"""Minimal Jira CLI for loop agents. Stdlib only.

Environment:
  JIRA_URL      e.g. https://jira.company.com (self-hosted Data Center/Server) or https://x.atlassian.net (Cloud)
  JIRA_TOKEN    Personal Access Token (Data Center) or API token (Cloud)
  JIRA_USER     optional; when set, use Basic auth user:token (Cloud email, or DC username if PATs are disabled)
                instead of Bearer PAT

Every command that writes to Jira prints the request and does nothing unless --apply is given.
"""

import argparse
import base64
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

FIELDS = "summary,description,status,labels,components,issuetype,priority,assignee,reporter,fixVersions,versions,attachment,comment,issuelinks,parent,subtasks,created,updated"


class Jira:
    def __init__(self, url, token, user=None):
        self.url = url.rstrip("/")
        if user:
            cred = base64.b64encode(f"{user}:{token}".encode()).decode()
            self.auth = f"Basic {cred}"
        else:
            self.auth = f"Bearer {token}"
        self.cloud = urllib.parse.urlparse(self.url).hostname.endswith(".atlassian.net")

    def request(self, method, path, body=None, raw=False):
        url = path if path.startswith("http") else self.url + path
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", self.auth)
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = resp.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:2000]
            sys.exit(f"jira: {method} {path} -> HTTP {e.code}: {detail}")
        if raw:
            return payload
        return json.loads(payload) if payload else None

    def issue(self, key):
        return self.request("GET", f"/rest/api/2/issue/{q(key)}?fields={FIELDS}")

    def search(self, jql, limit):
        params = urllib.parse.urlencode({"jql": jql, "maxResults": limit, "fields": "summary,status,labels,issuetype,priority,assignee,updated"})
        # Jira Cloud retired /search in favour of /search/jql; Data Center still uses /search.
        path = "/rest/api/2/search/jql" if self.cloud else "/rest/api/2/search"
        return self.request("GET", f"{path}?{params}")["issues"]


def q(key):
    return urllib.parse.quote(key, safe="")


def text(value):
    """Descriptions are plain text in API v2; tolerate ADF dicts just in case."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def render_issue(issue):
    f = issue["fields"]
    name = lambda x: (x or {}).get("name") or (x or {}).get("displayName") or ""
    lines = [
        f"# {issue['key']}: {f.get('summary', '')}",
        "",
        f"- Type: {name(f.get('issuetype'))}",
        f"- Status: {name(f.get('status'))}",
        f"- Priority: {name(f.get('priority'))}",
        f"- Assignee: {name(f.get('assignee'))}",
        f"- Reporter: {name(f.get('reporter'))}",
        f"- Labels: {', '.join(f.get('labels') or [])}",
        f"- Components: {', '.join(name(c) for c in f.get('components') or [])}",
        f"- Affects: {', '.join(name(v) for v in f.get('versions') or [])}",
        f"- Fix versions: {', '.join(name(v) for v in f.get('fixVersions') or [])}",
        f"- Updated: {f.get('updated', '')}",
    ]
    if f.get("parent"):
        lines.append(f"- Parent: {f['parent']['key']}")
    for link in f.get("issuelinks") or []:
        other = link.get("outwardIssue") or link.get("inwardIssue") or {}
        rel = link["type"].get("outward" if "outwardIssue" in link else "inward", "")
        lines.append(f"- Link: {rel} {other.get('key', '')} {other.get('fields', {}).get('summary', '')}")
    lines += ["", "## Description", "", text(f.get("description")), "", "## Attachments", ""]
    for a in f.get("attachment") or []:
        lines.append(f"- {a['filename']} ({a.get('size', 0)} bytes, {a.get('created', '')})")
    lines += ["", "## Comments", ""]
    for c in (f.get("comment") or {}).get("comments", []):
        lines += [f"### {name(c.get('author'))} @ {c.get('created', '')}", "", text(c.get("body")), ""]
    return "\n".join(lines)


def cmd_show(j, args):
    issue = j.issue(args.key)
    if args.json:
        print(json.dumps(issue, indent=2, ensure_ascii=False))
    else:
        print(render_issue(issue))


def cmd_search(j, args):
    for i in j.search(args.jql, args.limit):
        f = i["fields"]
        print(f"{i['key']}\t{f['status']['name']}\t{','.join(f.get('labels') or [])}\t{f['summary']}")


def safe_filename(name):
    """Attachment names may contain characters Windows rejects."""
    base = pathlib.PurePosixPath(name.replace("\\", "/")).name
    return "".join("_" if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in base).rstrip(". ") or "attachment"


def cmd_fetch(j, args):
    """Download issue + attachments into a dossier directory (idempotent)."""
    out = pathlib.Path(args.dossier) / args.key
    att_dir = out / "attachments"
    att_dir.mkdir(parents=True, exist_ok=True)
    issue = j.issue(args.key)
    (out / "ticket.md").write_text(render_issue(issue), encoding="utf-8")
    (out / "ticket.json").write_text(json.dumps(issue, indent=2, ensure_ascii=False), encoding="utf-8")
    for a in issue["fields"].get("attachment") or []:
        target = att_dir / safe_filename(a["filename"])
        if target.exists() and target.stat().st_size == a.get("size"):
            print(f"skip   {target}")
            continue
        if a.get("size", 0) > args.max_mb * 1024 * 1024:
            print(f"TOO BIG {a['filename']} ({a['size']} bytes) — download manually if needed")
            continue
        target.write_bytes(j.request("GET", a["content"], raw=True))
        print(f"saved  {target}")
    print(f"wrote  {out / 'ticket.md'}")


def write(j, args, method, path, body):
    if not args.apply:
        print(f"[dry-run] {method} {path}\n{json.dumps(body, indent=2, ensure_ascii=False)}\n(re-run with --apply to send)")
        return
    j.request(method, path, body)
    print(f"ok     {method} {path}")


def cmd_comment(j, args):
    body = pathlib.Path(args.file).read_text(encoding="utf-8") if args.file else args.text
    if not body:
        sys.exit("jira: comment needs --text or --file")
    write(j, args, "POST", f"/rest/api/2/issue/{q(args.key)}/comment", {"body": body})


def cmd_label(j, args):
    ops = [{"add": l} for l in args.add] + [{"remove": l} for l in args.remove]
    if not ops:
        sys.exit("jira: label needs --add and/or --remove")
    write(j, args, "PUT", f"/rest/api/2/issue/{q(args.key)}", {"update": {"labels": ops}})


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # Windows consoles may not encode every character
    p = argparse.ArgumentParser(prog="jira", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show", help="print an issue as markdown")
    s.add_argument("key")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("search", help="JQL search, one issue per line")
    s.add_argument("jql")
    s.add_argument("--limit", type=int, default=50)
    s.set_defaults(fn=cmd_search)

    s = sub.add_parser("fetch", help="save ticket.md, ticket.json and attachments into <dossier>/<KEY>/")
    s.add_argument("key")
    s.add_argument("--dossier", default=os.path.join(os.environ.get("LOOP_HOME", "."), "dossier"))
    s.add_argument("--max-mb", type=int, default=500)
    s.set_defaults(fn=cmd_fetch)

    s = sub.add_parser("comment", help="add a comment (dry-run unless --apply)")
    s.add_argument("key")
    s.add_argument("--text")
    s.add_argument("--file")
    s.add_argument("--apply", action="store_true")
    s.set_defaults(fn=cmd_comment)

    s = sub.add_parser("label", help="add/remove labels (dry-run unless --apply)")
    s.add_argument("key")
    s.add_argument("--add", action="append", default=[])
    s.add_argument("--remove", action="append", default=[])
    s.add_argument("--apply", action="store_true")
    s.set_defaults(fn=cmd_label)

    args = p.parse_args(argv)
    url, token = os.environ.get("JIRA_URL"), os.environ.get("JIRA_TOKEN")
    if not url or not token:
        sys.exit("jira: set JIRA_URL and JIRA_TOKEN (and JIRA_USER for Basic auth)")
    args.fn(Jira(url, token, os.environ.get("JIRA_USER") or os.environ.get("JIRA_EMAIL")), args)


if __name__ == "__main__":
    main()
