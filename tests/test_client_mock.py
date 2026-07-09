import os
import sys
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hy3cli.client import Hy3Client, _mock_command  # noqa: E402


class TestMockClient(unittest.TestCase):
    def _client(self):
        return Hy3Client(base_url="http://x", api_key="", model="hy3", mock=True)

    def test_mock_returns_json(self):
        c = self._client()
        out = c.natural_language_to_command(
            "找出当前目录下最近7天修改、大于100MB的文件", "linux")
        self.assertIn("command", out)
        self.assertIn("risk_level", out)

    def test_mock_port_query(self):
        c = self._client()
        out = c.natural_language_to_command("查看占用 8080 端口的进程", "linux")
        self.assertIn("lsof", out["command"])

    def test_mock_windows_shell(self):
        out = _mock_command("找出最近7天修改的大于100MB的文件", "windows")
        self.assertIn("Get-ChildItem", out["command"])

    def test_parse_json_strips_fences(self):
        from hy3cli.client import _parse_json
        self.assertEqual(_parse_json('```json\n{"a":1}\n```'), {"a": 1})


if __name__ == "__main__":
    unittest.main()
