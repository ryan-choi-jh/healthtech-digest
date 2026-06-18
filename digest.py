#!/usr/bin/env python3
"""Daily Healthcare Tech & AI research digest.

Runs a Claude-powered research pass (web search over the last 7 days),
deduplicates against state committed from prior runs, formats a Slack
message, and posts it to an incoming webhook.

Designed to run headless from GitHub Actions on a daily cron. See README.md.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request

import anthropic

# --- Configuration ----------------------------------------------------------

MODEL = "claude-opus-4-8"

# How far back the digest looks, and how long a surfaced item is remembered so
# it is not repeated on later runs.
LOOKBACK_DAYS = 7
STATE_TTL_DAYS = 60

STATE_PATH = os.path.join(os.path.dirname(__file__), "state", "seen.json")

# Section themes, in the order they appear in the digest. The research prompt
# is told to slot items into exactly these sections.
SECTIONS = [
    "Prior Auth / Payer Workflow",
    "Clinical AI Companies",
    "Stanford Healthcare AI",
    "Interviews & Video",
    "Articles & News",
]

# The research brief the agent executes on each run.
SYSTEM_PROMPT = f"""\
You are a research agent producing a daily digest of new developments in \
healthcare technology and AI for an early-stage investor whose thesis centers \
on prior authorization and payer/clinical workflow.

On each run, search the web for items published within the last {LOOKBACK_DAYS} \
days and organize them into these sections (use these exact titles):

