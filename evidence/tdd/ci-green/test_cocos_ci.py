"""Synthetic result rejection tests; these do not count as native or hosted CI runs."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "templates/ui-design/ci/cocos-android.py"
spec = importlib.util.spec_from_file_location("cocos_ci", SOURCE)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class CocosResultsTests(unittest.TestCase):
    def setUp(self):
        self.head = "a" * 40
        self.expected = {"devices": [{"name": "small", "px": [720, 1280], "density": 320},
                                     {"name": "regular", "px": [1080, 2400], "density": 420}],
                         "cases": [{"id": f"C{i:02}"} for i in range(1, 17)],
                         "device_count": 2, "device_test_count": 16, "total_required_device_tests": 32,
                         "runtime": {"fingerprint": "TEST image", "api": 37, "abi": "arm64-v8a", "page_size": 16384},
                         "timeouts_seconds": {"creator_export": 600, "native_build": 900,
                                              "emulator_boot_per_device": 240, "suite_per_device": 300, "case": 30}}
        self.build = {"passed": True, "source_head": self.head, "source_dirty": "", "started_at": 1, "finished_at": 30,
                      "steps": [{"name": "creator", "exit": 36, "timeout_seconds": 600, "started_at": 1, "finished_at": 10},
                                {"name": "native", "exit": 0, "timeout_seconds": 900, "started_at": 10, "finished_at": 30}],
                      "apk": {"path": "TEST.apk", "bytes": 1234, "sha256": "b" * 64, "native_library_sha256": "c" * 64},
                      "scene_uuid": "TEST scene"}
        self.runtime = {"passed": True, "started_at": 31, "finished_at": 210, "expected_cases": 32,
                        "apk": deepcopy(self.build["apk"]), "cleanup_errors": [], "devices": []}
        for index, d in enumerate(self.expected["devices"]):
            self.runtime["devices"].append({"name": d["name"], "serial": f"emulator-{5580 + 2 * index}",
                "boot_started_at": 31 + index * 80, "boot_completed_at": 40 + index * 80,
                "identity": {"fingerprint": "TEST image", "api": "37", "abi": "arm64-v8a", "page_size": "16384",
                             "size": f"Physical size: {d['px'][0]}x{d['px'][1]}", "density": f"Physical density: {d['density']}"},
                "cases": [{"id": c["id"], "status": "passed", "started_at": 45 + index * 80 + i * 3,
                           "finished_at": 47 + index * 80 + i * 3} for i, c in enumerate(self.expected["cases"])]})

    def verify(self):
        return runner.verify_native(self.build, self.runtime, self.expected, self.head)

    def test_complete_exact_matrix_passes(self):
        self.assertTrue(self.verify()["passed"])

    def test_missing_or_failed_build_step_rejects(self):
        original = deepcopy(self.build)
        for change in [lambda b: b["steps"].pop(), lambda b: b["steps"][1].update(exit=1),
                       lambda b: b["steps"][0].update(timed_out=True), lambda b: b.update(passed=False)]:
            with self.subTest(change=change):
                self.build = deepcopy(original); change(self.build)
                with self.assertRaises(ValueError): self.verify()

    def test_missing_empty_duplicate_or_extra_cases_reject(self):
        original = deepcopy(self.runtime)
        for cases in [[], original["devices"][0]["cases"][:-1], original["devices"][0]["cases"] * 2,
                      original["devices"][0]["cases"] + [{"id": "C99", "status": "passed"}]]:
            self.runtime = deepcopy(original); self.runtime["devices"][0]["cases"] = cases
            with self.assertRaises(ValueError): self.verify()

    def test_skipped_cancelled_failed_or_timed_out_case_rejects(self):
        for status in ["skipped", "cancelled", "failed", "timed_out"]:
            with self.subTest(status=status):
                self.runtime["devices"][0]["cases"][0]["status"] = status
                with self.assertRaises(ValueError): self.verify()

    def test_timeout_cannot_be_reported_as_pass(self):
        self.runtime["devices"][0]["cases"][0]["finished_at"] = 100
        with self.assertRaises(ValueError): self.verify()

    def test_wrong_missing_or_duplicate_device_rejects(self):
        original = deepcopy(self.runtime)
        for devices in [original["devices"][:1], [original["devices"][0]] * 2]:
            self.runtime = deepcopy(original); self.runtime["devices"] = devices
            with self.assertRaises(ValueError): self.verify()
        self.runtime = deepcopy(original); self.runtime["devices"][0]["identity"]["api"] = "36"
        with self.assertRaises(ValueError): self.verify()

    def test_wrong_source_or_apk_rejects(self):
        self.build["source_head"] = "d" * 40
        with self.assertRaises(ValueError): self.verify()
        self.build["source_head"] = self.head; self.runtime["apk"]["sha256"] = "e" * 64
        with self.assertRaises(ValueError): self.verify()

    def test_failed_cleanup_or_unfinished_result_rejects(self):
        self.runtime["cleanup_errors"] = ["TEST failed restore"]
        with self.assertRaises(ValueError): self.verify()
        self.runtime["cleanup_errors"] = []; self.runtime.pop("finished_at")
        with self.assertRaises(ValueError): self.verify()

    def test_empty_independent_denominator_rejects(self):
        self.expected["cases"] = []
        with self.assertRaises(ValueError): self.verify()

    def test_missing_result_cannot_satisfy_success(self):
        with self.assertRaises(ValueError): runner.verify_native({}, self.runtime, self.expected, self.head)
        with self.assertRaises(ValueError): runner.verify_native(self.build, {}, self.expected, self.head)

    def test_actual_nonzero_process_rejects_and_retains_exit(self):
        with tempfile.TemporaryDirectory(prefix="cocos-ci-nonzero-") as temp:
            out = Path(temp)
            with self.assertRaises(ValueError):
                runner.run_command([sys.executable, "-c", "raise SystemExit(7)"], out, out, "native", 5)
            self.assertEqual(json.loads((out / "native.command.json").read_text())["exit"], 7)

    def test_actual_timeout_rejects_and_retains_interruption(self):
        with tempfile.TemporaryDirectory(prefix="cocos-ci-timeout-") as temp:
            out = Path(temp)
            with self.assertRaises(subprocess.TimeoutExpired):
                runner.run_command([sys.executable, "-c", "import time; time.sleep(30)"], out, out, "native", 0.1)
            result = json.loads((out / "native.command.json").read_text())
            self.assertTrue(result["interrupted"])
            self.assertIsNotNone(result["exit"])

    def test_actual_missing_apk_rejects(self):
        with tempfile.TemporaryDirectory(prefix="cocos-ci-missing-") as temp:
            out = Path(temp)
            self.build["apk"]["path"] = str(out / "missing.apk")
            with self.assertRaises(FileNotFoundError):
                runner.verify_artifacts(out, out, self.build, self.runtime, self.expected)


if __name__ == "__main__":
    unittest.main()
