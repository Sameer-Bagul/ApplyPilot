#!/usr/bin/env python3
"""Discovery Sources Crawler (Phase 4 Step E).

Loops over `discovery_sources` (prioritizing Pune & Bengaluru ecosystems,
GitHub awesome-lists, and India-Remote directories, with a bounded cap on
Global-Remote company additions). Deduplicates newly discovered companies
against `career_watchlist` by canonical domain & normalized company name
before insertion, and updates `discovery_sources` crawl telemetry.
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from applypilot.career_resolver.jsonld_parser import extract_jsonld_jobpostings  # noqa: E402
from applypilot.config import DB_PATH  # noqa: E402
from applypilot.database import commit_with_retry, get_connection, init_db, store_jobs, sync_execution_routes  # noqa: E402
from applypilot.discovery.url_normalize import canonicalize_application_url  # noqa: E402
from applypilot.learning.migrations import (  # noqa: E402
    _clean_domain_token,
    is_aggregator_or_ats_domain,
    run_migrations,
)
from ingest_pune_blr_remote_research import (  # noqa: E402
    is_blacklisted_entity,
    is_self_employer,
    is_specific_job_url,
    normalize_company_name,
    parse_ats_from_url,
)
from run_all_companies_looper import is_ai_sde_role  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("applypilot.sources_crawler")

IGNORED_OUTBOUND_HOSTS = (
    "twitter.com", "x.com", "facebook.com", "instagram.com", "youtube.com",
    "youtu.be", "t.me", "whatsapp.com", "play.google.com", "apps.apple.com",
    "github.com", "gist.github.com", "githubstatus.com", "medium.com", "substack.com",
    "beehiiv.com", "cloudflare.com", "fonts.googleapis.com", "w3.org", "schema.org",
    "creativecommons.org", "shields.io", "img.shields.io", "badge",
    "goodfirms.co", "clutch.co", "getchayan.com", "aipune.org", "echai.ventures",
    "fliarbi.com", "landed.jobs", "startupsgraph.com", "startupmap.in",
    "punetechmap.in", "punestartupmap.in", "bangalorestartupmap.com",
    "builtinpune.in", "builtinbengaluru.in", "builtinchennai.in", "builtindelhi.in",
    "builtinhyderabad.in", "builtinkolkata.in", "builtinmumbai.in",
    "builtinlifesciences.com", "builtinindustrial.com", "builtinretail.com",
    "interaction-design.org", "pages.dev", "wordpress.com", "blogspot.com",
    "wixsite.com", "typeform.com", "calendly.com", "notion.site", "airtable.com",
    "supablog.app", "vue.js", "react.js", "luma.com", "lu.ma", "allevents.in",
    "marketplace.visualstudio.com", "wellfound.ai", "venturebeat.com",
    "techcrunch.com", "yourstory.com", "inc42.com", "wework.com", "cubbon.run",
    "bengalurutechweek.com", "startupgrantsindia.com", "haystack.cv",
    "wikipedia.org", "yanirseroussi.com", "open.buffer.com", "buffer.com",
    "startupschool.org", "startup.google.com", "analyticsindiamag.com",
    "topmate.io", "jotform.com", "remoterocketship.com", "turing.com",
    "crossover.com", "arc.dev", "topstartups.io", "glassdoor.",
    "gov.in", "edu.in", ".edu", "ac.in", "10000startups.com", "draperstartuphouse.com",
)

IGNORED_CTA_LABELS = frozenset({
    "website", "visit website", "careers", "apply", "apply now", "jobs", "link",
    "here", "home", "read more", "learn more", "visit", "write a review",
    "leave a review", "help center", "get started", "contact us", "get a quote",
    "shortlist", "msg", "sign in", "login", "log in", "register", "privacy",
    "terms", "life sciences", "manufacturing", "retail", "built in pune",
    "built in bengaluru", "share feedback", "premium resume templates",
    "rich countries", "salary formula", "status", "view", "view job", "details",
})

_CTA_PREFIX_RE = re.compile(r"^(apply|view|open|click|learn more|read more)\b", re.IGNORECASE)
_UUID_OR_NUM_RE = re.compile(r"^(?:\d+|[0-9a-f]{8}-[0-9a-f-]{12,}|[0-9a-f]{24,})$", re.IGNORECASE)


def _derive_title_from_slug(url: str) -> str | None:
    """Extract a readable role title from a job URL path slug if possible."""
    path_parts = [p for p in urlparse(url).path.split("/") if p]
    if not path_parts:
        return None
    slug = path_parts[-1]
    if _UUID_OR_NUM_RE.match(slug):
        return None
    # Strip leading short IDs like l28KKVa-founding-engineer or 123456-software-engineer
    slug = re.sub(r"^(?:\d+|[A-Za-z0-9]{6,10})-(?=[A-Za-z])", "", slug)
    slug = re.sub(r"-[0-9a-f]{6,}$", "", slug)
    title = re.sub(r"[-_]+", " ", slug).strip().title()
    if len(title) < 4 or _UUID_OR_NUM_RE.match(title.replace(" ", "")):
        return None
    return title[:120]


def _resolve_job_title(raw_label: str, url: str) -> str | None:
    """Return clean job title or None if the link is an unresolvable CTA/URL."""
    lbl = re.sub(r"\s+", " ", html.unescape(raw_label or "")).strip()
    lbl_clean = re.sub(r"[→↗►]+", "", lbl).strip()
    if not lbl_clean or lbl_clean.lower().startswith(("http://", "https://", "www.")) or _CTA_PREFIX_RE.match(lbl_clean) or lbl_clean.lower() in IGNORED_CTA_LABELS:
        return _derive_title_from_slug(url)
    if len(lbl_clean) < 4:
        return _derive_title_from_slug(url)
    return lbl_clean[:120]


def _format_token_name(token: str) -> str:
    t = re.sub(r"(softwareprivatelimited|privatelimited|pvtltd|technologies|india|talent|people|hq)$", "", token, flags=re.IGNORECASE)
    t = re.sub(r"[-_]+", " ", t).strip()
    return t.title() if t else token.title()


def _infer_company_name(
    url: str,
    explicit_company: str | None,
    watchlist_by_ats: dict[tuple[str, str], str],
    watchlist_by_dom: dict[str, str],
) -> str | None:
    if explicit_company and explicit_company.strip() and explicit_company.strip().lower() != "unknown":
        return explicit_company.strip()

    ats_p, ats_t = parse_ats_from_url(url)
    if ats_p and ats_t:
        hit = watchlist_by_ats.get((ats_p.lower(), ats_t.lower()))
        if hit:
            return hit
        if ats_p == "workday":
            tok = ats_t.split("/")[0].split(".")[0]
            return _format_token_name(tok)
        return _format_token_name(ats_t)

    p = urlparse(url)
    host = _clean_domain_token(url)
    path_parts = [x for x in p.path.split("/") if x]
    if ("ycombinator.com" in host or "himalayas.app" in host) and len(path_parts) >= 2 and path_parts[0].lower() == "companies":
        return _format_token_name(path_parts[1])

    if host and host in watchlist_by_dom:
        return watchlist_by_dom[host]

    if host and not is_aggregator_or_ats_domain(host):
        base_dom = host.split(".", 1)[1] if host.startswith(("careers.", "jobs.", "career.")) else host
        if base_dom in watchlist_by_dom:
            return watchlist_by_dom[base_dom]
        stem = base_dom.split(".")[0]
        if len(stem) >= 2:
            return stem.title()

    return None


def _root_domain(dom: str) -> str:
    parts = dom.lower().split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "net", "ac", "gov", "edu"):
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return dom.lower()


def _extract_links_from_html_or_md(body: str, base_url: str) -> list[tuple[str, str]]:
    """Extract (label, absolute_url) pairs from HTML anchors or Markdown links."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    # Markdown links (for GitHub raw/README or markdown pages)
    for m in re.finditer(r"\[([^\]]{2,80})\]\((https?://[^)\s]+)\)", body):
        lbl = m.group(1).strip()
        u = m.group(2).strip().rstrip(".,;:")
        if u not in seen:
            seen.add(u)
            out.append((lbl, u))

    # HTML anchors
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', body, re.I | re.S):
        href = m.group(1).strip()
        lbl = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        if href.startswith("/"):
            href = origin + href
        if href.startswith("http") and href not in seen:
            seen.add(href)
            out.append((lbl, href))

    return out


