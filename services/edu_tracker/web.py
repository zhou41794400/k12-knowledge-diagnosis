from __future__ import annotations

from email.parser import BytesParser
from email.policy import default
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, quote, urlparse
from uuid import uuid4

from .pipeline import LocalPipeline
from .reporting import generate_reports
from .knowledge_registry import registry
from .data_management import delete_student, export_student, health_status


def _field(values: dict[str, list[str]], name: str) -> str:
    return values.get(name, [""])[0].strip()


def _parse_multipart(content_type: str, body: bytes) -> tuple[dict[str, str], Optional[tuple[str, bytes]]]:
    raw = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
    message = BytesParser(policy=default).parsebytes(raw)
    fields: dict[str, str] = {}
    upload: Optional[tuple[str, bytes]] = None
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if filename:
            upload = (filename, payload)
        else:
            fields[name] = payload.decode(part.get_content_charset() or "utf-8", errors="replace").strip()
    return fields, upload


def build_handler(project_root: Path):
    vault_root = project_root / "教育智能体"
    pipeline = LocalPipeline(vault_root)
    knowledge_root = vault_root / "02-课标与知识体系" / "02-国家课标知识树"

    class ParentHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._home(_field(parse_qs(parsed.query), "message"))
            elif parsed.path == "/report":
                self._report()
            elif parsed.path == "/data-export":
                self._download_export(_field(parse_qs(parsed.query), "student_id"))
            else:
                self.send_error(404, "页面不存在")

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/manual":
                    values = self._urlencoded()
                    result = pipeline.process_manual_question(
                        student_id=_field(values, "student_id"), subject="数学",
                        grade=_field(values, "grade"), text=_field(values, "text"),
                        answer=_field(values, "answer"), student_answer=_field(values, "student_answer"),
                    )
                    self._redirect("已进入复核" if result["evidence"] is None else "已完成分析")
                    return
                if parsed.path == "/photo":
                    self._handle_photo()
                    return
                if parsed.path == "/ocr-confirm":
                    values = self._urlencoded()
                    result = pipeline.process_photo(
                        student_id=_field(values, "student_id"), subject="数学",
                        grade=_field(values, "grade"), image_path=_field(values, "image_path"),
                        ingest_id=_field(values, "ingest_id"), ocr_text=_field(values, "ocr_text"),
                        answer=_field(values, "answer"), student_answer=_field(values, "student_answer"),
                    )
                    self._redirect(str(result.get("reason") or result.get("status") or "已确认"))
                    return
                if parsed.path == "/review/close":
                    values = self._urlencoded()
                    result = pipeline.close_review_task(
                        _field(values, "review_id"), abandon=_field(values, "action") == "abandon",
                    )
                    self._redirect(str(result["status"]))
                    return
                if parsed.path == "/review/apply":
                    values = self._urlencoded()
                    result = pipeline.apply_review_decision(
                        _field(values, "review_id"), point_code=_field(values, "point_code"),
                        is_correct=_field(values, "is_correct") == "true",
                    )
                    self._redirect(str(result.get("reason") or result["status"]))
                    return
                if parsed.path == "/data-delete":
                    values = self._urlencoded()
                    deleted = delete_student(
                        project_root, _field(values, "student_id"), _field(values, "confirm"),
                    )
                    self._redirect(f"已删除：{deleted}")
                    return
            except (OSError, ValueError, KeyError) as exc:
                self._redirect(f"操作失败：{exc}")
                return
            self.send_error(404, "接口不存在")

        def _urlencoded(self) -> dict[str, list[str]]:
            length = int(self.headers.get("Content-Length", "0"))
            return parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)

        def _handle_photo(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            fields, upload = _parse_multipart(self.headers.get("Content-Type", ""), self.rfile.read(length))
            if upload is None or not upload[1]:
                raise ValueError("请选择试卷图片")
            original_name, content = upload
            if len(content) > 15 * 1024 * 1024:
                raise ValueError("图片不能超过 15MB")
            suffix = Path(original_name).suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}:
                raise ValueError("仅支持 PNG、JPG、WEBP 和 TIFF 图片")
            upload_dir = vault_root / "logs" / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            image_path = upload_dir / f"{uuid4().hex}{suffix}"
            image_path.write_bytes(content)
            result = pipeline.process_photo(
                student_id=fields.get("student_id", ""), subject="数学", grade=fields.get("grade", ""),
                image_path=str(image_path), answer=fields.get("answer", ""),
                student_answer=fields.get("student_answer", ""),
            )
            self._redirect(str(result.get("status", "已提交")))

        def _home(self, message: str) -> None:
            generate_reports(project_root)
            reviews = pipeline.list_review_tasks()
            published_points = registry(knowledge_root)
            health = health_status(project_root)
            point_options = "".join(
                f'<option value="{escape(point.point_code)}">{escape(point.title)}</option>'
                for point in published_points
            )
            review_html = []
            for task in reviews:
                rid = escape(str(task.get("review_id", "")))
                target_id = str(task.get("target_id", ""))
                ingest = pipeline.store.get_record("ingest", target_id)
                if ingest and ingest.get("status") == "待确认":
                    grade = escape(str(ingest.get("grade") or "二年级"))
                    other_grade = "三年级" if grade == "二年级" else "二年级"
                    review_html.append(f"""<article class="review"><div><strong>OCR 待确认</strong><p>{escape(str(ingest.get('image_path', '')))}</p></div>
                    <form method="post" action="/ocr-confirm"><input type="hidden" name="ingest_id" value="{escape(target_id)}"><input type="hidden" name="student_id" value="{escape(str(ingest.get('student_id', '')))}"><input type="hidden" name="image_path" value="{escape(str(ingest.get('image_path', '')))}"><select name="grade"><option>{grade}</option><option>{other_grade}</option></select><textarea name="ocr_text" required>{escape(str(ingest.get('ocr_text', '')))}</textarea><div class="pair"><input name="answer" placeholder="标准答案"><input name="student_answer" placeholder="学生作答"></div><button>确认并分析</button></form></article>""")
                    continue
                review_html.append(f"""<article class="review"><div><strong>{escape(str(task.get('target_id', '')))}</strong><p>{escape(str(task.get('reason', '')))}</p></div>
                <form method="post" action="/review/apply"><input type="hidden" name="review_id" value="{rid}"><input name="point_code" list="published-points" placeholder="选择已发布知识点" required><button name="is_correct" value="true">确认正确</button><button class="warn" name="is_correct" value="false">确认错误</button></form>
                <form method="post" action="/review/close"><input type="hidden" name="review_id" value="{rid}"><button name="action" value="resolve">仅关闭</button><button class="ghost" name="action" value="abandon">放弃</button></form></article>""")
            notice = f'<div class="message">{escape(message)}</div>' if message else ""
            body = f"""<header><div><small>本地隐私型学习记录</small><h1>启智知踪</h1></div><a href="/report">查看家长报告</a></header>{notice}
            <main><datalist id="published-points">{point_options}</datalist><section class="hero"><p>今天只做三件事</p><h2>录入、复核、查看下一步</h2><div class="stats"><span><b>{len(reviews)}</b>待复核</span><span><b>{len(published_points)}</b>已发布数学知识点</span></div></section>
            <div class="grid"><section><h2>手动录题</h2>{self._manual_form()}</section><section><h2>上传试卷图片</h2>{self._photo_form()}</section></div>
            <section><div class="section-title"><h2>待处理复核</h2><span>{len(reviews)} 条</span></div>{''.join(review_html) if review_html else '<div class="empty">当前没有待处理记录。</div>'}</section>
            <section><h2>数据管理</h2><p>数据库版本 {health['schema_version']}，待导出队列 {health['pending_outbox']} 条。</p><div class="grid"><form class="stack" method="get" action="/data-export"><input name="student_id" placeholder="学生编号" required><button>导出学生数据</button></form><form class="stack" method="post" action="/data-delete"><input name="student_id" placeholder="学生编号" required><input name="confirm" placeholder="再次输入同一编号确认删除" required><button class="warn">永久删除</button></form></div></section></main>"""
            self._send_html(self._layout(body))

        def _manual_form(self) -> str:
            return """<form class="stack" method="post" action="/manual"><div class="pair"><input name="student_id" placeholder="学生编号" required><select name="grade"><option>二年级</option><option>三年级</option></select></div><textarea name="text" placeholder="输入题干" required></textarea><div class="pair"><input name="answer" placeholder="标准答案"><input name="student_answer" placeholder="学生作答"></div><button>提交分析</button></form>"""

        def _photo_form(self) -> str:
            return """<form class="stack" method="post" action="/photo" enctype="multipart/form-data"><div class="pair"><input name="student_id" placeholder="学生编号" required><select name="grade"><option>二年级</option><option>三年级</option></select></div><input type="file" name="image" accept="image/*" required><div class="pair"><input name="answer" placeholder="标准答案"><input name="student_answer" placeholder="学生作答"></div><button>上传并识别</button></form>"""

        def _report(self) -> None:
            path = vault_root / "05-结果视图" / "家长端总览.md"
            generate_reports(project_root)
            self._send_html(self._layout(f'<main><a href="/">返回首页</a><pre>{escape(path.read_text(encoding="utf-8"))}</pre></main>'))

        def _download_export(self, student_id: str) -> None:
            path = export_student(project_root, student_id)
            payload = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header(
                "Content-Disposition", f"attachment; filename=student-data.zip; filename*=UTF-8''{quote(path.name)}",
            )
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _redirect(self, message: str) -> None:
            self.send_response(303)
            self.send_header("Location", f"/?message={quote(message)}")
            self.end_headers()

        def _send_html(self, content: str) -> None:
            payload = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _layout(self, body: str) -> str:
            return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>启智知踪·家长端</title><style>
            :root{{--ink:#16302b;--paper:#f4f0e6;--card:#fffdf7;--accent:#db5b32;--line:#d8cfbd}}*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 85% 0,#e8c98755,transparent 28%),var(--paper);color:var(--ink);font-family:"Songti SC","Noto Serif SC",serif}}header,main{{max-width:1080px;margin:auto}}header{{display:flex;justify-content:space-between;align-items:center;padding:28px 20px}}h1,h2,p{{margin-top:0}}h1{{font-size:34px;margin-bottom:0}}a{{color:var(--ink)}}main{{padding:0 20px 60px}}.hero{{padding:46px;border:1px solid var(--line);background:linear-gradient(130deg,#fffdf7,#e6eddf);border-radius:28px;margin-bottom:22px}}.hero h2{{font-size:clamp(30px,5vw,58px);max-width:760px}}.stats{{display:flex;gap:32px}}.stats span{{display:flex;gap:8px;align-items:baseline}}.stats b{{font-size:30px;color:var(--accent)}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}section{{background:var(--card);padding:26px;border:1px solid var(--line);border-radius:20px;margin-bottom:22px}}.stack,.review form{{display:grid;gap:12px}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}input,textarea,select,button{{font:inherit;padding:12px;border:1px solid var(--line);border-radius:10px;background:white}}textarea{{min-height:110px}}button{{background:var(--ink);color:white;border:0;cursor:pointer}}button.warn{{background:var(--accent)}}button.ghost{{background:#786f61}}.section-title,.review{{display:flex;justify-content:space-between;gap:20px;align-items:start}}.review{{padding:16px 0;border-top:1px solid var(--line)}}.review>div{{flex:1}}.message{{max-width:1040px;margin:0 auto 18px;padding:12px 20px;background:#fff3c7;border-radius:12px}}.empty,pre{{padding:24px;background:#f1ecdf;border-radius:14px;white-space:pre-wrap}}small{{letter-spacing:.12em}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}.hero{{padding:28px}}.stats,.review{{display:block}}.review form{{margin-top:12px}}}}</style></head><body>{body}</body></html>"""

        def log_message(self, format: str, *args) -> None:
            return

    return ParentHandler


def run_server(project_root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), build_handler(project_root))
    print(f"启智知踪家长端已启动：http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
