import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from services.edu_tracker.web import build_handler
from tests.helpers import write_point


class WebTests(unittest.TestCase):
    def test_home_and_manual_submission(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            write_point(project_root / "教育智能体" / "02-课标与知识体系" / "02-国家课标知识树")
            try:
                server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(project_root))
            except PermissionError:
                self.skipTest("当前沙箱禁止绑定本地端口")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                home = urlopen(base + "/", timeout=5).read().decode("utf-8")
                self.assertIn("手动录题", home)
                payload = urlencode({
                    "student_id": "s1", "grade": "二年级", "text": "乘法口诀练习",
                    "answer": "6", "student_answer": "6",
                }).encode()
                response = urlopen(Request(base + "/manual", data=payload), timeout=5)
                self.assertIn("已完成分析", response.read().decode("utf-8"))
                exported = urlopen(base + "/data-export?student_id=s1", timeout=5)
                self.assertEqual(exported.headers.get_content_type(), "application/zip")
                self.assertGreater(len(exported.read()), 0)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
