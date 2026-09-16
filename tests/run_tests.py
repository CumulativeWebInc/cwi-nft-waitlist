#!/usr/bin/env python3
"""Validation suite for the waitlist page build.
1. HTML: parse + required sections/ids + content rules.
2. Issue template YAML: parse + labels + class options + checkboxes.
3. count_waitlist.tally_issues: fixtures for zero/mixed/invalid cases.
Exit non-zero on any failure.
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
failures = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


# ---------- 1. HTML ----------
class TagChecker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        if tag not in ("img", "br", "meta", "link", "input", "hr", "source"):
            self.stack.append(tag)
        for k, v in attrs:
            if k == "id":
                self.ids.add(v)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append(f"mismatched </{tag}>")

    def handle_startendtag(self, tag, attrs):
        for k, v in attrs:
            if k == "id":
                self.ids.add(v)


html = (ROOT / "index.html").read_text(encoding="utf-8")
parser = TagChecker()
parser.feed(html)
check("html: parses without mismatched tags", not parser.errors, str(parser.errors[:3]))
check("html: balanced <html>", html.count("<html") == html.count("</html>") == 1)
for sid in ["thesis", "classes", "utility", "demand", "faq", "gate-count", "d-total",
            "d-origin", "d-vector", "d-phantom", "d-crown", "d-updated", "d-gate", "bar-fill"]:
    check(f"html: id/section #{sid} present", sid in parser.ids or f'id="{sid}"' in html)

# crown appears exactly once, in the Crown Signal card context
crown_hits = html.count("crown.webp")
check("html: crown.webp used exactly once (Crown Signal card only)", crown_hits == 1, f"found {crown_hits}")
crown_ctx = html[html.find("crown.webp") - 400:html.find("crown.webp") + 400]
check("html: crown usage is in Crown Signal class context", "Crown Signal" in crown_ctx, crown_ctx[:120])
# CWI logo branding in header
check("html: CWI logo used as page branding", "cwi-logo.jpg" in html and 'class="brand"' in html)

# anti-hype language (the FAQ legitimately uses "guaranteed return" inside a
# negation that filters out speculators — allowed only in that context)
banned = ["selling fast", "almost gone", "almost sold", "going fast", "don't miss out",
          "floor price", "to the moon", "mint now", "buy now"]
for phrase in banned:
    check(f"html: no hype phrase '{phrase}'", phrase not in html.lower())
guaranteed_hits = [m.start() for m in re.finditer("guaranteed return", html.lower())]
guaranteed_ok = all("not the buyer" in html[max(0, i-80):i+80].lower() for i in guaranteed_hits) and guaranteed_hits
check("html: 'guaranteed return' only inside speculator-filtering sentence", bool(guaranteed_ok))
# required honesty language
for phrase in ["no mint date", "75", "target band", "not an investment", "zero is a number"]:
    check(f"html: honesty phrase present: '{phrase}'", phrase.lower() in html.lower())
for img in ["assets/origin.webp", "assets/vector.webp", "assets/phantom.webp", "assets/crown.webp"]:
    check(f"html: references {img}", img in html)

# ---------- 2. Issue template YAML ----------
import yaml

tpl_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "waitlist-signup.yml"
tpl = yaml.safe_load(tpl_path.read_text(encoding="utf-8"))
check("yaml: parses", isinstance(tpl, dict))
check("yaml: labels == ['waitlist']", tpl.get("labels") == ["waitlist"], str(tpl.get("labels")))
body = tpl.get("body", [])
check("yaml: body has fields", isinstance(body, list) and len(body) >= 5)
dropdown = next((f for f in body if f.get("id") == "class-interest"), None)
check("yaml: class-interest dropdown exists", dropdown is not None)
if dropdown:
    opts = dropdown["attributes"]["options"]
    for opt in ["Origin (44)", "Vector (30)", "Phantom (20)", "Crown Signal (5, KingCode class)", "No preference"]:
        check(f"yaml: dropdown option '{opt}'", opt in opts, str(opts))
    check("yaml: dropdown required", dropdown["validations"]["required"] is True)
checks = next((f for f in body if f.get("id") == "understanding"), None)
check("yaml: understanding checkboxes exist", checks is not None)
if checks:
    opts = checks["attributes"]["options"]
    check("yaml: 3 understanding checkboxes", len(opts) == 3, str(len(opts)))
    check("yaml: all checkboxes required", all(o.get("required") for o in opts))
cfg = yaml.safe_load((ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml").read_text(encoding="utf-8"))
check("yaml: config disables blank issues", cfg.get("blank_issues_enabled") is False)

# ---------- 3. count_waitlist ----------
sys.path.insert(0, str(ROOT / "scripts"))
from count_waitlist import tally_issues, GATE_THRESHOLD, normalize_class

snap = tally_issues([])
check("count: zero issues -> total 0", snap["total"] == 0)
check("count: zero -> gate closed", snap["gate"]["demand_gate_met"] is False)
check("count: gate threshold is 75", GATE_THRESHOLD == 75)


def issue(n, body, state="open", labels=("waitlist",), label_names=None):
    return {"number": n, "state": state,
            "labels": [{"name": l} for l in (label_names if label_names is not None else labels)],
            "body": body, "created_at": "2026-09-16T00:00:00Z"}


b = "### Which class interests you?\n\nOrigin (44)\n\n### Why?"
snap = tally_issues([issue(1, b)])
check("count: Origin counted", snap["by_class"]["Origin"] == 1 and snap["total"] == 1)

snap = tally_issues([
    issue(1, "### Which class interests you?\n\nVector (30)"),
    issue(2, "### Which class interests you?\n\nvector (30)"),
    issue(3, "### Which class interests you?\n\nCrown Signal (5, KingCode class)"),
    issue(4, "no template body at all"),
    issue(5, "### Which class interests you?\n\nOrigin (44)", state="closed"),
    issue(6, "### Which class interests you?\n\nPhantom (20)", label_names=["question"]),
])
check("count: case-insensitive Vector x2", snap["by_class"]["Vector"] == 2)
check("count: Crown Signal with parenthetical", snap["by_class"]["Crown Signal"] == 1)
check("count: missing class -> No preference", snap["by_class"]["No preference"] == 1)
check("count: closed issue excluded", snap["total"] == 4, f"total={snap['total']}")
check("count: non-waitlist label excluded (Phantom=0)", snap["by_class"]["Phantom"] == 0)

many = [issue(i, "### Which class interests you?\n\nNo preference") for i in range(1, 75)]
snap = tally_issues(many)
check("count: 74 -> gate closed", snap["gate"]["demand_gate_met"] is False and snap["total"] == 74)
snap = tally_issues([issue(i, "### Which class interests you?\n\nNo preference") for i in range(1, 76)])
check("count: 75 -> gate met flag true", snap["gate"]["demand_gate_met"] is True)
check("count: gate note says mint gate CLOSED", "CLOSED" in snap["gate"]["note"])

# issue list sorted + serializable
snap2 = tally_issues([issue(9, b), issue(3, b)])
check("count: issues sorted by number", [i["number"] for i in snap2["issues"]] == [3, 9])
import json as _json
_json.dumps(snap2)
check("count: snapshot JSON-serializable", True)

print()
if failures:
    print(f"{len(failures)} FAILURES: {failures}")
    sys.exit(1)
print("ALL TESTS PASSED")
