from __future__ import annotations

import argparse
import json
from pathlib import Path

from .materials import generate_materials
from .pipeline import LocalPipeline
from .reporting import generate_reports
from .validation import validate_mapping
from .web import run_server
from .data_management import create_backup, delete_student, export_student, health_status, restore_backup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="edu-tracker")
    sub = parser.add_subparsers(dest="command", required=True)

    manual = sub.add_parser("manual", help="处理手动录入题目")
    manual.add_argument("--student-id", required=True)
    manual.add_argument("--subject", required=True)
    manual.add_argument("--grade", required=True)
    manual.add_argument("--text", required=True)
    manual.add_argument("--answer", default="")
    manual.add_argument("--student-answer", default="")

    photo = sub.add_parser("photo", help="处理照片旁路文本题目")
    photo.add_argument("--student-id", required=True)
    photo.add_argument("--subject", required=True)
    photo.add_argument("--grade", required=True)
    photo.add_argument("--image-path", required=True)
    photo.add_argument("--ocr-text", default="")
    photo.add_argument("--ingest-id", default="", help="待确认 OCR 记录编号")
    photo.add_argument("--answer", default="")
    photo.add_argument("--student-answer", default="")

    report = sub.add_parser("report", help="生成家长端和学生端报告")
    report.add_argument("--student-id", default="")

    materials = sub.add_parser("materials", help="生成软著材料")

    validate = sub.add_parser("validate", help="运行知识点映射研发验收")
    validate.add_argument("--dataset", default="")

    review_list = sub.add_parser("review-list", help="查看复核任务")
    review_list.add_argument("--student-id", default="")
    review_list.add_argument("--status", default="待处理")

    review_close = sub.add_parser("review-close", help="解决或放弃复核任务")
    review_close.add_argument("--review-id", required=True)
    review_close.add_argument("--abandon", action="store_true")

    review_apply = sub.add_parser("review-apply", help="将人工复核结论写入掌握度")
    review_apply.add_argument("--review-id", required=True)
    review_apply.add_argument("--point-code", required=True)
    correctness = review_apply.add_mutually_exclusive_group(required=True)
    correctness.add_argument("--correct", action="store_true")
    correctness.add_argument("--wrong", action="store_true")

    web = sub.add_parser("web", help="启动本地家长端")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8765)

    data_export = sub.add_parser("data-export", help="导出单个学生的全部本地数据")
    data_export.add_argument("--student-id", required=True)

    data_delete = sub.add_parser("data-delete", help="删除单个学生的全部本地数据")
    data_delete.add_argument("--student-id", required=True)
    data_delete.add_argument("--confirm", required=True, help="必须再次输入相同学生编号")

    sub.add_parser("backup", help="创建本地完整备份")
    restore = sub.add_parser("restore", help="将备份恢复到新目录")
    restore.add_argument("--backup-path", required=True)
    restore.add_argument("--target", required=True)
    sub.add_parser("health", help="查看本地数据健康状态")

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
            ingest_id=args.ingest_id,
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

    if args.command == "validate":
        dataset = (
            Path(args.dataset)
            if args.dataset
            else project_root / "教育智能体" / "07-测试验收" / "数据" / "数学映射验收题集.jsonl"
        )
        knowledge_root = project_root / "教育智能体" / "02-课标与知识体系" / "02-国家课标知识树"
        result = validate_mapping(dataset, knowledge_root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["failed"] == 0 else 1

    if args.command == "review-list":
        print(json.dumps(pipeline.list_review_tasks(args.student_id, args.status), ensure_ascii=False, indent=2))
        return 0

    if args.command == "review-close":
        result = pipeline.close_review_task(args.review_id, abandon=args.abandon)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] != "操作失败" else 1

    if args.command == "review-apply":
        result = pipeline.apply_review_decision(
            args.review_id, point_code=args.point_code, is_correct=args.correct,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] != "操作失败" else 1

    if args.command == "web":
        run_server(project_root, args.host, args.port)
        return 0

    if args.command == "data-export":
        path = export_student(project_root, args.student_id)
        print(json.dumps({"status": "已导出", "path": str(path)}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "data-delete":
        result = delete_student(project_root, args.student_id, args.confirm)
        print(json.dumps({"status": "已删除", "deleted": result}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "backup":
        path = create_backup(project_root)
        print(json.dumps({"status": "已备份", "path": str(path)}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "restore":
        target = restore_backup(Path(args.backup_path), Path(args.target))
        print(json.dumps({"status": "已恢复", "target": str(target)}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "health":
        print(json.dumps(health_status(project_root), ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
