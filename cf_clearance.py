"""Pass a Cloudflare challenge page with ZeroCaptcha, then fetch the page behind it through the same
proxy, with the cf_clearance cookie and the user agent it is bound to:

    export ZEROCAPTCHA_API=https://api.zerocaptcha.io ZEROCAPTCHA_KEY=zc_live_...
    export PROXY_URL=http://user:pass@proxy.example.net:8080
    python cf_clearance.py https://your-site.example/

It prints the clearance as JSON, then the HTTP status the page answered with. Standard library
only; Python 3.9 or later. Use it only on sites you own or are allowed to automate.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Dict, Tuple

from zerocaptcha_client import ZeroCaptcha, ZeroCaptchaError


def fetch_with_clearance(url: str, proxy: str, clearance: Dict[str, str], timeout: float = 30) -> Tuple[int, bytes]:
    """GETs the page through the proxy with the clearance: the cf_clearance cookie and exactly the
    user agent that earned it. Returns the status and the body, whatever the status."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": clearance["user_agent"],
            "Cookie": f"cf_clearance={clearance['cf_clearance']}",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def main(argv: list) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    proxy = os.environ.get("PROXY_URL")
    if not proxy:
        print("Set PROXY_URL: a challenge page is solved through your proxy.", file=sys.stderr)
        return 2
    try:
        clearance = ZeroCaptcha().solve_challenge(argv[1], proxy)
    except (ZeroCaptchaError, ValueError) as error:
        request = f" (request {error.request_id})" if getattr(error, "request_id", None) else ""
        print(f"{error}{request}", file=sys.stderr)
        return 1
    print(json.dumps(clearance))
    status, _body = fetch_with_clearance(argv[1], proxy, clearance)
    print(f"HTTP {status}")
    return 0 if status < 400 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
