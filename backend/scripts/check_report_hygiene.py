"""Refuse to publish test reports that carry secrets, real addresses, or fixture content.

CI uploads JUnit and coverage reports as build artifacts (issue #58), and anyone who can
read the repository's Actions tab can download them. A passing report holds little more
than test names and line counts, but a *failing* one embeds assertion messages and
captured output -- which is exactly where a token, a key, or a decrypted file would land
if a test printed it. This scans every file under the given directories and fails if it
finds any of:

* a PEM block of any kind (private or public key material);
* a session token in this application's `at_`/`rt_` format, or any `Bearer` credential;
* an email address outside the reserved example domains the suites use;
* a known plaintext sentence from a test fixture, which would mean decrypted file content
  reached the report.

    .venv/bin/python scripts/check_report_hygiene.py reports/ other-reports/

It prints the file and the kind of finding, never the matched text itself.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_EMAIL_DOMAINS = {"example.com", "example.org", "example.net", "example.invalid"}

PATTERNS: dict[str, re.Pattern[str]] = {
    "PEM block": re.compile(r"-----BEGIN [A-Z0-9 ]+-----"),
    "session token": re.compile(r"\b(?:at|rt)_[A-Za-z0-9_\-]{20,}"),
    "bearer credential": re.compile(r"Bearer\s+[A-Za-z0-9._~+/\-]{16,}=*"),
}
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@([A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+)")

# Plaintext the suites encrypt. If one of these appears in a report, a decrypted file (or
# the fixture itself) was printed by a failing test.
FIXTURE_PLAINTEXT = (
    "MCS21 demo file",
    "the server must never be able to read this sentence",
    "chapter one, and everything after it",
    "synthetic fixture bytes, not a real document",
    "uploaded before the passphrase reset",
    "end-to-end upload check",
)


def scan_text(text: str) -> list[str]:
    findings = [name for name, pattern in PATTERNS.items() if pattern.search(text)]
    for match in EMAIL.finditer(text):
        if match.group(1).lower() not in ALLOWED_EMAIL_DOMAINS:
            findings.append("email address outside the example domains")
            break
    if any(sentinel in text for sentinel in FIXTURE_PLAINTEXT):
        findings.append("fixture plaintext")
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: check_report_hygiene.py <report-dir> [<report-dir> ...]", file=sys.stderr)
        return 2

    files = []
    for root in map(Path, argv[1:]):
        if not root.exists():
            print(f"check_report_hygiene: {root} does not exist", file=sys.stderr)
            return 2
        files.extend(p for p in ([root] if root.is_file() else root.rglob("*")) if p.is_file())

    problems = 0
    for path in sorted(files):
        text = path.read_bytes().decode("utf-8", errors="replace")
        for finding in scan_text(text):
            problems += 1
            print(f"check_report_hygiene: {path}: {finding}", file=sys.stderr)

    if problems:
        print(
            f"check_report_hygiene: {problems} finding(s); refusing to publish these reports",
            file=sys.stderr,
        )
        return 1
    print(f"check_report_hygiene: {len(files)} report file(s) clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
