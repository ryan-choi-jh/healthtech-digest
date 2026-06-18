# healthtech-digest

Workspace for a **Claude Code Routine** that posts a daily healthcare technology
& AI digest to Slack — cloud-hosted, runs on your Claude subscription, no laptop
required and no separate API key.

> This repo is just the workspace the Routine clones on each run. The research,
> formatting, and Slack delivery are driven entirely by the Routine's prompt
> (see below) — there's no code to run here.

## How it works

A scheduled Claude Code Routine runs every morning at 8am, researches the last 7
days of healthcare-tech and AI news with web search, and posts a themed digest
to a Slack channel via the Slack connector. Routines run on Anthropic-managed
cloud infrastructure and draw down your subscription usage like an interactive
session.

Docs: <https://code.claude.com/docs/en/routines>

## Output format

A single Slack message, sectioned by theme (prior auth first), one hyperlinked
line per item, with *"No new items this run."* under any empty section:

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

## Setup

### 1. Connect Slack (once)

- Go to **https://claude.ai/customize/connectors**
- Enable the **Slack** connector and authorize it for your workspace/channel
  (invite the Claude app to the channel if it's private)

### 2. Create the Routine

- Go to **https://claude.ai/code/routines** → **New routine**
- **Name:** `Healthcare Tech Daily Digest`
- **Prompt:** paste the brief from [`ROUTINE_PROMPT.md`](./ROUTINE_PROMPT.md); pick
  **Opus** in the model selector
- **Repositories:** select this repo (`healthtech-digest`) as the workspace
- **Environment:** leave **Default** (Trusted). If a test run can't reach some
  news sites, edit the environment → **Network access** → **Full**.

### 3. Schedule it

- **Select a trigger** → **Schedule** → **Daily** → **8:00 AM** in your timezone.
  Routines honor your wall-clock time and adjust for daylight saving, so 8am
  Pacific stays 8am year-round.

### 4. Connectors & test

- On the **Connectors** tab, confirm **Slack** is included; remove others
- Click **Create**, then **Run now** to fire a test. Open the run session to
  confirm it actually posted to Slack (a green status only means no infra error).

## Notes

- Runs on your Claude subscription usage (no API key, no pay-as-you-go billing).
  Check usage at <https://claude.ai/settings/usage>.
- The digest uses a 7-day rolling window. Routines don't persist dedup state
  across runs, so an item may occasionally repeat day-to-day.
- To tune sources, sections, or the schedule, edit the Routine's prompt and
  trigger at <https://claude.ai/code/routines> (keep
  [`ROUTINE_PROMPT.md`](./ROUTINE_PROMPT.md) in sync as the source of truth).
