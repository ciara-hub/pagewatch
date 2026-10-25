import json
import os
import re
from dataclasses import dataclass
from pathlib import Path


class SetupError(ValueError):
    pass


@dataclass(frozen=True, repr=False)
class Config:
    page_id: str
    token: str
    version: str

    @classmethod
    def from_env(cls):
        names = ("META_PAGE_ID", "META_PAGE_TOKEN", "META_GRAPH_VERSION")
        values = [os.environ.get(name, "").strip() for name in names]
        missing = [name for name, value in zip(names, values) if not value]
        if missing:
            raise SetupError("Missing Codespaces secrets: " + ", ".join(missing))
        page, token, version = values
        if not page.isascii() or not page.isdigit():
            raise SetupError("META_PAGE_ID must contain digits only.")
        if not re.fullmatch(r"v\d+\.\d+", version):
            raise SetupError("META_GRAPH_VERSION must match Graph API Explorer, e.g. vNN.0.")
        if any(ord(c) < 33 or ord(c) > 126 for c in token):
            raise SetupError("META_PAGE_TOKEN contains unsupported characters.")
        return cls(page, token, version)


def load_policy(path="policy.json"):
    defaults = {"trusted_domains": [], "ignore_repeat_phrases": [], "repeat_threshold": 3}
    file = Path(path)
    if file.exists():
        try:
            value = json.loads(file.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise SetupError("Cannot read policy.json; check its JSON syntax.") from exc
        if not isinstance(value, dict):
            raise SetupError("policy.json must be a JSON object.")
        defaults.update(value)
    for key in ("trusted_domains", "ignore_repeat_phrases"):
        if not isinstance(defaults[key], list) or not all(isinstance(x, str) for x in defaults[key]):
            raise SetupError(key + " must be a list of strings.")
    if type(defaults["repeat_threshold"]) is not int or not 3 <= defaults["repeat_threshold"] <= 20:
        raise SetupError("repeat_threshold must be an integer from 3 to 20.")
    return defaults
