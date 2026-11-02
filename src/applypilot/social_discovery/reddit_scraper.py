"""Reddit .json public feed scraper for hiring posts.

Fetches new submissions from targeted hiring subreddits via public .json endpoints
without requiring Reddit API developer keys or session credentials.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_SUBREDDITS = [
    "forhire",
    "RemoteJS",
    "developersIndia",
    "golang",
    "aijobs",
    "jobbit",
    "pythonjobs",
]

_HIRING_TAGS = {"[hiring]", "(hiring)", "hiring", "[lead]", "job opening"}
_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0"


def fetch_subreddit_posts(
    subreddit: str,
    limit: int = 50,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    """Fetch recent posts from a subreddit using public JSON endpoint.

    Args:
        subreddit: Name of the subreddit (without r/).
        limit: Number of posts to fetch (max 100).
        timeout: Network timeout in seconds.

    Returns:
        List of raw submission dicts.
    """
    clean_sub = subreddit.replace("r/", "").strip()
    url = f"https://old.reddit.com/r/{clean_sub}/new.json?limit={min(limit, 100)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                logger.warning("Reddit returned status %s for r/%s", resp.status, clean_sub)
                return []
            payload = json.loads(resp.read().decode("utf-8"))
            children = payload.get("data", {}).get("children", [])
            return [child.get("data", {}) for child in children if isinstance(child, dict)]
    except Exception as e:
        logger.warning("Failed to fetch r/%s: %s", clean_sub, e)
        return []


def is_hiring_post(post: dict[str, Any]) -> bool:
    """Filter post to ensure it represents an employer hiring, not a job seeker."""
    title = (post.get("title") or "").lower()
    flair = (post.get("link_flair_text") or "").lower()
    text = (post.get("selftext") or "").lower()

    # Reject explicit seeker posts
    if "[for hire]" in title or "[forhire]" in title or "(for hire)" in title:
        return False
    if "for hire" in flair or "seeking work" in flair:
        return False

    # Positive match
    if any(tag in title for tag in _HIRING_TAGS):
        return True
    if any(tag in flair for tag in _HIRING_TAGS):
        return True
    if "we are hiring" in text or "looking for a developer" in text or "looking for an engineer" in text:
        return True

    return False


def scrape_reddit_hiring_posts(
    subreddits: list[str] | None = None,
    limit_per_sub: int = 50,
    delay_between_requests: float = 1.0,
) -> list[dict[str, Any]]:
    """Scrape and filter hiring posts across all targeted subreddits.

    Returns:
        List of normalized post dicts:
        {"title": ..., "text": ..., "url": ..., "author": ..., "created_utc": ..., "subreddit": ...}
    """
    subs = subreddits or DEFAULT_SUBREDDITS
    hiring_posts: list[dict[str, Any]] = []

    for sub in subs:
        raw_items = fetch_subreddit_posts(sub, limit=limit_per_sub)
        for item in raw_items:
            if is_hiring_post(item):
                permalink = item.get("permalink", "")
                post_url = f"https://www.reddit.com{permalink}" if permalink.startswith("/") else item.get("url", "")
                hiring_posts.append({
                    "title": item.get("title", ""),
                    "text": item.get("selftext", ""),
                    "url": post_url,
                    "author": item.get("author", ""),
                    "created_utc": item.get("created_utc"),
                    "subreddit": sub,
                    "platform": "reddit",
                })
        if delay_between_requests > 0:
            time.sleep(delay_between_requests)

    logger.info("Discovered %d hiring posts across %d subreddits", len(hiring_posts), len(subs))
    return hiring_posts
