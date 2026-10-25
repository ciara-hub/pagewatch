"""Explainable heuristics, not a truth detector or malware verdict."""

import hashlib
import ipaddress
import re
import unicodedata
from collections import Counter
from urllib.parse import urlsplit


def normalized(text):
    plain = unicodedata.normalize("NFKD", text.casefold().replace("đ", "d"))
    return " ".join("".join(c for c in plain if not unicodedata.combining(c)).split())


def reference(page, object_id):
    return hashlib.sha256((page + ":" + str(object_id)).encode()).hexdigest()[:12]


def links(text):
    return re.findall(r"(?:https?://|www\.)[^\s<>\"']+", text, flags=re.I)


def finding(level, rule, ref, reason):
    return {"level": level, "rule": rule, "ref": ref, "reason": reason}


def analyze(items, policy, page):
    """items contain id and message only. Message bodies are not returned/stored."""
    findings, hosts = [], set()
    trusted = {d.lower().strip().strip(".") for d in policy["trusted_domains"]}
    ignored = {normalized(t) for t in policy["ignore_repeat_phrases"]}
    counts = Counter(normalized(x["message"]) for x in items)
    for item in items:
        text, ref = item["message"], reference(page, item["id"])
        norm = normalized(text)
        credential = any(c in norm for c in ("mat khau", "password", "ma otp", "one time password", "dang nhap", "log in"))
        urgent = any(c in norm for c in ("ngay lap tuc", "khan cap", "24 gio", "24h", "immediately", "urgent", "bi khoa", "disabled"))
        impersonation = any(c in norm for c in ("meta support", "facebook support", "ho tro meta", "ho tro facebook", "bao mat meta"))
        if credential and urgent and impersonation:
            findings.append(finding("high", "credential-impersonation", ref, "Credential request + urgency + support impersonation cues; admin review needed."))
        elif credential and (urgent or impersonation):
            findings.append(finding("review", "credential-pressure", ref, "Credential-related wording combined with urgency/support cues; context may be benign."))
        if len(norm) >= 12 and counts[norm] >= policy["repeat_threshold"] and norm not in ignored:
            findings.append(finding("info", "repeated-text", ref, "Same normalized text appears " + str(counts[norm]) + " times in this scan; repeated cheers may be normal."))
        for raw_url in links(text):
            try:
                parsed = urlsplit(raw_url.rstrip(".,;!?)，。") if "://" in raw_url else "https://" + raw_url.rstrip(".,;!?)"))
                host = (parsed.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
                if not host:
                    continue
                if parsed.username or parsed.password:
                    findings.append(finding("review", "url-userinfo", ref, "URL contains a userinfo section; actual destination host: " + host))
                if host not in trusted:
                    hosts.add(host)
                    findings.append(finding("info", "unlisted-domain", ref, "Host is not in the project allowlist: " + host + ". This alone does not mean malicious."))
                if host in {"bit.ly", "tinyurl.com", "t.co", "cutt.ly", "is.gd"}:
                    findings.append(finding("review", "short-url", ref, "Shortened destination cannot be checked from its text: " + host))
                try:
                    ipaddress.ip_address(host)
                    findings.append(finding("review", "ip-address-url", ref, "URL uses a literal IP address; inspect context manually."))
                except ValueError:
                    pass
            except (ValueError, UnicodeError):
                findings.append(finding("review", "malformed-url", ref, "URL could not be parsed; no destination was opened."))
    return findings, sorted(hosts)
