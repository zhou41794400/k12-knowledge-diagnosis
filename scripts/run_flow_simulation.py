from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from services.edu_tracker.pipeline import LocalPipeline
from services.edu_tracker.ocr import OCRResult
from services.edu_tracker.reporting import generate_reports


def passed(name: str, condition: bool, detail: str) -> dict:
    return {"流程": name, "结果": "通过" if condition else "失败", "说明": detail}


def main() -> int:
    results: list[dict] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        vault = root / "教育智能体"
        shutil.copytree(
            PROJECT / "教育智能体" / "02-课标与知识体系",
            vault / "02-课标与知识体系",
        )
        pipeline = LocalPipeline(vault)

        correct = pipeline.process_manual_question(
            student_id="sim001", subject="数学", grade="三年级",
            text="计算小区花坛一圈围栏的周长", answer="20米", student_answer="20米",
        )
        results.append(passed("手动录题-正确", correct["evidence"] is not None, "生成 rule-v2 证据和掌握状态"))

        wrong = pipeline.process_manual_question(
            student_id="sim001", subject="数学", grade="三年级",
            text="计算小区花坛一圈围栏的周长", answer="20米", student_answer="18米",
        )
        results.append(passed("手动录题-错误", wrong["mastery"]["negative_evidence_count"] == 1, "负向证据累计一次"))

        pending = pipeline.process_manual_question(
            student_id="sim001", subject="数学", grade="三年级", text="计算图形的面积"
        )
        results.append(passed("答案缺失", pending["evidence"] is None and pending["mastery"] is None, "仅记录题目与审计"))

        unmatched = pipeline.process_manual_question(
            student_id="sim001", subject="数学", grade="三年级",
            text="计算236加489", answer="725", student_answer="725",
        )
        results.append(passed("未知知识点拒识", unmatched["evidence"] is None, "进入人工复核"))

        ambiguous = pipeline.process_manual_question(
            student_id="sim001", subject="数学", grade="三年级",
            text="比较图形的周长和面积", answer="略", student_answer="略",
        )
        results.append(passed("多知识点歧义", ambiguous["match"]["review_required"] and ambiguous["evidence"] is None, "不更新掌握度"))

        reviewed = pipeline.apply_review_decision(
            f"r_{ambiguous['question']['question_id']}", point_code="MATH-PRI-G3-GG-001", is_correct=False,
        )
        results.append(passed("人工复核写入", reviewed.get("status") == "已解决" and reviewed.get("evidence") is not None, "人工结论生成审核证据"))

        image_path = root / "paper.png"
        ocr_patch = None
        try:
            if shutil.which("tesseract") is None:
                raise ImportError("Tesseract unavailable")
            from PIL import Image, ImageDraw, ImageFont
            font_candidates = list(Path("/System/Library/Fonts").rglob("*.ttc")) + list(Path("/usr/share/fonts").rglob("*.ttf"))
            image = Image.new("RGB", (900, 160), "white")
            font = ImageFont.truetype(str(font_candidates[0]), 48) if font_candidates else ImageFont.load_default()
            ImageDraw.Draw(image).text((20, 40), "Rectangle perimeter is 24 cm", font=font, fill="black")
            image.save(image_path)
        except (ImportError, OSError):
            image_path.write_bytes(b"simulation")
            from unittest.mock import patch
            ocr_patch = patch(
                "services.edu_tracker.pipeline.recognize_image",
                return_value=OCRResult("Rectangle perimeter is 24 cm", 0.9, "ci-simulated-ocr"),
            )
            ocr_patch.start()
        try:
            ocr_pending = pipeline.process_photo(
                student_id="sim001", subject="数学", grade="三年级", image_path=str(image_path)
            )
        finally:
            if ocr_patch:
                ocr_patch.stop()
        results.append(passed("真实OCR待确认", ocr_pending.get("status") == "待确认" and "ocr" in ocr_pending, "未进入知识映射"))

        confirmed = pipeline.process_photo(
            student_id="sim001", subject="数学", grade="三年级", image_path=str(image_path),
            ocr_text="学校操场的周长是多少", answer="24米", student_answer="24米",
            ingest_id=ocr_pending["ingest"]["ingest_id"],
        )
        results.append(passed("OCR人工确认后提交", confirmed["evidence"] is not None, "确认文本进入分析"))

        missing = pipeline.process_photo(
            student_id="sim001", subject="数学", grade="三年级", image_path=str(root / "missing.png")
        )
        results.append(passed("图片不存在", missing.get("status") == "OCR失败", "返回明确失败，不写掌握度"))

        generated = generate_reports(root, "sim001")
        results.append(passed("报告生成", all(path.exists() for path in generated), f"生成 {len(generated)} 个结果文件"))

        with sqlite3.connect(vault / "logs" / "edu_tracker.sqlite3") as db:
            question_count = db.execute("SELECT COUNT(*) FROM records WHERE record_type='questions'").fetchone()[0]
            mastery_count = db.execute("SELECT COUNT(*) FROM mastery_current").fetchone()[0]
            review_count = db.execute("SELECT COUNT(*) FROM review_tasks WHERE status='待处理'").fetchone()[0]
            schema_version = db.execute("PRAGMA user_version").fetchone()[0]
        results.append(passed("SQLite与JSONL双写", question_count == 6 and mastery_count == 1, f"题目={question_count}，当前掌握={mastery_count}"))
        results.append(passed("复核任务汇总", review_count == 3, f"待处理复核={review_count}"))
        results.append(passed("数据库版本", schema_version == 1, f"schema_version={schema_version}"))

    summary = {"总流程数": len(results), "通过": sum(r["结果"] == "通过" for r in results), "失败": sum(r["结果"] == "失败" for r in results), "明细": results}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["失败"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
