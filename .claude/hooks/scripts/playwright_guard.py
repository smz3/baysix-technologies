#!/usr/bin/env python3
"""
Playwright MCP URL guard.

Fires on PreToolUse for mcp__playwright__browser_navigate.
- Blocks navigation to any domain not in APPROVED_DOMAINS
- Logs every attempt (ALLOW / BLOCK) to .claude/logs/playwright_audit.log

To add a new domain: append it to APPROVED_DOMAINS below.
"""
import json
import sys
import os
from urllib.parse import urlparse
from datetime import datetime

APPROVED_DOMAINS = {
    # Sigma apps — deployed
    "syafiqmzin-sigma-quant.pages.dev",
    # Sigma apps — local dev (covers all ports: 3000 Next.js, 7070 Kronos, 8080 sigma-research)
    "localhost",
    "127.0.0.1",
    # Crypto market data
    "tradingview.com",
    "coinmarketcap.com",
    "coinglass.com",
    "binance.com",
    # Macro / sentiment
    "alternative.me",
    "forexfactory.com",
    "investing.com",
    "federalreserve.gov",
    "fred.stlouisfed.org",
    # APAC exchanges & central banks
    "bursamalaysia.com",
    "sgx.com",
    "bnm.gov.my",
    "mas.gov.sg",
    "bi.go.id",
}


def _log_path() -> str:
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    log_dir = os.path.join(project_dir, ".claude", "logs")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "playwright_audit.log")


def _is_approved(url: str) -> bool:
    try:
        hostname = urlparse(url).hostname or ""
        domain = hostname.removeprefix("www.")
        # Exact match covers IPs (localhost, 127.0.0.1) and precise domains
        # Suffix match covers subdomains (e.g. api.tradingview.com)
        return any(
            domain == approved or domain.endswith("." + approved)
            for approved in APPROVED_DOMAINS
        )
    except Exception:
        return False


def _log(url: str, verdict: str, reason: str = "") -> None:
    try:
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"[{ts}] {verdict:5s}  {url}"
        if reason:
            line += f"  # {reason}"
        with open(_log_path(), "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass  # never crash on a logging failure


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    url = (data.get("tool_input") or {}).get("url", "")
    if not url:
        sys.exit(0)

    if _is_approved(url):
        _log(url, "ALLOW")
        sys.exit(0)
    else:
        _log(url, "BLOCK", "domain not in allowlist")
        print(json.dumps({
            "decision": "block",
            "reason": (
                f"[playwright_guard] Domain not in approved allowlist: {url}\n"
                "To allow it, add the domain to APPROVED_DOMAINS in "
                ".claude/hooks/scripts/playwright_guard.py"
            ),
        }))
        sys.exit(2)


if __name__ == "__main__":
    main()
