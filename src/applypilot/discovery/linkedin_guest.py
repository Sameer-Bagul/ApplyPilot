"""LinkedIn Public Job Harvester.

Harvests active public engineering job cards from LinkedIn's guest collections
(e.g. remote-software-engineer-jobs, backend-engineer-jobs) using headless Playwright.
Operates with ZERO session cookies, avoiding account ban risks.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

LINKEDIN_PUBLIC_COLLECTIONS = [
    "https://www.linkedin.com/jobs/remote-software-engineer-jobs",
    "https://www.linkedin.com/jobs/backend-engineer-jobs",
    "https://www.linkedin.com/jobs/full-stack-engineer-jobs",
    "https://www.linkedin.com/jobs/python-developer-jobs",
    "https://www.linkedin.com/jobs/machine-learning-engineer-jobs",
]

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


async def _scrape_collection(url: str, max_items: int = 50) -> list[dict[str, Any]]:
    """Scrape a single public LinkedIn collection URL."""
    jobs: list[dict[str, Any]] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=_USER_AGENT)
        page = await context.new_page()
        try:
            logger.info("Visiting LinkedIn public collection: %s", url)
            await page.goto(url, timeout=20000)
            await page.wait_for_timeout(3000)

            cards = await page.query_selector_all(".base-card, .job-search-card")
            logger.info("Found %d LinkedIn cards for %s", len(cards), url)

            for c in cards[:max_items]:
                title_el = await c.query_selector(".base-search-card__title")
                company_el = await c.query_selector(".base-search-card__subtitle")
                location_el = await c.query_selector(".job-search-card__location")
                link_el = await c.query_selector("a.base-card__full-link")

                title = (await title_el.inner_text()).strip() if title_el else ""
                company = (await company_el.inner_text()).strip() if company_el else ""
                location = (await location_el.inner_text()).strip() if location_el else "Remote"
                raw_link = await link_el.get_attribute("href") if link_el else ""
                clean_link = raw_link.split("?")[0] if raw_link else ""

                if title and company and clean_link:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": clean_link,
                        "site": "linkedin",
                        "platform": "linkedin_public",
                        "execution_route": "PORTAL_ONLY",
                    })
        except Exception as e:
            logger.warning("Error scraping LinkedIn collection %s: %s", url, e)
        finally:
            await browser.close()
    return jobs


def scrape_linkedin_public_jobs(max_collections: int = 3, max_per_collection: int = 40) -> list[dict[str, Any]]:
    """Synchronous entry point to scrape multiple LinkedIn public job collections.

    Returns:
        List of normalized job dicts with title, company, location, and url.
    """
    all_jobs: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for collection_url in LINKEDIN_PUBLIC_COLLECTIONS[:max_collections]:
        try:
            scraped = asyncio.run(_scrape_collection(collection_url, max_items=max_per_collection))
            for job in scraped:
                if job["url"] not in seen_urls:
                    seen_urls.add(job["url"])
                    all_jobs.append(job)
        except Exception as e:
            logger.warning("Failed collection run for %s: %s", collection_url, e)

    return all_jobs


# Convenient alias
scrape_linkedin_guest_jobs = scrape_linkedin_public_jobs
