"""The challenge flow against stand-ins for the API and for a site behind a Cloudflare challenge,
reached through a stand-in proxy: no key, no real task, nothing spent."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from cf_clearance import fetch_with_clearance
from stand_ins import CHALLENGED_SITE, CLEARANCE, KEY, USER_AGENT, StandInApi, StandInChallengeProxy
from zerocaptcha_client import ZeroCaptcha, ZeroCaptchaError


class ChallengeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.api = StandInApi()
        self.proxy = StandInChallengeProxy()
        self.client = ZeroCaptcha(self.api.url, KEY, interval=0.01)

    def tearDown(self) -> None:
        self.api.close()
        self.proxy.close()

    def test_the_task_goes_through_your_proxy(self) -> None:
        clearance = self.client.solve_challenge(CHALLENGED_SITE, self.proxy.url)
        self.assertEqual(clearance, {"cf_clearance": CLEARANCE, "user_agent": USER_AGENT})
        create = self.api.requests[0]
        self.assertEqual(
            create["body"],
            {"type": "CloudflareChallengeTask", "websiteURL": CHALLENGED_SITE, "proxy": self.proxy.url},
        )

    def test_the_clearance_opens_the_page_through_the_same_proxy(self) -> None:
        clearance = self.client.solve_challenge(CHALLENGED_SITE, self.proxy.url)
        status, body = fetch_with_clearance(CHALLENGED_SITE, self.proxy.url, clearance)
        self.assertEqual(status, 200)
        self.assertIn(b"Welcome", body)
        seen = self.proxy.seen[-1]
        self.assertEqual(seen["url"], CHALLENGED_SITE)  # the whole URL: it came through the proxy
        self.assertEqual(seen["cookies"]["cf_clearance"], CLEARANCE)
        self.assertEqual(seen["user_agent"], USER_AGENT)

    def test_another_user_agent_meets_the_challenge_again(self) -> None:
        clearance = {"cf_clearance": CLEARANCE, "user_agent": "python-urllib/3"}
        status, body = fetch_with_clearance(CHALLENGED_SITE, self.proxy.url, clearance)
        self.assertEqual(status, 403)
        self.assertIn(b"Just a moment", body)

    def test_a_wrong_key_is_refused(self) -> None:
        with self.assertRaises(ZeroCaptchaError) as raised:
            ZeroCaptcha(self.api.url, "zc_live_wrong", interval=0.01).solve_challenge(CHALLENGED_SITE, self.proxy.url)
        self.assertEqual(raised.exception.code, "unauthorized")

    def test_the_command_prints_the_clearance_and_the_status(self) -> None:
        script = Path(__file__).resolve().parent.parent / "cf_clearance.py"
        run = subprocess.run(
            [sys.executable, str(script), CHALLENGED_SITE],
            env={**os.environ, "ZEROCAPTCHA_API": self.api.url, "ZEROCAPTCHA_KEY": KEY, "PROXY_URL": self.proxy.url},
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        first, second = run.stdout.strip().splitlines()
        self.assertEqual(json.loads(first), {"cf_clearance": CLEARANCE, "user_agent": USER_AGENT})
        self.assertEqual(second, "HTTP 200")


if __name__ == "__main__":
    unittest.main()