1. "Prior Auth / Payer Workflow" — funding, launches, policy, and analysis on \
prior authorization, claims, denials, peer-to-peer review, and payer-side AI. \
This is the priority track; surface anything relevant here even if thin.
2. "Clinical AI Companies" — newly launched, newly funded, or stealth-exiting \
health-tech startups (ambient documentation, AI clinicians, coding, referrals, \
life-sciences tooling, etc.). Include notable YC / a16z Bio+Health / Rock Health \
/ General Catalyst announcements.
3. "Stanford Healthcare AI" — new releases from Stanford HAI, Stanford Medicine, \
RAISE Health, and the Stanford Center for AI in Medicine & Imaging (talks, \
papers, symposia, recordings).
4. "Interviews & Video" — interviews, podcasts, panels, and talks on AI/tech in \
healthcare posted recently (YouTube, Spotify, Apple, etc.).
5. "Articles & News" — notable journalism and analysis from credible outlets \
(STAT, MedCity News, Fierce Healthcare, Endpoints, Becker's Health IT, Nature \
Medicine, NEJM AI, MIT Tech Review, TechCrunch health).

Rules:
- Only include items genuinely published in the last {LOOKBACK_DAYS} days. Parse \
and trust the real publication date, not search ranking.
- Prioritize primary sources (company sites, the Stanford channel itself, the \
actual paper/announcement) over aggregators.
- For a company, the link should be the company's own website when you can \
verify it; otherwise link the most authoritative source (YC profile, the \
article that reported it). Do not invent URLs — only use links you actually \
retrieved.
- Drop marketing fluff, listicles, and SEO spam.
- Keep each summary to a single tight clause/sentence.
- If a section has nothing new and credible, return it with an empty item list.

When you are done researching, output ONLY a JSON object (in a ```json code \
fence) with this exact shape and nothing else after it:

{{
  "date": "Month D, YYYY",
  "sections": [
    {{
      "title": "<one of the section titles above>",
      "items": [
        {{"name": "<company or title>", "url": "<https link>", "summary": "<one line>"}}
      ]
    }}
  ]
}}

Include all five sections in order, even when their item list is empty."""

USER_PROMPT = (
    "Run the daily healthcare tech & AI research pass for today and return the "
    "JSON digest."
)


# --- State (dedup) ----------------------------------------------------------


def load_state() -> dict:
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def prune_state(state: dict, today: dt.date) -> dict:
    cutoff = today - dt.timedelta(days=STATE_TTL_DAYS)
    kept = {}
    for url, first_seen in state.items():
        try:
            seen_date = dt.date.fromisoformat(first_seen)
        except (TypeError, ValueError):
            continue
        if seen_date >= cutoff:
            kept[url] = first_seen
    return kept


def normalize_url(url: str) -> str:
    """Normalize a URL so trivial variants dedupe to the same key."""
    url = url.strip()
    url = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
    url = re.sub(r"^www\.", "", url, flags=re.IGNORECASE)
    return url.rstrip("/").lower()


# --- Research ---------------------------------------------------------------


def run_research(client: anthropic.Anthropic) -> str:
    """Drive the web-search agentic loop and return the final text."""
    tools = [{"type": "web_search_20260209", "name": "web_search"}]
    messages = [{"role": "user", "content": USER_PROMPT}]

    final = None
    for _ in range(8):  # cap continuations
        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            tools=tools,
            messages=messages,
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("Model refused the research request.")
        if response.stop_reason == "pause_turn":
            # Server-side tool loop hit its iteration limit; resume.
            messages.append({"role": "assistant", "content": response.content})
            continue
        final = response
        break

    if final is None:
        raise RuntimeError("Research did not complete within the continuation cap.")

    return "".join(b.text for b in final.content if b.type == "text")


def extract_json(text: str) -> dict:
    """Pull the JSON object out of the model's final message."""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    blob = fence.group(1) if fence else None
    if blob is None:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON object found in model output.")
        blob = text[start : end + 1]
    return json.loads(blob)


# --- Formatting & delivery --------------------------------------------------


def slack_escape(text: str) -> str:
    """Escape the three characters Slack treats specially in mrkdwn."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_digest(digest: dict, state: dict, today: dt.date) -> tuple[str, list[str]]:
    """Return (slack_message, list_of_new_urls), filtering already-seen items."""
    date_label = digest.get("date") or today.strftime("%B %-d, %Y")
    by_title = {s.get("title"): s.get("items", []) for s in digest.get("sections", [])}

    lines = [f"*Healthcare Tech & AI Digest — {slack_escape(date_label)}*"]
    new_urls: list[str] = []
    total_new = 0

    for title in SECTIONS:
        lines.append("")  # blank line between sections
        lines.append(f"*{slack_escape(title)}*")

        fresh = []
        for item in by_title.get(title, []) or []:
            url = (item.get("url") or "").strip()
            name = (item.get("name") or "").strip()
            summary = (item.get("summary") or "").strip()
            if not url or not name:
                continue
            if normalize_url(url) in state:
                continue
            fresh.append((name, url, summary))
            new_urls.append(url)

        if not fresh:
            lines.append("• _No new items this run._")
            continue

        for name, url, summary in fresh:
            total_new += 1
            link = f"<{url}|{slack_escape(name)}>"
            if summary:
                lines.append(f"• {link} — {slack_escape(summary)}")
            else:
                lines.append(f"• {link}")

    if total_new == 0:
        lines.append("")
        lines.append("_Nothing new across all tracks today._")

    return "\n".join(lines), new_urls


def post_to_slack(webhook_url: str, message: str) -> None:
    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", "replace")
        if resp.status != 200 or body.strip() != "ok":
            raise RuntimeError(f"Slack returned {resp.status}: {body!r}")


# --- Entry point ------------------------------------------------------------


def main() -> int:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("ERROR: SLACK_WEBHOOK_URL is not set.", file=sys.stderr)
        return 1
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        return 1

    today = dt.date.today()
    client = anthropic.Anthropic()

    raw = run_research(client)
    digest = extract_json(raw)

    state = load_state()
    message, new_urls = build_digest(digest, state, today)

    post_to_slack(webhook_url, message)
    print("Posted digest to Slack.")

    stamp = today.isoformat()
    for url in new_urls:
        state[normalize_url(url)] = stamp
    state = prune_state(state, today)
    save_state(state)
    print(f"Recorded {len(new_urls)} new item(s); state now tracks {len(state)}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
