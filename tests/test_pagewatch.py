import contextlib
import io
import json
import os
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pagewatch.analyze import analyze, normalized
from pagewatch.cli import main
from pagewatch.config import Config, SetupError, load_policy
from pagewatch.graph import Batch, Graph, GraphError
from pagewatch.report import render
from pagewatch.service import PageWatch
from pagewatch.store import Store
from pagewatch.urls import InputError, post_key


PAGE = "61579488621852"
POST = PAGE + "_123"
URL = "https://www.facebook.com/permalink.php?story_fbid=pfbidTEST&id=" + PAGE
POLICY = {"trusted_domains": [], "ignore_repeat_phrases": ["Juhoon fighting!"], "repeat_threshold": 3}


class FakeConnection:
    def __init__(self, body=None, status=200):
        self.body = json.dumps(body if body is not None else {"id": PAGE}).encode()
        self.status = status
        self.calls = []
        self.closed = False

    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))

    def getresponse(self):
        return self

    def read(self, limit):
        return self.body[:limit]

    def close(self):
        self.closed = True


class TransportTests(unittest.TestCase):
    def graph(self, connection):
        self.targets = []
        def factory(host, **kwargs):
            self.targets.append(host)
            return connection
        return Graph(Config(PAGE, "SECRET-DO-NOT-PRINT", "v99.0"), factory)

    def test_fixed_host_get_and_header_token(self):
        connection = FakeConnection()
        graph = self.graph(connection)
        graph.get(("me",), fields="id")
        self.assertEqual(self.targets, ["graph.facebook.com"])
        args, kwargs = connection.calls[0]
        self.assertEqual(args[0], "GET")
        self.assertNotIn("SECRET", args[1])
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer SECRET-DO-NOT-PRINT")
        self.assertTrue(connection.closed)

    def test_untrusted_id_stays_in_graph_path(self):
        connection = FakeConnection()
        graph = self.graph(connection)
        graph.get(("https://evil.invalid/x?access_token=bad",))
        self.assertEqual(self.targets, ["graph.facebook.com"])
        self.assertIn("https%3A%2F%2F", connection.calls[0][0][1])

    def test_token_error_redacted_not_empty_data(self):
        graph = self.graph(FakeConnection({"error": {"code": 190, "message": "SECRET-DO-NOT-PRINT"}}, 400))
        with self.assertRaises(GraphError) as error:
            graph.get(("me",))
        self.assertIn("190", str(error.exception))
        self.assertNotIn("SECRET", str(error.exception))

    def test_redirect_refused(self):
        graph = self.graph(FakeConnection(status=302))
        with self.assertRaisesRegex(GraphError, "redirect refused"):
            graph.get(("me",))
        self.assertEqual(len(self.targets), 1)

    def test_no_access_token_query(self):
        graph = self.graph(FakeConnection())
        with self.assertRaises(GraphError):
            graph.get(("me",), access_token="secret")

    def test_response_size_limit(self):
        connection = FakeConnection()
        connection.body = b"x" * 2_000_001
        with self.assertRaisesRegex(GraphError, "2 MB"):
            self.graph(connection).get(("me",))

    def test_request_budget(self):
        graph = self.graph(FakeConnection())
        graph.requests = 120
        with self.assertRaisesRegex(GraphError, "budget"):
            graph.get(("me",))
        self.assertFalse(self.targets)

    def test_empty_data_is_explicit(self):
        graph = self.graph(FakeConnection({"data": []}))
        self.assertEqual(graph.edge((PAGE, "posts"), "id").status, "empty_visible")

    def test_paginate_by_cursor_not_next_host(self):
        graph = self.graph(FakeConnection())
        with patch.object(graph, "get", side_effect=[
            {"data": [{"id": "1"}], "paging": {"next": "https://evil.invalid/?access_token=secret", "cursors": {"after": "A"}}},
            {"data": [{"id": "2"}]},
        ]) as request:
            batch = graph.edge((PAGE, "posts"), "id", limit=5)
        self.assertEqual(len(batch.items), 2)
        self.assertEqual(request.call_args.args[0], (PAGE, "posts"))
        self.assertEqual(request.call_args.kwargs["after"], "A")

    def test_partial_pagination_is_not_success(self):
        graph = self.graph(FakeConnection())
        with patch.object(graph, "get", side_effect=[
            {"data": [{"id": "1"}], "paging": {"next": "ignored", "cursors": {"after": "A"}}},
            GraphError("Permission denied"),
        ]):
            batch = graph.edge((PAGE, "posts"), "id")
        self.assertEqual(batch.status, "partial")
        self.assertEqual(len(batch.items), 1)

    def test_missing_data_is_error(self):
        graph = self.graph(FakeConnection({"id": PAGE}))
        with self.assertRaises(GraphError):
            graph.edge((PAGE, "posts"), "id")


