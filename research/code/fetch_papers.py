"""
fetch_papers.py — download research-paper PDFs into research/papers/<family>/.

Naming (per research/papers/README.md): <firstauthor>_<year>_<shorttitle>.pdf
Folder: research/papers/<family>/  where family = idea_id prefix, lowercased
        (BRK-001 -> brk, IV-001 -> iv).

Source handling:
  - arxiv  : abstract URL -> /pdf/<id>  (reliable, direct).
  - ssrn   : abstract page gates the PDF behind Delivery.cfm + login/captcha.
             We attempt a polite fetch; if it returns HTML instead of a PDF
             (the usual bot-block), we SKIP and print the manual-download URL.

Idempotent: a paper whose target file already exists is skipped.
PDFs are gitignored — this only ever writes local files. No DB writes.

Usage:
    python research/code/fetch_papers.py            # fetch the default manifest
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[2]
PAPERS_DIR = REPO / "research" / "papers"

# Browser-ish headers — SSRN/journals 403 a bare python-requests UA.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
}

# Manifest: one row per paper we want on disk.
#   family   -> subfolder
#   filename -> firstauthor_year_shorttitle.pdf
#   source   -> 'arxiv' | 'ssrn'
#   url      -> abstract/landing URL (PDF URL is derived per source)
MANIFEST = [
    dict(family="brk", source="arxiv",
         url="https://arxiv.org/abs/2511.08571",
         filename="singha_2025_forecast_to_fill_gold.pdf"),
    dict(family="brk", source="ssrn",
         url="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3662052",
         filename="caporale_2021_gold_oil_abnormal_returns.pdf"),
    dict(family="brk", source="ssrn",
         url="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3953845",
         filename="han_2022_commodity_trend_factor.pdf"),
    dict(family="iv", source="ssrn",
         url="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=485402",
         filename="neely_2004_gold_implied_vol.pdf"),
]


def _arxiv_pdf_url(abstract_url: str) -> str:
    """https://arxiv.org/abs/<id>  ->  https://arxiv.org/pdf/<id>"""
    arxiv_id = abstract_url.rstrip("/").split("/abs/")[-1]
    return f"https://arxiv.org/pdf/{arxiv_id}"


def _looks_like_pdf(content: bytes, ctype: str) -> bool:
    return content[:5] == b"%PDF-" or "application/pdf" in ctype.lower()


def fetch(item: dict) -> str:
    """Return one of: 'saved', 'skipped-exists', 'blocked', 'error'."""
    dest_dir = PAPERS_DIR / item["family"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / item["filename"]

    label = f"{item['family']}/{item['filename']}"
    if dest.exists():
        print(f"  [skip] already on disk: {label}")
        return "skipped-exists"

    if item["source"] == "arxiv":
        pdf_url = _arxiv_pdf_url(item["url"])
    else:  # ssrn / journal — try the abstract URL directly; usually gated
        pdf_url = item["url"]

    try:
        r = requests.get(pdf_url, headers=HEADERS, timeout=30, allow_redirects=True)
    except requests.RequestException as e:
        print(f"  [error] {label}: {e}")
        return "error"

    ctype = r.headers.get("Content-Type", "")
    if r.status_code == 200 and _looks_like_pdf(r.content, ctype):
        dest.write_bytes(r.content)
        kb = len(r.content) // 1024
        print(f"  [saved] {label}  ({kb} KB)")
        return "saved"

    # Not a PDF — almost always SSRN's bot wall returning HTML.
    print(f"  [blocked] {label}  (HTTP {r.status_code}, {ctype or 'no content-type'})")
    print(f"            manual download -> {item['url']}")
    print(f"            save as          -> {dest}")
    return "blocked"


def main() -> int:
    print(f"Fetching {len(MANIFEST)} paper(s) into {PAPERS_DIR}\n")
    tally: dict[str, int] = {}
    for item in MANIFEST:
        status = fetch(item)
        tally[status] = tally.get(status, 0) + 1

    print("\n--- summary ---")
    for k in ("saved", "skipped-exists", "blocked", "error"):
        if tally.get(k):
            print(f"  {k:14} {tally[k]}")

    if tally.get("blocked"):
        print("\nBlocked = SSRN bot wall. Open each URL in a logged-in browser,")
        print("download the PDF, and save it to the path printed above (exact name).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
