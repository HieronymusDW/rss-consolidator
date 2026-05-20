#!/usr/bin/env python3
"""
RSS Feed Consolidator
Fetches multiple RSS feeds, merges and deduplicates entries, outputs a single RSS feed.
"""

import feedparser
import json
import os
from datetime import datetime, timezone
from feedgen.feed import FeedGenerator
from urllib.parse import urlparse

# Load feed URLs from config file
with open("feeds.json") as f:
    FEEDS = json.load(f)

OUTPUT_FILE = "docs/feed.xml"


def fetch_entries(feed_url):
    """Fetch and parse a single RSS feed, return list of entries."""
    try:
        parsed = feedparser.parse(feed_url)
        entries = []
        for entry in parsed.entries:
            # Normalize the entry into a consistent dict
            link = entry.get("link", "")
            title = entry.get("title", "").strip()

            if not link or not title:
                continue

            # Parse published date, fall back to now if missing
            published = None
            for date_field in ("published_parsed", "updated_parsed"):
                if entry.get(date_field):
                    published = datetime(*entry[date_field][:6], tzinfo=timezone.utc)
                    break
            if published is None:
                published = datetime.now(timezone.utc)

            # Get summary/description
            summary = ""
            if entry.get("summary"):
                summary = entry.summary
            elif entry.get("description"):
                summary = entry.description

            entries.append({
                "title": title,
                "link": link,
                "published": published,
                "summary": summary,
                "source": parsed.feed.get("title", urlparse(feed_url).netloc),
            })

        print(f"  OK  {feed_url} — {len(entries)} entries")
        return entries

    except Exception as e:
        print(f"  FAIL {feed_url} — {e}")
        return []


def deduplicate(entries):
    """Remove duplicate entries by normalized URL."""
    seen = set()
    unique = []
    for entry in entries:
        # Normalize URL: strip trailing slash and common tracking params
        url = entry["link"].split("?")[0].rstrip("/").lower()
        if url not in seen:
            seen.add(url)
            unique.append(entry)
    return unique


def generate_feed(entries):
    """Generate RSS feed XML from a list of entries."""
    fg = FeedGenerator()
    fg.id("https://your-username.github.io/rss-consolidator/feed.xml")
    fg.title("Geopolitics Digest")
    fg.link(href="https://your-username.github.io/rss-consolidator/feed.xml", rel="self")
    fg.description("Consolidated geopolitics RSS feed")
    fg.language("en")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for entry in entries:
        fe = fg.add_entry()
        fe.id(entry["link"])
        fe.title(f"[{entry['source']}] {entry['title']}")
        fe.link(href=entry["link"])
        fe.published(entry["published"])
        fe.description(entry["summary"] or entry["title"])

    os.makedirs("docs", exist_ok=True)
    fg.rss_str(pretty=True)
    fg.rss_file(OUTPUT_FILE)
    print(f"\nWrote {len(entries)} entries to {OUTPUT_FILE}")


def main():
    print(f"Fetching {len(FEEDS)} feeds...\n")

    all_entries = []
    for url in FEEDS:
        all_entries.extend(fetch_entries(url))

    print(f"\nTotal entries before dedup: {len(all_entries)}")
    unique_entries = deduplicate(all_entries)
    print(f"Total entries after dedup:  {len(unique_entries)}")

    # Sort by date, newest first
    unique_entries.sort(key=lambda e: e["published"], reverse=True)

    # Cap at 200 entries to keep feed manageable
    unique_entries = unique_entries[:200]

    generate_feed(unique_entries)


if __name__ == "__main__":
    main()
