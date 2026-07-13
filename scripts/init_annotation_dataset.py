import csv
from pathlib import Path


path = Path("教育智能体/07-测试验收/数据/真实题双人标注模板.csv")
path.parent.mkdir(parents=True, exist_ok=True)
fields = ["case_id", "source_hash", "subject", "grade", "question_text", "annotator_a", "annotator_b", "adjudicated_code", "consent_confirmed", "deidentified", "status"]
with path.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    for index in range(1, 51):
        writer.writerow({"case_id": f"REAL-{index:03d}", "subject": "数学", "status": "待采集"})
print(path)