def _to_raw_github_url(url: str) -> str:
    """Convert GitHub repo/blob URLs to raw README URLs for fast zero-JS parsing."""
    if "github.com/" in url and "/blob/" in url:
        return url.replace("github.com/", "raw.githubusercontent.com/").replace("/blob/", "/")
    m = re.match(r"^https?://github\.com/([^/]+/[^/?#]+)/?$", url.strip())
    if m:
        return f"https://raw.githubusercontent.com/{m.group(1)}/main/README.md"
    return url


def crawl_discovery_sources(
    db_path: Path = DB_PATH,
    limit: int | None = None,
    global_remote_cap: int = 200,
    regions: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Crawl `discovery_sources` and ingest deduplicated companies & jobs."""
    conn = get_connection(db_path)
    init_db(conn)
    run_migrations(conn)

    query = """
        SELECT url, name, region, source_type, requires_login, priority_tier
        FROM discovery_sources
        WHERE COALESCE(requires_login, 0) = 0
    """
    params: list[Any] = []
    if regions:
        ph = ",".join("?" for _ in regions)
        query += f" AND region IN ({ph})"
        params.extend(regions)

    query += """
        ORDER BY
            CASE region
                WHEN 'Pune' THEN 1
                WHEN 'Bengaluru' THEN 2
                WHEN 'India-Remote' THEN 3
                ELSE 4
            END,
            priority_tier ASC,
            COALESCE(last_crawled_at, '') ASC
    """
    if limit:
        query += " LIMIT ?"
        params.append(limit)

    sources = [dict(r) for r in conn.execute(query, params).fetchall()]

    # Existing company & job lookup sets for strict zero-duplication
    watchlist_rows = conn.execute(
        "SELECT company_name, official_domain, ats_provider, ats_board_token FROM career_watchlist"
    ).fetchall()
    existing_domains: set[str] = set()
    existing_norm_names: set[str] = set()
    watchlist_by_dom: dict[str, str] = {}
    watchlist_by_ats: dict[tuple[str, str], str] = {}
    for wr in watchlist_rows:
        cname = wr[0]
        dom_v = wr[1]
        ats_p_v = wr[2]
        ats_t_v = wr[3]
        if dom_v:
            d_low = dom_v.lower().strip()
            existing_domains.add(d_low)
            if cname:
                watchlist_by_dom[d_low] = cname
        if cname:
            existing_norm_names.add(normalize_company_name(cname).lower())
            if ats_p_v and ats_t_v:
                watchlist_by_ats[(ats_p_v.lower().strip(), ats_t_v.lower().strip())] = cname

    source_domains: set[str] = {
        _clean_domain_token(r[0])
        for r in conn.execute("SELECT url FROM discovery_sources").fetchall()
        if r[0]
    }
    existing_job_urls: set[str] = {
        r[0].rstrip("/") for r in conn.execute("SELECT url FROM jobs").fetchall() if r[0]
    }
    existing_job_ct: set[tuple[str, str]] = {
        (r[0].strip().lower(), re.sub(r"\s+", " ", r[1].strip().lower()))
        for r in conn.execute("SELECT company, title FROM jobs WHERE company IS NOT NULL AND title IS NOT NULL").fetchall()
    }

    total_companies_added = 0
    total_jobs_added = 0
    global_remote_added = 0
    crawled_count = 0
    failed_count = 0

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/json,text/plain,*/*",
    }

    with httpx.Client(headers=headers, follow_redirects=True, timeout=8.0) as client:
        for src in sources:
            src_url = src["url"]
            region = src["region"] or "Global-Remote"
            fetch_url = _to_raw_github_url(src_url)
            comps_found = 0
            jobs_found = 0
            now_iso = datetime.now(timezone.utc).isoformat()

            try:
                resp = client.get(fetch_url, timeout=8.0)
                if resp.status_code >= 400 and fetch_url != src_url:
                    # Fallback for master branch on GitHub
                    resp = client.get(fetch_url.replace("/main/", "/master/"), timeout=8.0)
                if resp.status_code >= 400:
                    failed_count += 1
                    conn.execute(
                        "UPDATE discovery_sources SET last_crawled_at = ? WHERE url = ?",
                        (now_iso, src_url),
                    )
                    commit_with_retry(conn)
                    continue

                body = resp.text
                crawled_count += 1
                src_host = _clean_domain_token(src_url)

                # 1. JSON-LD JobPostings if any
                for jb in extract_jsonld_jobpostings(body, base_url=src_url):
                    ju = (jb.get("url") or "").strip()
                    jt = _resolve_job_title(jb.get("title") or "", ju)
                    if not ju or not jt:
                        continue
                    canon_ju = canonicalize_application_url(ju)
                    if canon_ju.rstrip("/") in existing_job_urls or ju.rstrip("/") in existing_job_urls:
                        continue
                    if not is_ai_sde_role(jt):
                        continue
                    jcomp = _infer_company_name(canon_ju, jb.get("company"), watchlist_by_ats, watchlist_by_dom) or "Unknown"
                    ct_key = (jcomp.lower(), re.sub(r"\s+", " ", jt.lower()))
                    if jcomp != "Unknown" and ct_key in existing_job_ct:
                        continue
                    existing_job_urls.add(canon_ju.rstrip("/"))
                    if jcomp != "Unknown":
                        existing_job_ct.add(ct_key)
                    new_c, _ = store_jobs(
                        conn=conn,
                        jobs=[{
                            "url": canon_ju,
                            "title": jt,
                            "company": jcomp,
                            "location": jb.get("location") or region,
                            "description": (jb.get("description") or "")[:1000],
                        }],
                        site=src_host or "discovery_source",
                        strategy="discovery_source_crawler",
                    )
                    if new_c > 0:
                        jobs_found += 1
                        total_jobs_added += 1

                # 2. Outbound company & specific job links
                links = _extract_links_from_html_or_md(body, src_url)
                src_root = _root_domain(src_host) if src_host else ""
                for lbl, u in links:
                    dom = _clean_domain_token(u)
                    if not dom or "." not in dom or dom == src_host:
                        continue
                    if src_root and _root_domain(dom) == src_root:
                        continue
                    if any(ih in dom for ih in IGNORED_OUTBOUND_HOSTS):
                        continue
                    if is_blacklisted_entity(lbl, u) or is_self_employer(lbl, dom):
                        continue

                    # Specific job posting
                    if is_specific_job_url(u):
                        canon_u = canonicalize_application_url(u)
                        if canon_u.rstrip("/") in existing_job_urls or u.rstrip("/") in existing_job_urls:
                            continue
                        resolved_title = _resolve_job_title(lbl, canon_u)
                        if not resolved_title or not is_ai_sde_role(resolved_title):
                            continue
                        jcomp = _infer_company_name(canon_u, None, watchlist_by_ats, watchlist_by_dom)
                        if not jcomp:
                            continue
                        ct_key = (jcomp.lower(), re.sub(r"\s+", " ", resolved_title.lower()))
                        if ct_key in existing_job_ct:
                            continue
                        existing_job_urls.add(canon_u.rstrip("/"))
                        existing_job_ct.add(ct_key)
                        ats_p, _ = parse_ats_from_url(canon_u)
                        new_c, _ = store_jobs(
                            conn=conn,
                            jobs=[{
                                "url": canon_u,
                                "title": resolved_title,
                                "company": jcomp,
                                "location": region,
                                "description": f"Discovered from {src['name']} ({src_url})",
                            }],
                            site=ats_p or src_host or "discovery_source",
                            strategy="discovery_source_crawler",
                        )
                        if new_c > 0:
                            jobs_found += 1
                            total_jobs_added += 1
                        continue

                    # Candidate company website
                    if is_aggregator_or_ats_domain(dom) or dom in source_domains:
                        continue
                    if region == "Global-Remote" and global_remote_added >= global_remote_cap:
                        continue

                    # Strip careers./jobs./career. prefix to canonical root company domain
                    careers_u = u if any(k in u.lower() for k in ("career", "jobs", "join")) else None
                    if dom.startswith(("careers.", "jobs.", "career.")):
                        dom = dom.split(".", 1)[1]
                    if is_aggregator_or_ats_domain(dom) or dom in source_domains:
                        continue

                    clean_lbl = html.unescape(lbl)
                    if clean_lbl.lower().startswith(("http://", "https://", "http//", "https//", "www.")):
                        clean_lbl = dom.split(".")[0].title()
                    clean_lbl = re.sub(r"[^A-Za-z0-9.&/ -]", "", clean_lbl).strip()
                    if clean_lbl.lower().startswith(("http", "www")):
                        clean_lbl = dom.split(".")[0].title()
                    if clean_lbl.lower() in IGNORED_CTA_LABELS or clean_lbl.lower().startswith(("visit ", "write ", "leave ", "get a ", "built in ", "continue as ", "my ", "how ", "why ", "what ")):
                        continue
                    # Reject prose/sentence labels from markdown articles
                    if len(clean_lbl.split()) > 5 or (clean_lbl == clean_lbl.lower() and len(clean_lbl.split()) >= 2):
                        continue
                    if len(clean_lbl) < 2 or len(clean_lbl) > 60:
                        continue
                    if "." in clean_lbl and clean_lbl.lower() == dom:
                        clean_lbl = dom.split(".")[0].title()

                    norm_n = normalize_company_name(clean_lbl).lower()
                    if not norm_n or len(norm_n) < 2:
                        continue
                    if dom in existing_domains or norm_n in existing_norm_names:
                        continue

                    existing_domains.add(dom)
                    existing_norm_names.add(norm_n)
                    watchlist_by_dom[dom] = clean_lbl
                    cid = f"comp_{uuid.uuid4().hex[:10]}"
                    ats_p, ats_t = parse_ats_from_url(u)
                    tier = 1 if region in ("Pune", "Bengaluru", "India-Remote") else 2

                    conn.execute(
                        """
                        INSERT INTO career_watchlist (
                            company_id, company_name, official_domain, careers_page_url,
                            ats_provider, ats_board_token, priority_tier, is_vip,
                            area, location, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            cid,
                            clean_lbl,
                            dom,
                            careers_u,
                            ats_p,
                            ats_t,
                            tier,
                            1 if region in ("Pune", "Bengaluru") else 0,
                            region if region in ("Pune", "Bengaluru") else None,
                            region,
                            json.dumps({"discovered_from": src_url}),
                        ),
                    )
                    comps_found += 1
                    total_companies_added += 1
                    if region == "Global-Remote":
                        global_remote_added += 1

                conn.execute(
                    """
                    UPDATE discovery_sources
                    SET last_crawled_at = ?,
                        companies_found = COALESCE(companies_found, 0) + ?,
                        jobs_found = COALESCE(jobs_found, 0) + ?
                    WHERE url = ?
                    """,
                    (now_iso, comps_found, jobs_found, src_url),
                )
                commit_with_retry(conn)
                logger.info("[%s] %s -> +%d companies, +%d jobs", region, src["name"], comps_found, jobs_found)
            except Exception as e:
                failed_count += 1
                logger.debug("Source crawl error for %s: %s", src_url, e)
                conn.execute(
                    "UPDATE discovery_sources SET last_crawled_at = ? WHERE url = ?",
                    (now_iso, src_url),
                )
                commit_with_retry(conn)

    sync_execution_routes(conn)
    return {
        "sources_queued": len(sources),
        "sources_crawled": crawled_count,
        "sources_failed": failed_count,
        "companies_added": total_companies_added,
        "global_remote_added": global_remote_added,
        "jobs_added": total_jobs_added,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl discovery_sources for Pune/Bengaluru/Remote startups & jobs.")
    parser.add_argument("--limit", type=int, default=40, help="Max sources to crawl in this run.")
    parser.add_argument("--global-remote-cap", type=int, default=200, help="Cap net-new Global-Remote companies per run.")
    parser.add_argument("--regions", nargs="*", default=None, help="Optional region filter(s).")
    parser.add_argument("--db-path", type=str, default=str(DB_PATH))
    args = parser.parse_args()

    res = crawl_discovery_sources(
        db_path=Path(args.db_path),
        limit=args.limit,
        global_remote_cap=args.global_remote_cap,
        regions=tuple(args.regions) if args.regions else None,
    )
    print(res)


if __name__ == "__main__":
    main()
