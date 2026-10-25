import re
from urllib.parse import parse_qs, urlsplit


class InputError(ValueError):
    pass


def post_key(url):
    if any(ord(c) < 33 or ord(c) == 127 for c in url.strip()):
        raise InputError("Post URL contains whitespace or control characters.")
    try:
        parsed = urlsplit(url.strip())
        if (parsed.scheme != "https" or parsed.hostname not in {
            "facebook.com", "www.facebook.com", "m.facebook.com", "mbasic.facebook.com"
        } or parsed.username or parsed.password or parsed.port not in (None, 443)):
            raise ValueError
    except ValueError:
        raise InputError("Use an HTTPS Facebook post permalink, without login data.") from None
    if parsed.path.startswith("/share/"):
        raise InputError("Opaque /share/ URL: click the post date/time, or run 'posts' and copy a returned URL.")
    query = parse_qs(parsed.query)
    story = query.get("story_fbid", [None])[0]
    owner = query.get("id", [None])[0]
    if not story:
        match = re.fullmatch(r"/[^/]+/posts/([A-Za-z0-9]+)(?:/)?", parsed.path)
        story = match.group(1) if match else None
    if not story or not re.fullmatch(r"(?:pfbid[A-Za-z0-9]+|[0-9]+)", story):
        raise InputError("Unsupported post URL. MVP supports regular Page posts, not Stories/Reels/photo links.")
    return story, owner
