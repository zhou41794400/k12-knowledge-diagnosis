import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.edu_tracker.ocr import recognize_image


class OCRTests(unittest.TestCase):
    def test_tesseract_tsv_is_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / "paper.png"
            image.write_bytes(b"image")
            tsv = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n5\t1\t1\t1\t1\t1\t0\t0\t1\t1\t90\t周长\n5\t1\t1\t1\t1\t2\t0\t0\t1\t1\t80\t是多少\n"
            completed = subprocess.CompletedProcess([], 0, stdout=tsv, stderr="")
            with patch("services.edu_tracker.ocr.shutil.which", return_value="/opt/homebrew/bin/tesseract"), patch(
                "services.edu_tracker.ocr.subprocess.run", return_value=completed
            ):
                result = recognize_image(image)
            self.assertEqual(result.text, "周长 是多少")
            self.assertEqual(result.confidence, 0.85)


if __name__ == "__main__":
    unittest.main()