class RuleTests(unittest.TestCase):
    def scan(self, texts, policy=None):
        return analyze([{"id": str(i), "message": t} for i, t in enumerate(texts)], policy or POLICY, PAGE)

    def test_vietnamese_normalization(self):
        self.assertEqual(normalized("Đăng   nhập"), "dang nhap")

    def test_credential_pressure_combination(self):
        findings, _ = self.scan(["Hỗ trợ Meta: page bị khóa trong 24h. Gửi mật khẩu và mã OTP ngay lập tức."])
        self.assertIn("credential-impersonation", [x["rule"] for x in findings])

    def test_negative_opinion_not_spam(self):
        self.assertEqual(self.scan(["Mình không thích poster lần này."])[0], [])

    def test_allowlisted_fan_cheer_not_duplicate_flag(self):
        self.assertEqual(self.scan(["Juhoon fighting!"] * 4)[0], [])

    def test_long_repeats_are_info_only(self):
        findings, _ = self.scan(["Một nội dung lặp lại trong bình luận"] * 3)
        self.assertTrue(findings)
        self.assertTrue(all(x["level"] == "info" for x in findings))

    def test_hostname_confusion(self):
        findings, hosts = self.scan(["https://facebook.com@evil.example.invalid/login"])
        self.assertEqual(hosts, ["evil.example.invalid"])
        self.assertIn("url-userinfo", [x["rule"] for x in findings])

    def test_trust_is_exact_host_not_suffix(self):
        policy = dict(POLICY, trusted_domains=["example.org"])
        _, hosts = self.scan(["https://example.org/x https://example.org.evil.invalid/x"], policy)
        self.assertEqual(hosts, ["example.org.evil.invalid"])

    def test_unlisted_is_not_malicious_verdict(self):
        findings, _ = self.scan(["https://new.example.invalid"])
        self.assertEqual(findings[0]["level"], "info")
        self.assertIn("does not mean malicious", findings[0]["reason"])

    def test_no_raw_text_in_findings(self):
        findings, _ = self.scan(["PRIVATE-MESSAGE https://new.example.invalid"])
        self.assertNotIn("PRIVATE-MESSAGE", json.dumps(findings))


