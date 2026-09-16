# The Logo Protocol: Founding Signal — Waitlist

Public waitlist + demand engine for the 99-pass utility-first membership pilot.

**Live page:** https://cumulativewebinc.github.io/cwi-nft-waitlist/

## The mint gate (hard rule)

There is **no mint date**. There will not be one until **75 qualified waitlist
members** are recorded, plus the four other gates (utility calendar, rights,
technology, control). This repository exists to measure demand, not to sell.

## How demand is counted

- Every signup is a public GitHub issue with the `waitlist` label, opened via
  the **Waitlist signup** issue template.
- The demand engine (`.github/workflows/demand.yml`, hourly + on every issue
  event, $0 on GitHub Actions) runs `scripts/count_waitlist.py`, which counts
  **open** issues labeled `waitlist`, breaks them down by the template's class
  field, and commits `data/demand.json`.
- The page renders that JSON live. Zero is a number — honest counts only.

## Layout

- `index.html` — thesis, four classes, utility calendar, mint gate, live demand, FAQ
- `data/demand.json` — public demand snapshot (machine-readable)
- `.github/ISSUE_TEMPLATE/waitlist-signup.yml` — the signup form
- `scripts/count_waitlist.py` + `tests/run_tests.py` — engine + validation

Brand rules: the CWI logo is page branding; the crown specimen appears only in
its own Crown Signal class card (the crown motif is KingCode's).
