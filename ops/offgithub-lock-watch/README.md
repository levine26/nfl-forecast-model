# Sunday Signal external lock scheduler — deployment kit

**Status: NOT DEPLOYED.** The repo contains a ready-to-review external Cloudflare Worker implementation, but it cannot run independently until an external operator provisions the Worker and credentials. It creates no Cloudflare account or external spending on its own.

The Worker uses an independent five-minute Cloudflare clock. On each successful tick it retrieves the latest canonical forecast CSV and immutable lock ledger from main through the GitHub Contents API. Kickoff time is interpreted in America/New_York (DST-aware). It dispatches the existing pregame workflow roughly 100–90 minutes before kickoff and the existing guarded fast official lock worker near the official T-minus-60 target. Legacy receipts and earlier targets remain T-minus-120; Week 6 of 2026 onward uses T-minus-60.

## Required external setup

1. Provision a Cloudflare Worker and KV namespace. Add a binding named LOCK_WATCH_STATE to the Worker. Review external platform costs before deploying.
2. Configure GITHUB_DISPATCH_TOKEN only as a Cloudflare secret. Use a fine-grained GitHub token restricted to levine26/nfl-forecast-model, with repository contents read and Actions dispatch write. Never commit the token.
3. Configure ALERT_WEBHOOK_URL as an independent Slack- or Discord-compatible webhook secret and HEALTH_TOKEN as another random secret. Neither belongs in the GitHub repository or public Pages.
4. Deploy the Worker using the supplied wrangler.toml once all bindings and secrets are configured. Run the Node regression tests and an isolated dispatch test before giving the Worker a production token.
5. Configure a second independent external uptime monitor to poll the Worker health endpoint at least every five minutes, including an Authorization: Bearer HEALTH_TOKEN header. Alert on 503, failed requests, or stale last-success timestamps. A Worker cannot detect its own missing cron execution without that independent monitor.
6. Validate two different real games. Capture the Cloudflare execution time, GitHub workflow dispatch response, actual workflow run start and completion, immutable official lock SHA, and timing versus the applicable target. The returned GitHub HTTP 204 only means a dispatch was accepted, not that the official lock occurred on time.

## Operational safeguards and limits

- Missing GitHub token, webhook or KV state: fail closed.
- GitHub API error: fail and attempt an independent webhook alert; health does not report success.
- No official lock by T-minus-50: post an independent alert; KV deduplicates that alert per game.
- KV is not a prediction ledger; duplicate dispatches remain safe only because the existing canonical lock writer is idempotent and validates frozen F-ST, freshness, cutoff and append-only history.
- All forecast, market, Read and historical prediction data remain read-only inside this Worker. It cannot grade, publish, backdate, promote research candidates, or approve HUMAN editorial claims.
- GitHub Actions availability, GitHub API availability and external hosting outages remain real failure modes. No hard SLA is established until external deployment, monitoring and real-game receipts are validated.
- The existing GitHub cron and 10-minute rescue must remain enabled as redundant scheduling paths.

Tracking issue: https://github.com/levine26/nfl-forecast-model/issues/701
