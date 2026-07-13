"""Fetch recent items from configured adtech sources.

Deterministic retrieval only — no model calls here. Each source is fetched
independently so one failure (timeout, paywall, 404) never breaks the run;
failures are collected and surfaced in the brief as "unavailable this week".
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import feedparser
import requests

RECENT_DAYS = 7
HTTP_TIMEOUT = 20
USER_AGENT = "adtech-intel-agent/0.1 (+personal research)"


@dataclass
class Item:
    source: str
    title: str
    url: str
    published: dt.datetime | None
    summary: str = ""


@dataclass
class FetchResult:
    items: list[Item] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # "SourceName: reason"


def _within_window(published: dt.datetime | None, days: int) -> bool:
    if published is None:
        return True  # keep undated items; let synthesis decide relevance
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    return published >= cutoff


def _parse_struct_time(entry) -> dt.datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return dt.datetime(*t[:6], tzinfo=dt.timezone.utc)
    return None


def _fetch_rss(source: dict) -> list[Item]:
    feed = feedparser.parse(source["url"])
    items: list[Item] = []
    for e in feed.entries:
        published = _parse_struct_time(e)
        if not _within_window(published, RECENT_DAYS):
            continue
        items.append(
            Item(
                source=source["name"],
                title=e.get("title", "(untitled)"),
                url=e.get("link", source["url"]),
                published=published,
                summary=e.get("summary", "")[:1000],
            )
        )
    return items


def _fetch_html(source: dict) -> list[Item]:
    # Minimal placeholder so synthesis has *something* to work with.
    # TODO: replace with real per-site extraction (article links + dates),
    # e.g. via selectolax/BeautifulSoup targeting the site's headline markup.
    resp = requests.get(
        source["url"], timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}
    )
    resp.raise_for_status()
    return [
        Item(
            source=source["name"],
            title=f"{source['name']} — homepage snapshot",
            url=source["url"],
            published=None,
            summary=resp.text[:4000],
        )
    ]


def fetch_all(sources: list[dict]) -> FetchResult:
    result = FetchResult()
    for source in sources:
        try:
            if source.get("type") == "rss":
                result.items.extend(_fetch_rss(source))
            else:
                result.items.extend(_fetch_html(source))
        except Exception as exc:  # graceful degradation (PRD P0)
            result.errors.append(f"{source['name']}: {exc}")
    return result
