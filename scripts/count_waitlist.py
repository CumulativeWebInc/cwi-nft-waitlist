#!/usr/bin/env python3
"""Demand engine for the Founding Signal waitlist.

Counts open GitHub issues labeled `waitlist`, breaks them down by the
"Which class interests you?" template field, and writes a public,
machine-readable snapshot to data/demand.json.

Honest numbers only: zero is a number. Issues are public and auditable at:
https://github.com/CumulativeWebInc/cwi-nft-waitlist/issues?q=is%3Aissue+is%3Aopen+label%3Awaitlist
"""
import json
import os
import re
import sys
import urllib.request

REPO = "CumulativeWebInc/cwi-nft-waitlist"
API = "https://api.github.com"
GATE_THRESHOLD = 75

CLASS_OPTIONS = [
    "No preference",
    "Origin",
    "Vector",
    "Phantom",
    "Crown Signal",
]

# Template renders the dropdown answer as "### Which class interests you?\n\n<value>"
CLASS_RE = re.compile(r"### Which class interests you\?\s*\n\s*\n\s*(.+)", re.IGNORECASE)


def normalize_class(raw):
    """Map a raw template answer to a canonical class key, or None."""
    if not raw:
        return None
    value = raw.strip()
    for opt in CLASS_OPTIONS:
        if value.lower() == opt.lower():
            return opt
    for key in ["Origin", "Vector", "Phantom", "Crown Signal"]:
        if key.lower() in value.lower():
            return key
    return "No preference"


def tally_issues(issues):
    """Pure function: issues -> snapshot dict. Fully unit-testable.

    `issues` is a list of dicts with keys: state, labels (list of names),
    body (str), number, created_at, updated_at.
    """
    by_class = {c: 0 for c in CLASS_OPTIONS}
    counted = []
    for issue in issues:
        if issue.get("state") != "open":
            continue
        labels = [l if isinstance(l, str) else l.get("name") for l in issue.get("labels", [])]
        if "waitlist" not in labels:
            continue
        match = CLASS_RE.search(issue.get("body") or "")
        cls = normalize_class(match.group(1) if match else None)
        if cls is None:
            cls = "No preference"
        by_class[cls] += 1
        counted.append(
            {
                "number": issue.get("number"),
                "class": cls,
                "created_at": issue.get("created_at"),
            }
        )
    total = len(counted)
    return {
        "collection": "The Logo Protocol: Founding Signal",
        "total": total,
        "by_class": by_class,
        "gate_threshold": GATE_THRESHOLD,
        "gate": {
            "demand_gate_met": total >= GATE_THRESHOLD,
            "note": (
                "Mint gate is CLOSED. A mint requires 75 qualified members "
                "(wallet readiness + utility interest confirmed) plus four "
                "further gates: utility calendar, rights, technology, control. "
                "Counts below are raw interest from open waitlist issues."
            ),
        },
        "issues": sorted(counted, key=lambda i: i["number"]),
        "source": "https://github.com/%s/issues?q=is:issue+is:open+label:waitlist" % REPO,
        "updated_at": None,  # filled in by main()
    }


def fetch_issues(token):
    """Fetch all issues (open+closed) carrying the waitlist label, paginated."""
    issues = []
    url = "%s/repos/%s/issues?state=all&labels=waitlist&per_page=100" % (API, REPO)
    while url:
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                                   "X-GitHub-Api-Version": "2022-11-28"})
        if token:
            req.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(req) as resp:
            page = json.loads(resp.read().decode())
            issues.extend(page)
            link = resp.headers.get("Link", "")
            nxt = re.search(r'<([^>]+)>;\s*rel="next"', link)
            url = nxt.group(1) if nxt else None
    return [
        {
            "number": i.get("number"),
            "state": i.get("state"),
            "labels": [l.get("name") for l in i.get("labels", [])],
            "body": i.get("body") or "",
            "created_at": i.get("created_at"),
            "updated_at": i.get("updated_at"),
        }
        for i in issues
        if "pull_request" not in i
    ]


def main():
    from datetime import datetime, timezone

    out_path = sys.argv[1] if len(sys.argv) > 1 else "data/demand.json"
    token = os.environ.get("GITHUB_TOKEN")
    issues = fetch_issues(token)
    snap = tally_issues(issues)
    snap["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(snap, f, indent=2)
        f.write("\n")
    print("wrote %s: total=%d (gate %s)" % (
        out_path, snap["total"],
        "MET" if snap["gate"]["demand_gate_met"] else "CLOSED"))


if __name__ == "__main__":
    main()
