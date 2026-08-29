import csv
import tempfile
import unittest
from pathlib import Path

from tools.official_rows import load_splits


class OfficialRowsTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def write_log(self, filename, records):
        with (self.data_dir / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["date", "user_id", "video_id", "long_view"],
            )
            writer.writeheader()
            writer.writerows(records)

    def test_preserves_file_order_and_official_date_boundaries(self):
        self.write_log(
            "log_standard_4_08_to_4_21_pure.csv",
            [{"date": 20220421, "user_id": "train", "video_id": "v0", "long_view": "0"}],
        )
        self.write_log(
            "log_standard_4_22_to_5_08_pure.csv",
            [
                {"date": 20220422, "user_id": "valid1", "video_id": "v1", "long_view": "0"},
                {"date": 20220428, "user_id": "valid2", "video_id": "v2", "long_view": "1"},
                {"date": 20220429, "user_id": "test", "video_id": "v3", "long_view": "1"},
            ],
        )
        splits = load_splits(self.data_dir)
        self.assertEqual([row[1] for row in splits["valid"]], ["valid1", "valid2"])
        self.assertEqual([row[6] for row in splits["valid"]], [0, 1])
        self.assertEqual([row[1] for row in splits["test"]], ["test"])


if __name__ == "__main__":
    unittest.main()
