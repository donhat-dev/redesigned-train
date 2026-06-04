import tempfile
import unittest
from pathlib import Path
from unittest import mock

import wsl_chrome_devtools_ws as bridge


class ResolveDevToolsUrlTests(unittest.TestCase):
    def test_rewrites_localhost_on_wsl(self) -> None:
        with mock.patch.object(bridge, "is_wsl", return_value=True):
            resolved = bridge.resolve_devtools_ws_url(
                "ws://127.0.0.1:9222/devtools/browser/abc",
                force_windows_host="172.29.224.1",
            )
        self.assertEqual(
            resolved,
            "ws://172.29.224.1:9222/devtools/browser/abc",
        )

    def test_keeps_url_when_not_wsl(self) -> None:
        with mock.patch.object(bridge, "is_wsl", return_value=False):
            resolved = bridge.resolve_devtools_ws_url(
                "ws://127.0.0.1:9222/devtools/browser/abc"
            )
        self.assertEqual(resolved, "ws://127.0.0.1:9222/devtools/browser/abc")

    def test_raises_for_non_websocket_scheme(self) -> None:
        with self.assertRaisesRegex(ValueError, "ws:// or wss://"):
            bridge.resolve_devtools_ws_url("http://127.0.0.1:9222/devtools/browser/abc")

    def test_raises_for_missing_hostname(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing hostname"):
            bridge.resolve_devtools_ws_url("ws:///devtools/browser/abc")


class ResolverHostTests(unittest.TestCase):
    def test_nameserver_from_resolv_conf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "resolv.conf"
            path.write_text("# generated\nnameserver 172.20.80.1\n", encoding="utf-8")
            self.assertEqual(bridge._first_resolver_nameserver(path), "172.20.80.1")

    def test_nameserver_skips_localhost_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "resolv.conf"
            path.write_text(
                "nameserver 127.0.0.1\nnameserver ::1\nnameserver 172.20.80.1\n",
                encoding="utf-8",
            )
            self.assertEqual(bridge._first_resolver_nameserver(path), "172.20.80.1")

    def test_windows_host_prefers_environment_override(self) -> None:
        with mock.patch.dict("os.environ", {"CHROME_WINDOWS_HOST": "10.0.0.9"}, clear=False):
            self.assertEqual(bridge.windows_host(), "10.0.0.9")


if __name__ == "__main__":
    unittest.main()
