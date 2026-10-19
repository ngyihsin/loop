"""Tests for tools/jira.py against a local fake Jira. Run: python3 -m unittest tools/test_jira.py"""

import contextlib
import io
import json
import os
import pathlib
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import jira  # noqa: E402

ISSUE = {
    "key": "NPU-1",
    "fields": {
        "summary": "HTP graph finalize fails on model X",
        "description": "qnn-net-run returns error 6020",
        "status": {"name": "Open"},
        "labels": ["agent:analyze"],
        "issuetype": {"name": "Bug"},
        "attachment": [{"filename": "logcat.txt", "size": 5, "content": "/secure/attachment/1/logcat.txt"}],
        "comment": {"comments": [{"author": {"displayName": "Alice"}, "created": "2026-10-01", "body": "repro on SM8750"}]},
    },
}


class Fake(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        Fake.calls.append(("GET", self.path, self.headers["Authorization"]))
        if self.path.startswith("/rest/api/2/issue/NPU-1"):
            self._send(200, json.dumps(ISSUE).encode())
        elif self.path.startswith("/secure/attachment/1/"):
            self._send(200, b"hello", "text/plain")
        elif self.path.startswith("/rest/api/2/search"):
            self._send(200, json.dumps({"issues": [ISSUE]}).encode())
        else:
            self._send(404, b"{}")

    def _write(self):
        n = int(self.headers.get("Content-Length", 0))
        Fake.calls.append((self.command, self.path, json.loads(self.rfile.read(n))))
        self._send(201, b"{}")

    do_POST = do_PUT = _write


class JiraTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        os.environ["JIRA_URL"] = f"http://127.0.0.1:{cls.server.server_port}"
        os.environ["JIRA_TOKEN"] = "t"
        os.environ.pop("JIRA_USER", None)
        os.environ.pop("JIRA_EMAIL", None)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        Fake.calls.clear()

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            jira.main(list(argv))
        return out.getvalue()

    def test_show_renders_markdown_with_bearer_auth(self):
        out = self.run_cli("show", "NPU-1")
        self.assertIn("# NPU-1: HTP graph finalize fails", out)
        self.assertIn("repro on SM8750", out)
        self.assertEqual(Fake.calls[0][2], "Bearer t")

    def test_fetch_downloads_attachments_idempotently(self):
        with tempfile.TemporaryDirectory() as d:
            self.run_cli("fetch", "NPU-1", "--dossier", d)
            self.assertEqual((pathlib.Path(d) / "NPU-1/attachments/logcat.txt").read_bytes(), b"hello")
            out = self.run_cli("fetch", "NPU-1", "--dossier", d)
            self.assertIn("skip", out)

    def test_safe_filename_for_windows(self):
        self.assertEqual(jira.safe_filename('trace 10:30 "a".txt'), "trace 10_30 _a_.txt")
        self.assertEqual(jira.safe_filename("dir\\sub/log?.txt"), "log_.txt")

    def test_writes_are_dry_run_by_default(self):
        out = self.run_cli("label", "NPU-1", "--add", "agent:fix-ready", "--remove", "agent:analyze")
        self.assertIn("[dry-run] PUT", out)
        self.assertEqual(Fake.calls, [])

    def test_apply_sends_label_update(self):
        self.run_cli("label", "NPU-1", "--add", "agent:fix-ready", "--apply")
        self.assertEqual(Fake.calls, [("PUT", "/rest/api/2/issue/NPU-1", {"update": {"labels": [{"add": "agent:fix-ready"}]}})])

    def test_basic_auth_and_cloud_detection(self):
        j = jira.Jira("https://acme.atlassian.net", "t", "me@acme.com")
        self.assertTrue(j.auth.startswith("Basic "))
        self.assertTrue(j.cloud)
        self.assertFalse(jira.Jira("https://jira.acme.com", "t").cloud)

    def test_search_uses_dc_endpoint_for_self_hosted(self):
        out = self.run_cli("search", "labels = agent:analyze")
        self.assertIn("NPU-1\tOpen", out)
        self.assertTrue(Fake.calls[0][1].startswith("/rest/api/2/search?"))


if __name__ == "__main__":
    unittest.main()
