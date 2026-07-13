from __future__ import annotations

import csv
import io
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OCRResult:
    text: str
    confidence: float
    engine: str


def recognize_image(image_path: Path, languages: str = "chi_sim+eng") -> OCRResult:
    if not image_path.exists():
        raise FileNotFoundError(f"图片不存在：{image_path}")
    executable = shutil.which("tesseract")
    if executable is None:
        raise RuntimeError("未安装 Tesseract OCR")
    completed = subprocess.run(
        [executable, str(image_path), "stdout", "-l", languages, "--psm", "6", "tsv"],
        check=True,
        capture_output=True,
        text=True,
    )
    words: list[str] = []
    confidences: list[float] = []
    for row in csv.DictReader(io.StringIO(completed.stdout), delimiter="\t"):
        word = (row.get("text") or "").strip()
        try:
            confidence = float(row.get("conf") or -1)
        except ValueError:
            confidence = -1
        if word:
            words.append(word)
        if confidence >= 0:
            confidences.append(confidence)
    return OCRResult(
        text=" ".join(words),
        confidence=round(sum(confidences) / len(confidences) / 100, 3) if confidences else 0.0,
        engine=f"tesseract:{languages}",
    )