class FakeGraph:
    def __init__(self):
        self.config = SimpleNamespace(page_id=PAGE)
        self.post = {"id": POST, "message": "Approved caption", "permalink_url": "https://www.facebook.com/Juhoonity/posts/pfbidTEST"}
        self.comments = Batch([], "empty_visible")
        self.conversations = Batch([], "empty_visible")
        self.objects = {}

    def edge(self, parts, fields, **kwargs):
        if parts == (PAGE, "posts"):
            return Batch([deepcopy(self.post)])
        if parts == (POST, "comments"):
            if isinstance(self.comments, Exception):
                raise self.comments
            return self.comments
        if parts == (PAGE, "conversations"):
            if isinstance(self.conversations, Exception):
                raise self.conversations
            return self.conversations
        raise AssertionError("Unexpected edge")

    def get(self, parts, **kwargs):
        if parts == ("me",):
            return {"id": PAGE}
        value = self.objects[parts[0]]
        if isinstance(value, Exception):
            raise value
        return deepcopy(value)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "state.sqlite3")
        self.graph = FakeGraph()
        self.app = PageWatch(self.graph, self.store, POLICY)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_permalink_pfbid_resolves_to_own_page(self):
        self.assertEqual(self.app.resolve(URL)["id"], POST)

    def test_share_url_is_not_falsely_resolved(self):
        with self.assertRaisesRegex(InputError, "share"):
            self.app.resolve("https://www.facebook.com/share/19hLTP7mxR/")

    def test_foreign_page_rejected(self):
        with self.assertRaisesRegex(InputError, "differs"):
            self.app.resolve(URL.replace(PAGE, "999"))

    def test_foreign_rows_rejected(self):
        self.graph.post["id"] = "999_123"
        with self.assertRaisesRegex(GraphError, "ownership"):
            self.app.resolve(URL)

    def test_user_token_not_accepted(self):
        with patch.object(self.graph, "get", return_value={"id": "USER"}):
            with self.assertRaisesRegex(InputError, "Page access token"):
                self.app.assert_page()

    def test_first_scan_baseline_then_diff_is_retained(self):
        self.app.scan_post(URL)
        self.graph.post["message"] = "Edited caption https://example.invalid"
        second = self.app.scan_post(URL)
        third = self.app.scan_post(URL)
        self.assertIn("caption-changed", [x["rule"] for x in second["findings"]])
        self.assertEqual(second["diff"], third["diff"])
        self.assertEqual(self.store.baseline(PAGE, POST)["message"], "Approved caption")

    def test_accept_updates_only_explicit_baseline(self):
        self.app.scan_post(URL)
        self.graph.post["message"] = "Reviewed edit"
        self.app.accept_post(URL)
        result = self.app.scan_post(URL)
        self.assertFalse(result["diff"])
        self.assertEqual(self.store.baseline(PAGE, POST)["message"], "Reviewed edit")

    def test_missing_caption_does_not_erase_baseline(self):
        self.app.scan_post(URL)
        self.graph.post.pop("message")
        result = self.app.scan_post(URL)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(self.store.baseline(PAGE, POST)["message"], "Approved caption")
        with self.assertRaises(InputError):
            self.app.accept_post(URL)

    def test_comment_failure_explicit_and_saved(self):
        self.graph.comments = GraphError("Permission denied")
        result = self.app.scan_post(URL)
        self.assertEqual(result["status"], "partial")
        self.assertIn("not analyzed", " ".join(result["notes"]))
        self.assertEqual(self.store.latest(PAGE, "post")["status"], "partial")

    def test_inbox_unavailable_not_zero_spam(self):
        self.graph.conversations = GraphError("Permission denied")
        result = self.app.scan_inbox()
        self.assertEqual(result["status"], "unavailable")

    def test_inbox_direction_privacy_and_coverage(self):
        self.graph.conversations = Batch([{"id": "c1"}])
        self.graph.objects = {
            "c1": {"messages": {"data": [{"id": x} for x in ("in", "out", "unknown", "image", "failed")], "paging": {"next": "ignored"}}},
            "in": {"from": {"id": "SENDER-PRIVATE"}, "message": "PRIVATE-TEXT https://evil.example.invalid"},
            "out": {"from": {"id": PAGE}, "message": "Page reply https://outgoing.invalid"},
            "unknown": {"message": "no direction"},
            "image": {"from": {"id": "SENDER"}},
            "failed": GraphError("Not readable"),
        }
        result = self.app.scan_inbox()
        self.assertEqual(result["counts"]["inbound_text_analyzed"], 1)
        self.assertEqual(result["counts"]["outgoing_skipped"], 1)
        self.assertEqual(result["counts"]["unknown_sender_skipped"], 1)
        self.assertEqual(result["counts"]["nontext_skipped"], 1)
        self.assertEqual(result["status"], "partial")
        saved = json.dumps(self.store.latest(PAGE, "inbox"))
        for secret in ("PRIVATE-TEXT", "SENDER-PRIVATE", "outgoing.invalid"):
            self.assertNotIn(secret, saved)

    def test_page_state_is_separate(self):
        self.app.scan_post(URL)
        self.assertIsNone(self.store.baseline("OTHER", POST))
        self.assertIsNone(self.store.latest("OTHER", "post"))

    def test_markdown_in_caption_stays_code(self):
        self.app.scan_post(URL)
        self.graph.post["message"] = "# FAKE HEADING\n<script>bad()</script>"
        text = render([self.app.scan_post(URL)])
        self.assertNotIn("\n# FAKE HEADING", text)
        self.assertIn("    +# FAKE HEADING", text)

    def test_cross_source_match_time_bounded(self):
        base = {"at": "2026-10-22T10:00:00+00:00", "target": "sample", "status": "ok", "notes": [], "counts": {}, "findings": [], "hosts": ["evil.invalid"]}
        post, inbox = dict(base, kind="post"), dict(base, kind="inbox")
        self.assertIn("Shared unlisted hosts: evil.invalid", render([post, inbox]))
        inbox["at"] = "2026-10-20T10:00:00+00:00"
        self.assertIn("Shared unlisted hosts: none", render([post, inbox]))


class SetupTests(unittest.TestCase):
    def test_missing_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SetupError):
                Config.from_env()

    def test_config_repr_does_not_reveal_token(self):
        self.assertNotIn("SECRET", repr(Config(PAGE, "SECRET", "v99.0")))

    def test_version_is_explicit_not_guessed(self):
        with patch.dict(os.environ, {"META_PAGE_ID": PAGE, "META_PAGE_TOKEN": "SECRET", "META_GRAPH_VERSION": "latest"}, clear=True):
            with self.assertRaises(SetupError):
                Config.from_env()

    def test_demo_works_without_token_and_no_database(self):
        with tempfile.TemporaryDirectory() as directory:
            old = Path.cwd()
            try:
                os.chdir(directory)
                with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["demo"]), 0)
                self.assertIn("SYNTHETIC DEMO", Path("reports/demo.md").read_text(encoding="utf-8"))
                self.assertFalse(Path("private").exists())
            finally:
                os.chdir(old)
