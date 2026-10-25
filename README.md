# PageWatch

A Python command-line tool for Facebook fanpage administrators: track visible caption changes, review comment text for spam/phishing cues, and sample inbound Page messages.

## Pilot results

A Juhoonity pilot on **24 October 2026** analyzed **69 API-visible comments across five posts** and **16 inbound text messages**. One informational domain finding was recorded. The pilot does not establish spam-detection accuracy or complete visibility of Page data.

- [Pilot evaluation](docs/EVALUATION.md)
- [Verification record](VERIFICATION.md)
- [Synthetic example report](examples/demo-report.md)

## Run locally or in Codespaces

Python 3.11 or later; standard library only.

~~~sh
python -m unittest discover -s tests -v
python -m pagewatch demo
~~~

The demo uses synthetic data and writes `reports/demo.md`. For live access, set `META_PAGE_ID`, `META_PAGE_TOKEN` and `META_GRAPH_VERSION` as environment variables or Codespaces secrets. Use a Page token that identifies the configured Page and the Graph version supported by your Meta app.

~~~sh
python -m pagewatch doctor
python -m pagewatch posts --limit 20
python -m pagewatch scan-post "YOUR_OWN_PAGE_POST_PERMALINK"
python -m pagewatch scan-inbox --conversations 5 --messages 10
~~~

Read the coverage notes in `reports/latest.md` before interpreting findings. Each source scan has its own timestamp.

## Implementation

| Module | Responsibility |
|---|---|
| `config.py` | Environment settings and local policy |
| `graph.py` | Bounded GET requests and cursor pagination |
| `urls.py` | Supported Facebook post permalink validation |
| `service.py` | Page ownership checks, caption snapshots, comments and inbound messages |
| `analyze.py` | Text normalization and explainable review rules |
| `store.py` | Local SQLite baselines and scan summaries |
| `report.py` | Markdown output, caption differences and shared-domain review |
| `cli.py` | Command-line interface and synthetic demo |

The first visible caption becomes a baseline. Future scans compare against it without silently replacing it. Use `accept-post` only after reviewing an intentional change.

## Scope and limitations

- Read and flag only; scans are started manually.
- Only API-visible top-level text comments are analyzed. Replies, images, posters, OCR and attachments are outside the current scope.
- Inbox access covers a limited sample of visible conversations, not every folder or the complete message history.
- An unlisted host or a repeated fan cheer is a review cue, not proof of spam or malicious activity.
- Caption differences do not identify an editor or establish account compromise.
- Shared hosts across eligible samples do not establish the same sender or attacker.
- App permissions, access levels, Page tasks and token validity affect data visibility.
- This prototype does not verify news, prevent document leaks, block users or perform penetration testing of Facebook.

## Data handling

Tokens remain in environment variables. Inbox bodies and sender IDs are processed transiently and are not intentionally stored in scan summaries. Caption baselines, differences, hashed references and hostnames are stored locally.

`private/`, `reports/`, `.env` and database files are excluded from Git. Keep live scan data and credentials private even when publishing the source code. Review reports before sharing them; see [SECURITY.md](SECURITY.md).
