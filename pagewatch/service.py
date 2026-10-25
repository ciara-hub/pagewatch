import difflib
from datetime import datetime, timezone

from .analyze import analyze, finding, reference
from .graph import GraphError
from .urls import InputError, post_key


POST_FIELDS = "id,message,permalink_url,created_time,updated_time"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PageWatch:
    def __init__(self, graph, store, policy):
        self.graph, self.store, self.policy = graph, store, policy
        self.page = graph.config.page_id

    def assert_page(self):
        data = self.graph.get(("me",), fields="id,name")
        if str(data.get("id")) != self.page:
            raise InputError("Token does not identify the configured Page. Use its Page access token, not a user token.")
        return data

    def catalog(self, limit=100):
        batch = self.graph.edge((self.page, "posts"), POST_FIELDS, limit=limit)
        if any(not str(p.get("id", "")).startswith(self.page + "_") for p in batch.items):
            raise GraphError("Page ownership could not be confirmed for returned posts.")
        return batch

    def resolve(self, url, lookup=100):
        key, owner = post_key(url)
        if owner and owner != self.page:
            raise InputError("URL Page ID differs from META_PAGE_ID; check which Page is connected.")
        batch = self.catalog(lookup)
        for post in batch.items:
            try:
                candidate, _ = post_key(post.get("permalink_url", ""))
            except InputError:
                candidate = None
            if key == candidate or str(post["id"]).split("_", 1)[-1] == key:
                return post
        if key.isdigit():
            post = self.graph.get((self.page + "_" + key,), fields=POST_FIELDS + ",from")
            if str((post.get("from") or {}).get("id")) == self.page and post.get("id") == self.page + "_" + key:
                return post
        raise InputError("Post not resolved among visible own-Page posts. Run 'posts --limit 200'; copy a returned URL or increase --lookup (max 500). Older/unsupported posts or missing access may remain unavailable.")

    def scan_post(self, url, comments=50, lookup=100):
        post = self.resolve(url, lookup)
        post_id = str(post["id"])
        result = {"kind": "post", "at": now(), "target": reference(self.page, post_id),
                  "status": "ok", "notes": [], "counts": {}, "findings": [], "hosts": [], "diff": ""}
        if isinstance(post.get("message"), str):
            snapshot = {"message": post["message"], "captured_at": result["at"]}
            baseline = self.store.baseline(self.page, post_id)
            if baseline is None:
                self.store.accept(self.page, post_id, snapshot)
                result["notes"].append("First visible caption saved as baseline. This says nothing about earlier edits.")
            elif snapshot["message"] != baseline["message"]:
                result["findings"].append(finding("review", "caption-changed", result["target"], "Published caption differs from the approved baseline at " + baseline["captured_at"] + ". Editor identity/cause is unknown."))
                result["diff"] = "\n".join(difflib.unified_diff(baseline["message"].splitlines(), snapshot["message"].splitlines(), fromfile="approved-baseline", tofile="current-caption", lineterm=""))
                result["notes"].append("Baseline kept. Use accept-post only after reviewing this change.")
            else:
                result["notes"].append("Caption matches saved baseline. Posters/images/attachments were not compared.")
        else:
            result["status"] = "partial"
            result["notes"].append("Caption field unavailable/non-text; baseline was not created or replaced.")
        try:
            batch = self.graph.edge((post_id, "comments"), "id,message,created_time", limit=comments, filter="toplevel")
            texts = [{"id": str(x.get("id", i)), "message": x["message"]} for i, x in enumerate(batch.items) if isinstance(x.get("message"), str) and x["message"].strip()]
            findings, hosts = analyze(texts, self.policy, self.page)
            result["findings"].extend(findings)
            result["hosts"] = hosts
            result["counts"] = {"comments_received": len(batch.items), "text_comments_analyzed": len(texts), "nontext_or_empty_skipped": len(batch.items) - len(texts)}
            if result["status"] != "partial":
                result["status"] = batch.status
            result["notes"].extend(["Comment scope: visible top-level comments returned by API; replies are not traversed.", "Comment access: " + batch.status + ("; " + batch.note if batch.note else "")])
        except GraphError as exc:
            result["status"] = "partial"
            result["notes"].append("Comments unavailable; not analyzed. " + str(exc))
        self.store.save(self.page, result)
        return result

    def accept_post(self, url, lookup=100):
        post = self.resolve(url, lookup)
        if not isinstance(post.get("message"), str):
            raise InputError("No visible text caption; baseline not replaced.")
        self.store.accept(self.page, str(post["id"]), {"message": post["message"], "captured_at": now()})

    def message_ids(self, conversation, limit):
        data = self.graph.get((str(conversation),), fields="messages.limit(" + str(limit) + "){id,created_time}")
        messages = data.get("messages")
        if not isinstance(messages, dict) or not isinstance(messages.get("data"), list):
            raise GraphError("Conversation messages were not returned; message access is unconfirmed.")
        rows = messages["data"]
        if any(not isinstance(row, dict) or not row.get("id") for row in rows):
            raise GraphError("Unexpected message identifier list.")
        more = bool((messages.get("paging") or {}).get("next")) or len(rows) > limit
        return [str(x["id"]) for x in rows[:limit]], more

    def scan_inbox(self, conversations=5, messages=10):
        result = {"kind": "inbox", "at": now(), "target": "Page inbox", "status": "ok",
                  "notes": ["Only API-visible conversations and the first requested message batch per conversation are sampled. Spam/Requests folders and full history are not guaranteed."],
                  "counts": {"conversations_received": 0, "messages_received": 0, "inbound_text_analyzed": 0, "outgoing_skipped": 0, "unknown_sender_skipped": 0, "nontext_skipped": 0, "failed_reads": 0},
                  "findings": [], "hosts": []}
        counts, texts = result["counts"], []
        try:
            batch = self.graph.edge((self.page, "conversations"), "id", limit=conversations, platform="messenger")
        except GraphError as exc:
            result["status"] = "unavailable"
            result["notes"].append(str(exc))
            self.store.save(self.page, result)
            return result
        result["status"] = batch.status
        if batch.note:
            result["notes"].append(batch.note)
        counts["conversations_received"] = len(batch.items)
        for conversation in batch.items:
            try:
                if not conversation.get("id"):
                    raise GraphError("Conversation ID missing.")
                ids, more = self.message_ids(conversation["id"], messages)
                if more and result["status"] == "ok":
                    result["status"] = "limited"
                for mid in ids:
                    try:
                        message = self.graph.get((mid,), fields="id,message,from,created_time")
                        counts["messages_received"] += 1
                        sender = (message.get("from") or {}).get("id")
                        if not sender:
                            counts["unknown_sender_skipped"] += 1
                            result["status"] = "partial"
                        elif str(sender) == self.page:
                            counts["outgoing_skipped"] += 1
                        elif isinstance(message.get("message"), str) and message["message"].strip():
                            texts.append({"id": mid, "message": message["message"]})
                        else:
                            counts["nontext_skipped"] += 1
                    except GraphError as exc:
                        counts["failed_reads"] += 1
                        result["status"] = "partial"
                        if str(exc) not in result["notes"]:
                            result["notes"].append(str(exc))
            except GraphError as exc:
                counts["failed_reads"] += 1
                result["status"] = "partial"
                if str(exc) not in result["notes"]:
                    result["notes"].append(str(exc))
        counts["inbound_text_analyzed"] = len(texts)
        result["findings"], result["hosts"] = analyze(texts, self.policy, self.page)
        if not texts:
            result["notes"].append("No inbound text analyzed. This is not evidence of a spam-free inbox.")
        self.store.save(self.page, result)
        return result

    def doctor(self):
        self.assert_page()
        checks = [("Page token", "ok", "Token identifies the configured Page.")]
        try:
            posts = self.catalog(1)
            checks.append(("Posts", posts.status, "Own-Page post list request succeeded."))
            if posts.items:
                try:
                    batch = self.graph.edge((str(posts.items[0]["id"]), "comments"), "id,message", limit=1, filter="toplevel")
                    checks.append(("Comments", batch.status, "Request succeeded; empty data does not establish full visibility."))
                except GraphError as exc:
                    checks.append(("Comments", "unavailable", str(exc)))
            else:
                checks.append(("Comments", "not_tested", "No visible own-Page post to test."))
        except GraphError as exc:
            checks.extend([("Posts", "unavailable", str(exc)), ("Comments", "not_tested", "Posts unavailable.")])
        try:
            conversations = self.graph.edge((self.page, "conversations"), "id", limit=1, platform="messenger")
            checks.append(("Conversations", conversations.status, "Only API-visible conversations were requested."))
            if conversations.items:
                ids, _ = self.message_ids(conversations.items[0]["id"], 1)
                if ids:
                    message = self.graph.get((ids[0],), fields="id,message,from,created_time")
                    valid = bool((message.get("from") or {}).get("id"))
                    checks.append(("Message detail", "ok" if valid else "not_tested", "Detail request returned; sender field " + ("visible." if valid else "unavailable.")))
                else:
                    checks.append(("Message detail", "not_tested", "No visible message ID to test."))
            else:
                checks.append(("Message detail", "not_tested", "No visible conversation to test."))
        except GraphError as exc:
            checks.append(("Inbox access", "unavailable", str(exc)))
        return checks
