from __future__ import annotations

import argparse
import json
from pathlib import Path

from .materials import generate_materials
from .pipeline import LocalPipeline
from .reporting import generate_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="edu-tracker")
    sub = parser.add_subparsers(dest="command", required=True)

    manual = sub.add_parser("manual", help="process a manual question")
    manual.add_argument("--student-id", required=True)
    manual.add_argument("--subject", required=True)
    manual.add_argument("--grade", required=True)
    manual.add_argument("--text", required=True)
    manual.add_argument("--answer", default="")
    manual.add_argument("--student-answer", default="")

    photo = sub.add_parser("photo", help="process a photo question")
    photo.add_argument("--student-id", required=True)
    photo.add_argument("--subject", required=True)
    photo.add_argument("--grade", required=True)
    photo.add_argument("--image-path", required=True)
    photo.add_argument("--ocr-text", default="")
    photo.add_argument("--answer", default="")
    photo.add_argument("--student-answer", default="")

    report = sub.add_parser("report", help="generate parent/student markdown reports")
    report.add_argument("--student-id", default="")

    materials = sub.add_parser("materials", help="generate copyright materials")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[2]
    pipeline = LocalPipeline(project_root / "教育智能体")

    if args.command == "manual":
        result = pipeline.process_manual_question(
            student_id=args.student_id,
            subject=args.subject,
            grade=args.grade,
            text=args.text,
            answer=args.answer,
            student_answer=args.student_answer,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "photo":
        result = pipeline.process_photo(
            student_id=args.student_id,
            subject=args.subject,
            grade=args.grade,
            image_path=args.image_path,
            ocr_text=args.ocr_text,
            answer=args.answer,
            student_answer=args.student_answer,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "report":
        sid = args.student_id.strip() or None
        generated = generate_reports(project_root, sid)
        print(json.dumps({"generated": [str(path) for path in generated]}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "materials":
        generated = generate_materials(project_root)
        print(json.dumps({"generated": [str(path) for path in generated]}, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
