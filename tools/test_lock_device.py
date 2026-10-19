"""Tests for tools/lock.py and tools/device.py. Run: python -m unittest discover -s tools -p "test_*.py" """

import base64
import contextlib
import io
import json
import os
import pathlib
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import device  # noqa: E402
import lock  # noqa: E402


class TempHome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {
            "LOOP_HOME": str(self.home), "LOOP_DOSSIER": str(self.home / "dossier"),
            "LOOP_LOCKS": str(self.home / "locks"), "LOOP_DEVICES": str(self.home / "devices.toml")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class LockTest(TempHome):
    def test_acquire_is_exclusive_and_reentrant(self):
        self.assertTrue(lock.acquire("device-a", "NPU-1")[0])
        self.assertTrue(lock.acquire("device-a", "NPU-1")[0])
        ok, info = lock.acquire("device-a", "NPU-2")
        self.assertFalse(ok)
        self.assertEqual(info["owner"], "NPU-1")

    def test_release_only_by_owner(self):
        lock.acquire("device-a", "NPU-1")
        self.assertFalse(lock.release("device-a", "NPU-2"))
        self.assertTrue(lock.release("device-a", "NPU-1"))
        self.assertTrue(lock.acquire("device-a", "NPU-2")[0])

    def test_steal_only_expired(self):
        lock.acquire("device-a", "NPU-1", ttl_min=1)
        self.assertFalse(lock.acquire("device-a", "NPU-2", steal_expired=True)[0])
        with mock.patch.object(lock.time, "time", return_value=time.time() + 120):
            self.assertTrue(lock.acquire("device-a", "NPU-2", steal_expired=True)[0])

    def test_require_exits_when_not_held(self):
        with self.assertRaises(SystemExit):
            lock.require("device-a", "NPU-1")


class DeviceLocalTest(TempHome):
    def setUp(self):
        super().setUp()
        scratch = (self.home / "scratch").as_posix()
        (self.home / "devices.toml").write_text(
            f'[[device]]\nid = "loc"\nos = "linux"\ntransport = "local"\nscratch = "{scratch}"\n')
        self.artifact = self.home / "model.bin"
        self.artifact.write_bytes(b"weights")

    def cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            device.main(list(argv))
        return out.getvalue()

    def test_requires_lock(self):
        with self.assertRaises(SystemExit):
            self.cli("doctor", "loc", "--key", "NPU-1")

    def test_push_run_pull_clean(self):
        lock.acquire("device-loc", "NPU-1")
        self.cli("push", "loc", "--key", "NPU-1", str(self.artifact))
        self.assertTrue((self.home / "scratch/NPU-1/model.bin").exists())

        out = self.cli("run", "loc", "--key", "NPU-1", "--slug", "repro", "--repeat", "2", "--",
                       sys.executable, "-c", "\"import pathlib; print(pathlib.Path('model.bin').read_text())\"")
        self.assertIn("0/2 runs exited non-zero", out)
        run_dir = next((self.home / "dossier/NPU-1/device-runs").iterdir())
        self.assertIn("weights", (run_dir / "stdout-2.txt").read_text())
        self.assertIn('"sha256"', (run_dir / "device.txt").read_text())
        self.assertEqual(len(json.loads((run_dir / "result.json").read_text())["runs"]), 2)

        dest = self.home / "pulled"
        self.cli("pull", "loc", "--key", "NPU-1", "model.bin", str(dest))
        self.assertEqual((dest / "model.bin").read_bytes(), b"weights")

        self.cli("clean", "loc", "--key", "NPU-1")
        self.assertFalse((self.home / "scratch/NPU-1").exists())


class DeviceCommandTest(unittest.TestCase):
    def test_windows_uses_encoded_powershell_in_workdir(self):
        dev = device.Device({"id": "w", "os": "windows", "transport": "ssh", "host": "u@h", "scratch": "C:/loop"}, "NPU-1")
        with mock.patch.object(device, "sh") as sh:
            dev.shell("Write-Output 'a b'", cwd=True)
        argv = sh.call_args[0][0]
        self.assertEqual(argv[:2], ["ssh", "u@h"])
        script = base64.b64decode(argv[2].split()[-1]).decode("utf-16-le")
        self.assertEqual(script, "Set-Location 'C:/loop/NPU-1'; Write-Output 'a b'")

    def test_android_uses_adb_serial(self):
        dev = device.Device({"id": "a", "os": "android", "transport": "adb", "serial": "S1",
                             "scratch": "/data/local/tmp/loop"}, "NPU-1")
        with mock.patch.object(device, "sh") as sh:
            dev.shell("./run", cwd=True)
        self.assertEqual(sh.call_args[0][0], ["adb", "-s", "S1", "shell", "cd /data/local/tmp/loop/NPU-1 && ./run"])


if __name__ == "__main__":
    unittest.main()
