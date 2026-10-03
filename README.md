<!-- zc:header (generated from the registry; edit repos/registry.json) -->
# Cloudflare WAF and 5-second challenge solver: get a cf_clearance cookie

[![CI](https://github.com/ZeroCaptcha/cloudflare-challenge-solver/actions/workflows/ci.yml/badge.svg)](https://github.com/ZeroCaptcha/cloudflare-challenge-solver/actions/workflows/ci.yml)

Cloudflare WAF and 5-second challenge solver: pass a Cloudflare "Just a moment..." or "Checking your browser" challenge page through your own proxy and get the cf_clearance cookie with the user agent it is bound to. A tested Python example with the standard library only, and a curl recipe.

[Website](https://zerocaptcha.io/cloudflare-challenge-solver) · [Docs](https://zerocaptcha.io/docs) · [Quickstart](https://zerocaptcha.io/docs/quickstart) · [API reference](https://zerocaptcha.io/docs/reference/api) · [Pricing](https://zerocaptcha.io/pricing)
<!-- /zc:header -->

## What it does

Some sites answer a first visit with a Cloudflare challenge page instead of the page itself. It goes by several names, all one thing to solve:

- **Cloudflare WAF challenge:** a WAF rule (custom, rate limiting or IP Access) whose action is Managed Challenge, Non-Interactive Challenge or Interactive Challenge. Bot Fight Mode and Under Attack mode show the same page.
- **"Just a moment..." or "Checking your browser":** the interstitial page itself, answered with HTTP 403 and the header `cf-mitigated: challenge`.
- **The 5-second challenge:** the old name for Cloudflare's JavaScript challenge, after the few seconds its page took. Today it is a Managed or Non-Interactive Challenge (`js_challenge`), which Cloudflare says typically takes less than five seconds.

A browser that passes it gets a `cf_clearance` cookie, and the site lets it through while the cookie is valid.

`cf_clearance.py` gets that cookie for you from the ZeroCaptcha API, through **your own proxy**, together with the user agent it is bound to, and then fetches the page with both, through the same proxy. It is written for sites you own or are allowed to automate, such as your own staging site behind Cloudflare's WAF, or a partner's feed you have permission to read.

- **Standard library only:** `urllib`, `json` and `uuid`. Python 3.9 or later.
- **One call:** `ZeroCaptcha().solve_challenge(url, proxy)` returns `{"cf_clearance": ..., "user_agent": ...}`.
- **Safe to retry:** every task has its own `Idempotency-Key`; 429, 502, 503 and 504 are retried after the wait the API asks for.

## Quickstart

1. Create an account on the ZeroCaptcha website, create an API key on the dashboard and add funds (crypto, from $10). A task is charged only when it succeeds.
2. Set the API's address, your key, and your proxy (`http` or `https`, with its port):

   ```sh
   export ZEROCAPTCHA_API=https://api.zerocaptcha.io
   export ZEROCAPTCHA_KEY=zc_live_...
   export PROXY_URL=http://user:pass@proxy.example.net:8080
   ```

3. Run it with the page behind the challenge:

   ```sh
   python cf_clearance.py https://your-site.example/
   ```

   It prints the clearance as JSON, then the status the page answered with through your proxy.

## Use it in your code

```python
import os

from cf_clearance import fetch_with_clearance
from zerocaptcha_client import ZeroCaptcha

proxy = os.environ["PROXY_URL"]
clearance = ZeroCaptcha().solve_challenge("https://your-site.example/", proxy)
status, body = fetch_with_clearance("https://your-site.example/prices", proxy, clearance)
```

## With curl

Any client works, as long as it sends the cookie with exactly that user agent, through the same proxy:

```sh
curl --proxy "$PROXY_URL" \
  --user-agent "$USER_AGENT" \
  --cookie "cf_clearance=$CF_CLEARANCE" \
  https://your-site.example/
```

## How it works

1. `POST /v1/tasks` with `{"type": "CloudflareChallengeTask", "websiteURL": ..., "proxy": ...}` and an `Idempotency-Key` header, so a retry never makes a second task. Add `"callbackUrl"` to have the result POSTed to you when the task ends ([Polling and callbacks](https://zerocaptcha.io/docs/callbacks)). The task's price is held on your balance.
2. ZeroCaptcha opens the page through your proxy, passes the challenge, and keeps the cookie Cloudflare sets.
3. `GET /v1/tasks/{id}` every 2 seconds until the task has `succeeded`: `solution.cookie.value` is the `cf_clearance` cookie and `solution.userAgent` is the user agent it was earned with. The held price is charged. A task that fails or expires costs nothing.

The [challenge pages docs](https://zerocaptcha.io/docs/challenges) have every field, and the [cf_clearance guide](https://zerocaptcha.io/guides/cf-clearance-cookie-explained) explains the cookie itself.

## Honest limits

- **Your proxy is required.** Cloudflare accepts a clearance only from the IP address that earned it, so there is no proxyless challenge task: `CloudflareChallengeTaskProxyless` is refused and nothing is held.
- **Same user agent, exactly.** Send `solution.userAgent` as your `User-Agent` on every request that carries the cookie.
- **It lasts as long as the site allows:** the site's Challenge Passage setting, 30 minutes by default. The API serves the clearance for 30 minutes after it is issued.
- **TLS fingerprints matter on some sites.** Cloudflare can compare your client's TLS handshake with the browser its user agent names, and Python's `urllib` does not look like Chrome. If a site challenges you again despite a valid cookie, use a client that impersonates Chrome's handshake (such as curl-impersonate) or a real browser: see the [Playwright](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver-playwright), [Puppeteer](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver-puppeteer) and [Selenium](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver-selenium) examples.
- **A Cloudflare block is not a challenge.** Error 1020 (access denied by a firewall rule) and 1015 (rate limited) are refusals, not challenges; see [error 1020](https://zerocaptcha.io/blog/cloudflare-error-1020) and [error 1015](https://zerocaptcha.io/blog/cloudflare-error-1015).
- **Only for sites you own or are allowed to automate.** The [Acceptable Use Policy](https://zerocaptcha.io/legal/acceptable-use) applies to every task, and any site owner can [opt out](https://zerocaptcha.io/opt-out).

## FAQ

**How is this different from a Cloudflare Turnstile token?**
Cloudflare Turnstile is a widget inside a page's form, and its token goes in the form. A challenge page stands in front of the whole site, and its result is a cookie. The [challenge vs Cloudflare Turnstile guide](https://zerocaptcha.io/guides/cloudflare-challenge-vs-turnstile) compares them, and the [Cloudflare Turnstile solver](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver) covers widgets.

**What does "Please unblock challenges.cloudflare.com to proceed" mean?**
The challenge's own script could not load, often because of an ad blocker or a network filter. The [article on that message](https://zerocaptcha.io/blog/please-unblock-challenges-cloudflare-com) covers the fixes for people and for automation.

**Which challenge types does it pass?**
The managed, JS and interactive challenges a Cloudflare WAF rule shows; the [challenge types article](https://zerocaptcha.io/blog/cloudflare-challenge-types) explains each.

**Is this the Cloudflare 5-second challenge?**
Yes, under its current names. The 5-second challenge was the JavaScript challenge page; today a WAF rule shows a Managed or Non-Interactive Challenge in its place. The [5-second challenge article](https://zerocaptcha.io/blog/cloudflare-5-second-challenge) has the history and the request.

**What does it cost?**
The [pricing page](https://zerocaptcha.io/pricing) lists the challenge-page price per 1,000 solved tasks. Only a task that succeeds is charged.

**Can I use the createTask format?**
Yes: `CloudflareChallengeTask` (or `AntiCloudflareTask`) works with `createTask`, and the ready reply carries `solution.cookies.cf_clearance` and `solution.userAgent`. See [createtask-api-migration](https://github.com/ZeroCaptcha/createtask-api-migration).

## Run the tests

```sh
python -m unittest discover -s tests -v
```

The tests run against stand-ins on your machine: an API, and a proxy that answers for a site behind a Cloudflare challenge. No key, no real task, nothing spent.

<!-- zc:footer (generated from the registry) -->
## More from ZeroCaptcha

- The website: [ZeroCaptcha](https://zerocaptcha.io), the [docs](https://zerocaptcha.io/docs), the [guides](https://zerocaptcha.io/guides), the [blog](https://zerocaptcha.io/blog) and the [status page](https://zerocaptcha.io/status)
- Start here: [zerocaptcha](https://github.com/ZeroCaptcha/zerocaptcha), [cloudflare-turnstile-solver](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver), **cloudflare-challenge-solver**
- Examples by language: [cloudflare-turnstile-solver-python](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver-python), [cloudflare-turnstile-solver-nodejs](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver-nodejs), [cloudflare-turnstile-solver-go](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver-go), [cloudflare-turnstile-solver-php](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver-php), [cloudflare-turnstile-solver-java](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver-java), [cloudflare-turnstile-solver-csharp](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver-csharp), [cloudflare-turnstile-solver-rust](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver-rust)
- Browser automation: [cloudflare-turnstile-solver-playwright](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver-playwright), [cloudflare-turnstile-solver-puppeteer](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver-puppeteer), [cloudflare-turnstile-solver-selenium](https://github.com/ZeroCaptcha/cloudflare-turnstile-solver-selenium)
- SDKs, MCP server and migration: [zerocaptcha-js](https://github.com/ZeroCaptcha/zerocaptcha-js), [zerocaptcha-python](https://github.com/ZeroCaptcha/zerocaptcha-python), [zerocaptcha-go](https://github.com/ZeroCaptcha/zerocaptcha-go), [zerocaptcha-mcp](https://github.com/ZeroCaptcha/zerocaptcha-mcp), [createtask-api-migration](https://github.com/ZeroCaptcha/createtask-api-migration)
- Lists: [awesome-cloudflare-turnstile](https://github.com/ZeroCaptcha/awesome-cloudflare-turnstile)

## Licence

MIT: see [LICENSE](LICENSE).

## Disclaimer

ZeroCaptcha is an independent service, not affiliated with or endorsed by Cloudflare. Cloudflare and Turnstile are trademarks of Cloudflare, Inc. Use ZeroCaptcha only on sites you own or are allowed to automate, as the [Acceptable Use Policy](https://zerocaptcha.io/legal/acceptable-use) says; any site owner can [opt out](https://zerocaptcha.io/opt-out).
<!-- /zc:footer -->
