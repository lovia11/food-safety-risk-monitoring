import tempfile
import unittest
from pathlib import Path

from src.local_api import list_run_snapshots, resolve_run_file, resolve_run_root
from src.runtime import write_json


class LocalApiHelpersTest(unittest.TestCase):
    def test_paths_cannot_escape_output_or_run_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary) / "output"
            run_root = output_root / "run-1"
            run_root.mkdir(parents=True)
            self.assertEqual(resolve_run_root(output_root, "run-1"), run_root.resolve())
            with self.assertRaises(ValueError):
                resolve_run_root(output_root, "../outside")
            with self.assertRaises(ValueError):
                resolve_run_file(run_root, "../../outside.txt")

    def test_lists_only_runs_with_valid_web_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary) / "output"
            write_json(
                output_root / "run-1" / "web_snapshot.json",
                {
                    "generatedAt": "2026-08-28T19:00:00+08:00",
                    "task": {"id": "run-1", "stage": "completed"},
                    "statistics": {"selectedProducts": 1},
                },
            )
            (output_root / "run-2").mkdir()
            runs = list_run_snapshots(output_root)
            self.assertEqual([item["id"] for item in runs], ["run-1"])
            self.assertEqual(runs[0]["statistics"]["selectedProducts"], 1)


if __name__ == "__main__":
    unittest.main()
