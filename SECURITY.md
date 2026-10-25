# Scope and data handling

Use only Pages you are authorized to manage and test. Official API access is required; no scraping login sessions or bypassing access restrictions.

The client exposes GET only, pins its destination to graph.facebook.com, uses TLS, refuses redirects, limits response size/time/request counts, and places the token in an Authorization header. Pagination reuses the original edge with a cursor; it never follows arbitrary paging.next hosts. Server error bodies are not echoed to the terminal.

The analyzer never visits comment/message links. This reduces exposure; it also means it cannot certify a URL's final destination, malware status or reputation. Allowlist entries are exact hostnames, without wildcard subdomains.

The CLI checks that /me identifies the configured Page. Post matching is limited to that Page's returned posts, with an ownership-checked numeric-ID fallback. Opaque share links, unsupported formats and unresolved older posts fail with guidance.

Reports contain no deliberately stored sender names/raw inbox texts, but can contain hostnames, hashed object references and captions/diffs. These remain private by default. Gitignore only affects untracked files; it does not remove content already committed or keep other people out of your Codespace. Local SQLite is unencrypted.

Retain pilot data only as long as needed for review; a suggested initial window is seven days. There is no automatic expiry/cleanup in v0.1.0. After retaining only aggregate/redacted evidence, delete the specific local database and report files through your editor if they are no longer needed. This resets saved caption baselines.

If a token leaks, revoke/regenerate it in Meta first, replace the Codespaces secret and restart the Codespace. Removing the visible line from the latest commit alone is not sufficient to revoke a token.

Do not put real tokens, messages, raw API responses or unredacted screenshots in issues, pull requests or CI artifacts. To report a code bug, use a synthetic reproduction with invented content and IDs.
