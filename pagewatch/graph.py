"""Fixed-host, GET-only Graph client. Never visits links found in messages."""

import http.client
import json
from dataclasses import dataclass
from urllib.parse import quote, urlencode


class GraphError(RuntimeError):
    """Messages are generated locally: server text/tokens are never displayed."""


@dataclass
class Batch:
    items: list
    status: str = "ok"
    note: str = ""


class Graph:
    def __init__(self, config, connection_factory=None):
        self.config = config
        self.connection_factory = connection_factory or http.client.HTTPSConnection
        self.requests = 0

    def get(self, parts, **params):
        if not parts or any(not isinstance(p, str) or not p for p in parts):
            raise GraphError("Invalid Graph object path.")
        if "access_token" in params:
            raise GraphError("Token query parameters are disabled.")
        if self.requests >= 120:
            raise GraphError("Request budget reached; reduce scan limits.")
        self.requests += 1
        path = "/" + self.config.version + "/" + "/".join(quote(p, safe="") for p in parts)
        if params:
            path += "?" + urlencode(params)
        connection = self.connection_factory("graph.facebook.com", timeout=15)
        try:
            connection.request("GET", path, headers={
                "Authorization": "Bearer " + self.config.token,
                "Accept": "application/json",
                "User-Agent": "PageWatch/0.1 (educational read-only review)",
            })
            response = connection.getresponse()
            if 300 <= response.status < 400:
                raise GraphError("Graph redirect refused; no other host was contacted.")
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise GraphError("Graph response exceeded 2 MB; reduce limits.")
            try:
                body = json.loads(raw)
            except (ValueError, UnicodeError):
                raise GraphError("Graph returned unreadable JSON.") from None
            if not isinstance(body, dict):
                raise GraphError("Unexpected Graph response shape.")
            if response.status != 200 or "error" in body:
                error = body.get("error", {})
                code = error.get("code") if isinstance(error, dict) else None
                hint = {
                    190: "Token expired or invalid; replace the Page token.",
                    10: "Permission/access level denied; check the app and Page tasks.",
                    200: "Permission/access level denied; check the app and Page tasks.",
                    100: "Object, field, permission or API version is unavailable; verify in Explorer.",
                    4: "API rate limit reached; try again later.",
                    613: "API rate limit reached; try again later.",
                }.get(code, "Request unavailable; check the same request in Graph API Explorer.")
                safe_code = str(code) if type(code) is int else "unknown"
                raise GraphError("Graph HTTP " + str(response.status) + ", code " + safe_code + ": " + hint)
            return body
        except (OSError, http.client.HTTPException):
            raise GraphError("Network/TLS failure contacting Graph; no scan conclusion is possible.") from None
        finally:
            connection.close()

    def edge(self, parts, fields, limit=50, **params):
        """Use only Graph cursors on the original edge, never paging.next URLs."""
        items, seen, after = [], set(), None
        for _ in range(10):
            query = dict(params, fields=fields, limit=min(100, limit - len(items)))
            if after:
                query["after"] = after
            try:
                data = self.get(parts, **query)
                rows = data.get("data")
                if not isinstance(rows, list) or not all(isinstance(x, dict) for x in rows):
                    raise GraphError("Expected a Graph data list; access was not confirmed.")
            except GraphError as exc:
                if items:
                    return Batch(items, "partial", str(exc))
                raise
            remaining = limit - len(items)
            items.extend(rows[:remaining])
            paging = data.get("paging") or {}
            more = bool(paging.get("next")) or len(rows) > remaining
            if len(items) >= limit:
                return Batch(items, "limited" if more else "ok", "Item limit reached." if more else "")
            if not more:
                return Batch(items, "ok" if items else "empty_visible")
            after = (paging.get("cursors") or {}).get("after")
            if not isinstance(after, str) or not after or after in seen:
                return Batch(items, "partial", "Missing or repeated pagination cursor; stopped.")
            seen.add(after)
        return Batch(items, "partial", "Pagination page budget reached.")
