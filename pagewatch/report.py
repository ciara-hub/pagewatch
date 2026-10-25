from datetime import datetime
from pathlib import Path


def block(value):
    # All external text is rendered as code, including text containing Markdown/HTML.
    text = "".join(c if c in "\n\t" or ord(c) >= 32 else "?" for c in str(value))
    return "\n".join("    " + line for line in text.splitlines()) + "\n"


def render(results, demo=False):
    lines = ["# PageWatch — " + ("SYNTHETIC DEMO" if demo else "local review report"), "",
             "Rule findings are review cues, not proof of scams, misinformation or account compromise.",
             "Only the latest saved post scan and latest saved inbox scan for this Page are shown.", ""]
    for result in results:
        lines += ["## " + result["kind"], "", block("Time (UTC): " + result["at"] + "\nStatus: " + result["status"] + "\nTarget ref: " + result["target"])]
        for key, count in result["counts"].items():
            lines.append(block(key + ": " + str(count)))
        for note in result["notes"]:
            lines.append(block(note))
        if not result["findings"]:
            lines.append("No rule findings in the analyzed sample; check coverage/status before interpreting.\n")
        for item in result["findings"]:
            lines.append(block(item["level"] + " | " + item["rule"] + " | ref " + item["ref"] + "\n" + item["reason"]))
        if result.get("diff"):
            lines += ["### Caption diff (local only)", "", block(result["diff"])]
    by_kind = {r["kind"]: r for r in results}
    if "post" in by_kind and "inbox" in by_kind:
        post, inbox = by_kind["post"], by_kind["inbox"]
        age = abs((datetime.fromisoformat(post["at"]) - datetime.fromisoformat(inbox["at"])).total_seconds())
        shared = set(post["hosts"]) & set(inbox["hosts"]) if age <= 86400 else set()
        lines += ["## Cross-source review", "", "Only samples taken within 24 hours of each other are compared. Matching hosts do not establish the same sender or malicious intent.", ""]
        lines.append(block("Shared unlisted hosts: " + (", ".join(sorted(shared)) if shared else "none in eligible samples")))
    return "\n".join(lines)


def write_report(store, page, path="reports/latest.md"):
    results = [store.latest(page, kind) for kind in ("post", "inbox")]
    results = [r for r in results if r]
    if not results:
        raise ValueError("No saved scans for this Page. Run scan-post or scan-inbox first.")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(results), encoding="utf-8")
    return target
