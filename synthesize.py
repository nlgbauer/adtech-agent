"""Turn fetched items into a synthesized market brief via Claude.

This is the one step that needs model judgment: clustering items into themes,
deciding what is notable, and writing the strategic implication lines. The
prompt enforces the PRD's output shape and caps (<=5 themes, <=12 moves) so the
brief stays a sub-5-minute read.
"""
from __future__ import annotations

import datetime as dt

from anthropic import Anthropic

MODEL = "claude-sonnet-5"  # configurable — see docs.claude.com for current models
MAX_TOKENS = 4000

SYSTEM = """You are a market-intelligence analyst covering the adtech industry.
You write for an operator who makes product, positioning, and partnership
decisions. For every notable move, give the strategic implication — why it
matters — not just the fact. Be concise and skeptical; omit filler. Never
invent items, companies, or links: use only what is provided."""

BRIEF_INSTRUCTIONS = """Write a weekly adtech market brief in markdown with these sections:

# Adtech Market Brief — Week of {date}

## TL;DR — themes shaping the market this week
3-5 bullets. Throughlines across items, not individual headlines.

## Notable moves
Group by type where relevant (Launches / M&A / Funding / Exec changes / Regulatory).
Each item: one-line factual summary + source link + **Implication:** one line.

## Players in the news
A short comma-separated index of companies that appeared.

## Watch items
Slow-burn shifts trending toward a decision, if any.

Hard limits: at most 5 themes and 12 moves; keep the whole brief under a
5-minute read. If any sources failed to fetch, add a final one-line section
"## Sources unavailable this week" listing them."""


def _format_items(items) -> str:
    if not items:
        return "(no items retrieved)"
    lines = []
    for it in items:
        when = it.published.date().isoformat() if it.published else "undated"
        lines.append(f"- [{it.source} | {when}] {it.title}\n  {it.url}\n  {it.summary}")
    return "\n".join(lines)


def synthesize(items, errors) -> str:
    client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    today = dt.date.today().isoformat()
    unavailable = "\n".join(f"- {e}" for e in errors) or "(none)"
    user_content = (
        BRIEF_INSTRUCTIONS.format(date=today)
        + "\n\n## Retrieved items\n"
        + _format_items(items)
        + "\n\n## Sources that failed to fetch\n"
        + unavailable
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")
