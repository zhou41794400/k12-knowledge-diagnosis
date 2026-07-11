from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .knowledge_registry import match_question


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            for field in ("case_id", "subject", "grade", "text", "expected_point_code"):
                if field not in case:
                    raise ValueError(f"第 {line_number} 行缺少字段：{field}")
            cases.append(case)
    return cases


def validate_mapping(dataset_path: Path, knowledge_root: Path) -> dict[str, Any]:
    cases = load_cases(dataset_path)
    results: list[dict[str, Any]] = []
    passed = 0
    for case in cases:
        match = match_question(
            str(case["subject"]),
            str(case["grade"]),
            str(case["text"]),
            knowledge_root=knowledge_root,
        )
        actual_code = match.point.point_code if match.point else ""
        expected_code = str(case["expected_point_code"])
        expected_review = bool(case.get("expected_review_required", expected_code == ""))
        case_passed = actual_code == expected_code and match.review_required == expected_review
        passed += int(case_passed)
        results.append(
            {
                "case_id": case["case_id"],
                "passed": case_passed,
                "expected_point_code": expected_code,
                "actual_point_code": actual_code,
                "expected_review_required": expected_review,
                "actual_review_required": match.review_required,
                "reason": match.reason,
            }
        )

    total = len(cases)
    failed = total - passed
    return {
        "dataset": str(dataset_path),
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "results": results,
    }
