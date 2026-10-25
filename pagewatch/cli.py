import argparse
import sqlite3
from pathlib import Path

from .analyze import analyze
from .config import Config, SetupError, load_policy
from .graph import Graph, GraphError
from .report import render, write_report
from .service import PageWatch, now
from .store import Store
from .urls import InputError, post_key


def bounded(low, high):
    def convert(raw):
        value = int(raw)
        if not low <= value <= high:
            raise argparse.ArgumentTypeError("Use a value from " + str(low) + " to " + str(high))
        return value
    return convert


def demo(policy):
    # Reserved .invalid domain; these are not messages from Juhoonity or any real user.
    items = [{"id": "synthetic-1", "message": "META support: page bi khoa trong 24h! Dang nhap, gui mat khau tai https://verify.example.invalid/form"}]
    findings, hosts = analyze(items, policy, "DEMO")
    results = []
    for kind in ("post", "inbox"):
        results.append({"kind": kind, "at": now(), "status": "synthetic_only", "target": "DEMO", "counts": {"synthetic_texts": 1}, "notes": ["Fabricated sample, no Facebook connection. Not pilot evidence."], "findings": findings, "hosts": hosts})
    path = Path("reports/demo.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(results, demo=True), encoding="utf-8")
    print("SYNTHETIC DEMO only. Open reports/demo.md; no Facebook data was read.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="PageWatch: read-only review of your own Facebook Page.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("demo", "doctor", "report"):
        commands.add_parser(name)
    posts = commands.add_parser("posts")
    posts.add_argument("--limit", type=bounded(1, 500), default=20)
    for name in ("scan-post", "accept-post"):
        command = commands.add_parser(name)
        command.add_argument("url")
        command.add_argument("--lookup", type=bounded(1, 500), default=100)
        if name == "scan-post":
            command.add_argument("--comments", type=bounded(1, 200), default=50)
    inbox = commands.add_parser("scan-inbox")
    inbox.add_argument("--conversations", type=bounded(1, 5), default=5)
    inbox.add_argument("--messages", type=bounded(1, 10), default=10)
    args = parser.parse_args(argv)
    store = None
    try:
        policy = load_policy()
        if args.command == "demo":
            demo(policy)
            return 0
        if args.command == "report":
            # Report is offline; a token is deliberately not needed.
            import os
            page = os.environ.get("META_PAGE_ID", "").strip()
            if not page.isascii() or not page.isdigit():
                raise SetupError("Set META_PAGE_ID to select the local Page report.")
            store = Store()
            print("Report saved: " + str(write_report(store, page)))
            return 0
        config = Config.from_env()
        graph = Graph(config)
        store = Store()
        app = PageWatch(graph, store, policy)
        if args.command == "doctor":
            checks = app.doctor()
            for name, status, note in checks:
                print(name + " | " + status + " | " + note)
            return 1 if any(c[1] in ("unavailable", "not_tested", "partial") for c in checks) else 0
        # Verify Page identity before any data scan or baseline acceptance.
        app.assert_page()
        if args.command == "posts":
            batch = app.catalog(args.limit)
            print("Posts: " + batch.status + "; visible rows: " + str(len(batch.items)))
            for row in batch.items:
                url = row.get("permalink_url", "")
                try:
                    post_key(url)
                    print(url)
                except InputError:
                    print("Post has no supported permalink in API response.")
            if batch.note:
                print(batch.note)
            return 2 if batch.status == "partial" else 0
        if args.command == "accept-post":
            app.accept_post(args.url, args.lookup)
            print("Current visible caption accepted as the new baseline. Run scan-post again to refresh the report.")
            return 0
        if args.command == "scan-post":
            result = app.scan_post(args.url, args.comments, args.lookup)
        else:
            result = app.scan_inbox(args.conversations, args.messages)
        write_report(store, config.page_id)
        print("Scan status: " + result["status"] + "; findings: " + str(len(result["findings"])))
        print("Open reports/latest.md. Read its coverage notes before interpreting findings.")
        return 2 if result["status"] in ("partial", "unavailable", "empty_visible") else 0
    except (SetupError, InputError, GraphError) as exc:
        print("PageWatch: " + str(exc))
        return 1
    except (OSError, sqlite3.Error, ValueError):
        print("PageWatch: local data/config could not be read or written. Check the guide; no successful scan is claimed.")
        return 1
    finally:
        if store:
            store.close()
