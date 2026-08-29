import csv
import tempfile
import unittest
from pathlib import Path

from tools.build_dev_dataset import build_dev_dataset


class BuildDevDatasetTests(unittest.TestCase):
    def test_keeps_order_and_never_copies_post_validation_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "input", root / "output"
            source.mkdir()
            headers = ["date", "user_id", "video_id", "long_view"]
            for filename in ("log_standard_4_08_to_4_21_pure.csv", "log_standard_4_22_to_5_08_pure.csv"):
                with (source / filename).open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows([
                        {"date": "20220420", "user_id": "u1", "video_id": "v1", "long_view": "0"},
                        {"date": "20220428", "user_id": "u2", "video_id": "v2", "long_view": "1"},
                        {"date": "20220429", "user_id": "u3", "video_id": "v3", "long_view": "1"},
                    ])
            build_dev_dataset(source, output, rows_per_log=10)
            with (output / "log_standard_4_22_to_5_08_pure.csv").open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["user_id"] for row in rows], ["u1", "u2"])
            self.assertTrue(all(int(row["date"]) <= 20220428 for row in rows))


if __name__ == "__main__":
    unittest.main()
