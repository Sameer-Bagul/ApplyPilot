"""Hacker News 'Who is Hiring' Thread Scraper.

Extracts published founder/recruiter emails and direct ATS links from the official
monthly 'Ask HN: Who is hiring?' threads using the public Algolia HN API.
"""

from __future__ import annotations

import html
import json
import logging
import re
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_USER_AGENT = "ApplyPilot/1.0 (HN Hiring Harvester; contact@applypilot.local)"


def clean_hn_html(raw_html: str) -> str:
    """Unescape HTML entities and replace break/paragraph tags with clean newlines."""
    if not raw_html:
        return ""
    # Unescape HTML entities (&#x2F; -> /, &amp; -> &, &quot; -> ", etc.)
    text = html.unescape(raw_html)
    # Replace paragraph/break tags with newlines
    text = re.sub(r"<\s*p\s*/?\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse excess whitespace
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def fetch_latest_hiring_threads(limit: int = 2, timeout: float = 12.0) -> list[dict[str, Any]]:
    """Fetch the latest official 'Ask HN: Who is hiring?' threads.

    Filters out 'Who wants to be hired?' and 'Freelancer? Seeking freelancer?' threads.
    """
    url = f"https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage={max(10, limit * 4)}"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})

    threads: list[dict[str, Any]] = []
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for hit in data.get("hits", []):
                title = hit.get("title", "")
                if "Who is hiring?" in title:
                    threads.append({
                        "id": hit.get("objectID"),
                        "title": title,
                        "created_at": hit.get("created_at"),
                        "num_comments": hit.get("num_comments", 0),
                    })
                    if len(threads) >= limit:
                        break
    except Exception as e:
        logger.warning("Failed to fetch HN hiring threads: %s", e)

    return threads


def fetch_thread_comments(story_id: str | int, timeout: float = 20.0) -> list[dict[str, Any]]:
    """Fetch top-level comments for a given HN story ID."""
    url = f"https://hn.algolia.com/api/v1/items/{story_id}"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            children = data.get("children", [])
            return children
    except Exception as e:
        logger.warning("Failed to fetch comments for story %s: %s", story_id, e)
        return []


def scrape_hn_hiring_posts(
    max_threads: int = 1,
    max_comments_per_thread: int = 300,
) -> list[dict[str, Any]]:
    """Scrape and normalize top-level hiring comments from recent HN hiring threads.

    Returns:
        List of normalized post dicts with title, text, url, and platform.
    """
    threads = fetch_latest_hiring_threads(limit=max_threads)
    posts: list[dict[str, Any]] = []

    for thread in threads:
        story_id = thread["id"]
        story_title = thread["title"]
        logger.info("Fetching HN hiring comments for %s (ID %s)...", story_title, story_id)

        comments = fetch_thread_comments(story_id)
        for comment in comments[:max_comments_per_thread]:
            raw_text = comment.get("text")
            if not raw_text:
                continue

            clean_text = clean_hn_html(raw_text)
            if len(clean_text) < 40:
                continue

            comment_id = comment.get("id")
            post_url = f"https://news.ycombinator.com/item?id={comment_id}" if comment_id else f"https://news.ycombinator.com/item?id={story_id}"

            # Extract headline from first line of text
            first_line = clean_text.split("\n")[0].strip()
            headline = first_line[:120] if first_line else story_title

            posts.append({
                "title": headline,
                "text": clean_text,
                "url": post_url,
                "platform": "hackernews",
                "author": comment.get("author", "hn_user"),
                "thread_title": story_title,
            })

    return posts
