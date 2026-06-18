# healthtech-digest

A daily research agent that surfaces new developments in **healthcare technology
and AI** and posts a skimmable digest to Slack every morning.

It runs fully in the cloud on GitHub Actions — no laptop required. Each run uses
Claude with web search to research the last 7 days, deduplicates against what it
has already surfaced, and posts a themed digest to a Slack channel.

## What it produces

A single Slack message, sectioned by theme, one hyperlinked line per item:

```
*Healthcare Tech & AI Digest — June 18, 2026*

*Prior Auth / Payer Workflow*
• <https://www.anterior.com|Anterior> — $40M raised for AI prior-authorization and clinical review.

*Clinical AI Companies*
• <https://www.doctronic.ai|Doctronic> — AI-doctor startup; $40M Series B.

*Stanford Healthcare AI*
• <…|RAISE Health Symposium 2026> — Health AI Week recordings now posted.

*Interviews & Video*
• <…|OpenAI Podcast Ep. 14> — Dr. Nate Gross on AI for strained healthcare systems.

*Articles & News*
• <…|STAT — Who'll pay for AI in health care?> — FDA has cleared 1,357 AI devices, few reimbursed.
```

Sections with nothing new say *"No new items this run."* rather than padding.

## How it works

- **`digest.py`** — the research script. Drives a Claude (`claude-opus-4-8`) web-search
  pass over the last 7 days, parses the structured result, drops items already
  seen, formats Slack mrkdwn, and posts it.
- **`.github/workflows/daily-digest.yml`** — the daily cron trigger (8am Pacific)
  plus the step that commits updated dedup state back to the repo.
- **`state/seen.json`** — committed dedup state. Each run records the URLs it
  surfaced (with the date) so the same item is not repeated. Entries older than
  60 days are pruned automatically.

### Research tracks

The digest is organized into five themed sections, with prior auth / payer
workflow prioritized:

1. **Prior Auth / Payer Workflow** — funding, launches, policy, and analysis on
   prior authorization, claims, denials, peer-to-peer review, payer-side AI.
2. **Clinical AI Companies** — newly launched/funded/stealth-exiting health-tech
   startups (YC, a16z Bio+Health, Rock Health, General Catalyst, etc.).
3. **Stanford Healthcare AI** — Stanford HAI, Stanford Medicine, RAISE Health,
   and the Stanford Center for AI in Medicine & Imaging.
4. **Interviews & Video** — recent interviews, podcasts, panels, and talks.
5. **Articles & News** — STAT, MedCity News, Fierce Healthcare, Endpoints,
   Becker's Health IT, Nature Medicine, NEJM AI, MIT Tech Review, and others.

## Setup

### 1. Create a Slack incoming webhook

1. Go to <https://api.slack.com/apps> → **Create New App** → *From scratch*.
2. Enable **Incoming Webhooks**, then **Add New Webhook to Workspace** and pick
   the channel you want the digest posted to.
3. Copy the webhook URL (looks like `https://hooks.slack.com/services/T…/B…/…`).

### 2. Add repository secrets

In this repo: **Settings → Secrets and variables → Actions → New repository
secret**. Add both:

| Secret name         | Value                                            |
| ------------------- | ------------------------------------------------ |
| `ANTHROPIC_API_KEY` | Your Anthropic API key                           |
| `SLACK_WEBHOOK_URL` | The Slack incoming webhook URL from step 1       |

These are read from the environment at runtime — never commit them to the repo.

### 3. (Optional) Test it now

Trigger a run by hand from the **Actions** tab → *Daily Healthcare Tech Digest*
→ **Run workflow**. The digest should appear in your Slack channel within a
minute or two, and the run will commit an updated `state/seen.json`.

You can also run it locally:

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
python digest.py
```

## Schedule

The workflow runs daily on the cron in `daily-digest.yml`. GitHub Actions cron
is **UTC and does not observe daylight saving**, so:

- `0 15 * * *` → **8:00 AM PDT** (summer) / 7:00 AM PST (winter) — the default.
- `0 16 * * *` → 9:00 AM PDT / **8:00 AM PST** (winter).

Pick the line that matches the season you care about most, or adjust twice a
year. Scheduled runs can be delayed by a few minutes during periods of high
GitHub load.

## Tuning

- **Lookback window / memory** — `LOOKBACK_DAYS` (default 7) and `STATE_TTL_DAYS`
  (default 60) at the top of `digest.py`.
- **Sources, sections, filtering** — edit `SECTIONS` and `SYSTEM_PROMPT` in
  `digest.py`.
