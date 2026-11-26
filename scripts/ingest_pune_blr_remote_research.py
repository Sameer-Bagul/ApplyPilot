#!/usr/bin/env python3
"""Idempotent Zero-Duplication Research Ingestion Pipeline (Pune / Bengaluru / Remote).

Ingests, canonicalizes, deduplicates, and routes intelligence from:
1. AI_SDE_Master_Company_Database.csv (917 companies, URLs, emails, founders, roles)
2. Pune_Discovery_Sources.csv (11 Pune discovery directories)
3. ChatGPT-New chat-20261126-1609.md (58 markdown tables, specific job URLs, directories, GitHub lists)
4. Pune_AI_SDE_Company_Tracker.xlsx (stdlib zipfile+xml parity verification, zero openpyxl dependency)

Supports --dry-run (collision & alias audit with rollback) and --commit.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import html
import json
import logging
import re
import sqlite3
import sys
import uuid
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse, urlunparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from applypilot.config import DB_PATH  # noqa: E402
from applypilot.database import get_connection, init_db, sync_execution_routes  # noqa: E402
from applypilot.learning.migrations import (  # noqa: E402
    _clean_domain_token,
    is_aggregator_or_ats_domain,
    run_migrations,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("applypilot.research_ingest")

DEFAULT_MASTER_CSV = PROJECT_ROOT / "AI_SDE_Master_Company_Database.csv"
DEFAULT_SOURCES_CSV = PROJECT_ROOT / "Pune_Discovery_Sources.csv"
DEFAULT_TRACKER_XLSX = PROJECT_ROOT / "Pune_AI_SDE_Company_Tracker.xlsx"
DEFAULT_CHATGPT_MD = PROJECT_ROOT / "ChatGPT-New chat-20261126-1609.md"

BLACKLISTED_NAMES = frozenset({
    "sameer bagul",
    "chatgpt",
    "chatgptexporter",
    "company",
    "column",
    "platform",
})

BLACKLISTED_DOMAINS = frozenset({
    "chatgpt.com",
    "chatgptexporter.com",
})

BLACKLISTED_URL_SUBSTRINGS = (
    "in.linkedin.com/in/sameer-bagul",
    "linkedin.com/in/sameer-bagul",
    "chatgpt.com",
    "chatgptexporter.com",
)

SELF_EMPLOYER_NAMES = frozenset({"revcloud"})
SELF_EMPLOYER_DOMAINS = frozenset({"revcloud.com"})

EXPLICIT_COMPANY_ALIASES: dict[str, str] = {
    "metamorphosys": "metamorphosys technologies",
    "pixel6": "pixel6 web studio",
    "wipro linecraft ai": "wipro",
    "sap labs": "sap",
    "jisa softech": "jisa",
    "rian / rikaian technology": "rian",
    "fourise software solutions pvt. ltd pune": "fourise software solutions",
    "codiastic soft pvt ltd-ai solutions": "codiastic soft",
    "coreco technologies private limited": "coreco technologies",
    "algoanalytics private limited": "algoanalytics",
    "thenoah.ai": "thenoah",
    "immersivedata.ai": "immersivedata",
}

SEARCH_DOMAINS = (
    "google.com",
    "bing.com",
    "duckduckgo.com",
)


def clean_markdown_text(text: str) -> str:
    """Unescape ChatGPT Markdown artifacts, HTML entities, and strip entity markup tokens."""
    if not text:
        return ""
    s = html.unescape(
        text.replace(r"\_", "_")
        .replace(r"\@", "@")
        .replace(r"\&", "&")
        .replace(r"\#", "#")
        .replace(r"\|", "|")
    )
    # Strip \ue200entity\ue202[...,"Label"]\ue201 and any \ue200...\ue201 spans
    s = re.sub(r"\ue200[^\ue201]*\ue201", "", s)
    return s


def clean_url(url: str) -> str:
    """Clean tracking parameters (utm_source=chatgpt.com), trailing punctuation, and whitespace."""
    if not url:
        return ""
    u = clean_markdown_text(url).strip().rstrip(".,;:)`'\"")
    if not u.startswith(("http://", "https://")):
        return u
    try:
        p = urlparse(u)
        if p.query:
            qs = [
                (k, v)
                for k, vals in parse_qs(p.query, keep_blank_values=True).items()
                if k.lower() != "utm_source"
                for v in vals
            ]
            new_q = "&".join(f"{k}={v}" if v != "" else k for k, v in qs)
        else:
            new_q = ""
        return urlunparse((p.scheme, p.netloc, p.path, p.params, new_q, p.fragment))
    except Exception:
        return u


def is_blacklisted_entity(name: str = "", url: str = "") -> bool:
    """Return True for hard-blacklisted self-profile or ChatGPT meta rows."""
    n_low = re.sub(r"\s+", " ", (name or "").strip().lower())
    if n_low in BLACKLISTED_NAMES or "sameer bagul" in n_low:
        return True
    u_low = (url or "").strip().lower()
    if any(sub in u_low for sub in BLACKLISTED_URL_SUBSTRINGS):
        return True
    dom = _clean_domain_token(url)
    if dom in BLACKLISTED_DOMAINS:
        return True
    return False


def is_self_employer(name: str = "", domain: str = "") -> bool:
    """Return True if row corresponds to user's current employer (Revcloud)."""
    n_low = normalize_company_name(name).lower()
    d_low = _clean_domain_token(domain)
    return n_low in SELF_EMPLOYER_NAMES or d_low in SELF_EMPLOYER_DOMAINS


def normalize_company_name(name: str) -> str:
    """Normalize company name by stripping parentheticals, SEO subtitles, legal suffixes, and punctuation."""
    if not name:
        return ""
    s = clean_markdown_text(name)
    s = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", s).strip()
    s = re.split(
        r"\s+[-–—]\s+(?:AI|Ai|Mobile|Digital|Software|Technology|GenAI|Solutions|Driven)\b",
        s,
        maxsplit=1,
    )[0].strip()
    s = re.sub(
        r"(?i),?\s*\b("
        r"inc\.?|llc|l\.l\.c\.?|ltd\.?|limited|pvt\.?\s*ltd\.?|"
        r"private\s+limited|corp\.?|corporation|gmbh|co\.?|llp"
        r")\b\.?$",
        "",
        s,
    ).strip()
    s = re.sub(r"[\s,\.-]+$", "", s).strip()
    return re.sub(r"\s+", " ", s)


def normalize_email(raw: str | None) -> str | None:
    """Normalize email address, stripping trailing dots and rejecting invalid/aggregator addresses."""
    if not raw:
        return None
    s = clean_markdown_text(raw).strip().rstrip(".,;:").lower()
    m = re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", s)
    if not m:
        return None
    em = m.group(0).rstrip(".")
    dom = em.split("@", 1)[1]
    if is_aggregator_or_ats_domain(dom) or dom in BLACKLISTED_DOMAINS:
        return None
    return em


def parse_ats_from_url(url: str | None) -> tuple[str | None, str | None]:
    """Detect ATS provider and board token from a career or job URL."""
    if not url:
        return None, None
    u = url.strip()
    patterns: list[tuple[str, str]] = [
        ("greenhouse", r"(?:job-boards|boards)\.greenhouse\.io/([^/?#]+)"),
        ("greenhouse", r"greenhouse\.io/(?:embed/job_app\?for=|[^/?#]*?/)([^/?#&]+)"),
        ("ashby", r"jobs\.ashbyhq\.com/([^/?#]+)"),
        ("lever", r"jobs\.lever\.co/([^/?#]+)"),
        ("workable", r"apply\.workable\.com/([^/?#]+)"),
        ("smartrecruiters", r"(?:jobs|careers)\.smartrecruiters\.com/([^/?#]+)"),
        ("bamboohr", r"([^./]+)\.bamboohr\.com"),
        ("freshteam", r"([^./]+)\.freshteam\.com"),
        ("zohorecruit", r"([^./]+)\.zohorecruit\.(?:in|com)"),
        ("keka", r"([^./]+)\.keka\.com"),
        ("param", r"([^./]+)\.param\.ai"),
        ("jobvite", r"jobs\.jobvite\.com/(?:careers/)?([^/?#]+)"),
        ("recruitee", r"([^./]+)\.recruitee\.com"),
        ("teamtailor", r"(?:career|jobs)?\.?([^./]+)\.teamtailor\.com"),
        ("breezy", r"([^./]+)\.breezy\.hr"),
        ("personio", r"([^./]+)\.jobs\.personio\.(?:de|com)"),
    ]
    for prov, pat in patterns:
        m = re.search(pat, u, re.IGNORECASE)
        if m:
            token = m.group(1).strip()
            if token.lower() not in ("embed", "jobs", "careers", "v1"):
                return prov, token
    if "myworkdayjobs.com" in u.lower():
        parsed = urlparse(u)
        host = parsed.netloc.lower()
        tenant = host.split(".")[0]
        parts = [p for p in parsed.path.split("/") if p and not re.match(r"^[a-z]{2}-[A-Z]{2}$", p)]
        site = parts[0] if parts and parts[0].lower() != "job" else "External"
        return "workday", f"{host}/{tenant}/{site}"
    return None, None


def careers_url_quality_rank(url: str | None) -> int:
    """Rank URL quality: 4=Direct ATS, 3=Custom /careers, 2=Aggregator, 1=Homepage, 0=Empty."""
    if not url or not str(url).strip():
        return 0
    u = str(url).strip()
    if not u.startswith(("http://", "https://")):
        return 0
    prov, _ = parse_ats_from_url(u)
    if prov:
        return 4
    dom = _clean_domain_token(u)
    if is_aggregator_or_ats_domain(dom):
        return 2
    path = (urlparse(u).path or "").lower().strip("/")
    if any(k in path for k in ("career", "jobs", "job", "join", "opening", "position", "hiring")):
        return 3
    return 1


def is_specific_job_url(url: str) -> bool:
    """Return True ONLY when url points to a specific job posting, not a /careers index or search page."""
    if not url or not url.startswith(("http://", "https://")):
        return False
    p = urlparse(url)
    host = p.netloc.lower()
    path = (p.path or "").lower().rstrip("/")
    query = (p.query or "").lower()

    if any(sd in host for sd in SEARCH_DOMAINS) or "linkedin.com/search" in url.lower():
        return False
    if any(blk in url.lower() for blk in BLACKLISTED_URL_SUBSTRINGS):
        return False

    # Reject aggregator category/search/listing pages
    if any(agg in host for agg in (
        "turing.com", "crossover.com", "remoterocketship.com", "cutshort.io",
        "weworkremotely.com", "remoteok.com", "remotive.com", "workingnomads.com",
        "nodesk.co", "arc.dev", "topstartups.io", "builtin", "startupmap.in",
    )):
        return False

    # Reject obvious index/search pages
    if path in ("", "/careers", "/career", "/jobs", "/join", "/join-us", "/openings", "/positions", "/en-in/careers", "/about/careers", "/company/careers"):
        return False
    if path.endswith(("/search", "/positions", "/applications", "/job-opportunities", "/careers/job-opportunities")):
        return False

    # Specific ATS job postings
    if "greenhouse.io" in host and ("/jobs/" in path or "gh_jid=" in query):
        return True
    if "ashbyhq.com" in host and len([x for x in path.split("/") if x]) >= 2:
        return True
    if "lever.co" in host and len([x for x in path.split("/") if x]) >= 2 and not query.startswith(("location=", "workplacetype=")):
        return True
    if "myworkdayjobs.com" in host and "/job/" in path:
        return True
    if "apply.workable.com" in host and "/j/" in path:
        return True
    if "zohorecruit." in host and "/jobs/careers/" in path and len([x for x in path.split("/") if x]) >= 4:
        return True
    if "keka.com" in host and re.search(r"/careers/\d+", path):
        return True
    if "linkedin.com/jobs/view/" in url.lower():
        return True
    if "wellfound.com/jobs/" in url.lower():
        return True
    if "hirist.tech/j/" in url.lower():
        return True
    if "ycombinator.com/companies/" in url.lower() and "/jobs/" in path:
        return True
    if "himalayas.app/companies/" in url.lower() and "/jobs/" in path:
        return True
    if "hacker-careers.com/job/" in url.lower():
        return True
    if "djinni.co/jobs/" in url.lower() and re.search(r"/jobs/\d+", path):
        return True
    if "freehire.me/jobs/" in url.lower() or "riseflake.com/jobs/" in url.lower() or "tcsion.com/jobs/" in url.lower() or "remotely.living/jobs/" in url.lower() or "jobsalertx.com/jobs/" in url.lower():
        return True

    # Custom company job detail pages (must have deeper path under /careers/ or /jobs/ or /job/ with role slug)
    if re.search(r"/(?:careers|jobs|job)/(?:details/|job/)?[a-z0-9][a-z0-9_-]{4,}", path):
        if not any(idx_word in path for idx_word in ("/countries/", "/category/", "/location/", "/role/")):
            return True
    if "job?id=" in url.lower():
        return True
    return False


def make_synthetic_email(name: str, company: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "contact"
    h = hashlib.sha256(f"{name.lower()}|{company.lower()}".encode("utf-8")).hexdigest()[:8]
    return f"linkedin-{slug}-{h}@connect.linkedin.com"


def parse_xlsx_parity(xlsx_path: Path) -> dict[str, Any]:
    """Parse Pune_AI_SDE_Company_Tracker.xlsx with Python stdlib zipfile + xml (no openpyxl)."""
    if not xlsx_path.exists():
        return {"exists": False, "companies": [], "sources": []}
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(xlsx_path) as z:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            ss_root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in ss_root.findall("s:si", ns):
                shared_strings.append("".join(t.text or "" for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")))

        def read_sheet(name: str) -> list[list[str]]:
            if name not in z.namelist():
                return []
            root = ET.fromstring(z.read(name))
            out: list[list[str]] = []
            for row in root.findall(".//s:row", ns):
                vals: list[str] = []
                for c in row.findall("s:c", ns):
                    ctype = c.attrib.get("t")
                    if ctype == "inlineStr":
                        vals.append("".join(t.text or "" for t in c.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")).strip())
                    elif ctype == "s":
                        v = c.find("s:v", ns)
                        idx = int(v.text) if v is not None and v.text is not None else -1
                        vals.append(shared_strings[idx].strip() if 0 <= idx < len(shared_strings) else "")
                    else:
                        v = c.find("s:v", ns)
                        vals.append((v.text or "").strip() if v is not None else "")
                out.append(vals)
            return out

        s1 = read_sheet("xl/worksheets/sheet1.xml")
        s2 = read_sheet("xl/worksheets/sheet2.xml")

    companies = [r[1] for r in s1[1:] if len(r) >= 2 and r[1]]
    sources = [r[2] for r in s2[1:] if len(r) >= 3 and r[2]]
    return {"exists": True, "companies": companies, "sources": sources}


def extract_md_links_and_urls(cell: str) -> list[tuple[str, str]]:
    """Return list of (label, cleaned_url) from a markdown table cell or line."""
    results: list[tuple[str, str]] = []
    cleaned = clean_markdown_text(cell)
    for m in re.finditer(r"\[([^\]]*)\]\((https?://[^)\s]+)\)", cleaned):
        results.append((m.group(1).strip(), clean_url(m.group(2))))
    stripped = re.sub(r"\[([^\]]*)\]\((https?://[^)\s]+)\)", "", cleaned)
    for m in re.finditer(r"(https?://[^\s,;|)\]>\"'`]+)", stripped):
        results.append(("", clean_url(m.group(1))))
    return results


def parse_discovery_sources(sources_csv_path: Path, md_text: str) -> list[dict[str, Any]]:
    """Parse curated directories & GitHub awesome-lists from Pune_Discovery_Sources.csv and ChatGPT MD."""
    sources_by_url: dict[str, dict[str, Any]] = {}

    def classify_source(url: str, name: str, notes: str = "") -> dict[str, Any]:
        u_low = url.lower()
        n_low = (name + " " + notes).lower()
        if "pune" in u_low or "pune" in n_low or "aipune" in u_low or "chayan" in u_low or "fliarbi" in u_low or "lets-code.co.in/startups" in u_low:
            region = "Pune"
        elif "bengaluru" in u_low or "bangalore" in u_low or "blr" in n_low or "bengaluru" in n_low:
            region = "Bengaluru"
        elif "india" in u_low or "india" in n_low or "gullyhire" in u_low or "rolenest" in u_low or "openroles.in" in u_low or "switchly.in" in u_low or "cutshort" in u_low or "hirist" in u_low:
            region = "India-Remote"
        else:
            region = "Global-Remote"

        if "github.com" in u_low or "gist.github.com" in u_low:
            stype = "github_list"
            tier = 1
        elif "echai" in u_low or "ycombinator" in u_low or "startupmap" in u_low or "punetechmap" in u_low or "bangalorestartupmap" in u_low or "aipune" in u_low:
            stype = "vc_ecosystem"
            tier = 1
        elif "blog" in u_low or "beehiiv" in u_low or "lets-code.co.in/blogs" in u_low or "serversidestory" in u_low or "reallyremote" in u_low or "jobrise.io" in u_low:
            stype = "blog_curated"
            tier = 2
        elif any(k in u_low for k in ("companies", "directory", "goodfirms", "clutch", "sortlist", "leadsetu", "addressbay", "fliarbi", "getchayan", "gccexplorer", "flexiple.com/gcc", "startupsgraph", "landed.jobs")):
            stype = "directory"
            tier = 1 if region in ("Pune", "Bengaluru") else 2
        else:
            stype = "job_board"
            tier = 2

        req_login = 1 if ("leadsetu.io" in u_low or "indianstartupmap.com" in u_low) else 0
        return {
            "url": url,
            "name": name or _clean_domain_token(url),
            "region": region,
            "source_type": stype,
            "requires_login": req_login,
            "scope_notes": notes or None,
            "priority_tier": tier,
        }

    # 1. From Pune_Discovery_Sources.csv
    if sources_csv_path.exists():
        with open(sources_csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                u = clean_url(r.get("URL", ""))
                if not u:
                    continue
                name = r.get("Directory", "").strip()
                scope = r.get("Scope reported by directory", "").strip()
                notes = r.get("Notes", "").strip()
                combined_notes = " — ".join(p for p in (scope, notes) if p)
                sources_by_url[u.rstrip("/")] = classify_source(u, name, combined_notes)

    # 2. From ChatGPT MD Platform tables & curated directory/GitHub URLs
    cleaned_md = clean_markdown_text(md_text)
    lines = cleaned_md.splitlines()

    # Tables starting with | Platform | Link ...
    in_platform_table = False
    for line in lines:
        s = line.strip()
        if s.startswith("|"):
            cols = [c.strip() for c in s.strip("|").split("|")]
            if len(cols) >= 2 and cols[0].lower() == "platform" and "link" in cols[1].lower():
                in_platform_table = True
                continue
            if in_platform_table:
                if all(set(c) <= set("-: ") for c in cols):
                    continue
                pname = cols[0]
                links = extract_md_links_and_urls(cols[1])
                notes = cols[2] if len(cols) >= 3 else ""
                for _, u in links:
                    if not is_blacklisted_entity(pname, u):
                        key = u.rstrip("/")
                        if key not in sources_by_url:
                            sources_by_url[key] = classify_source(u, pname, notes)
        else:
            in_platform_table = False

    # Prose directory / GitHub list / portal links in MD
    directory_hosts_or_paths = (
        "github.com/", "gist.github.com/", "builtin", "startupmap", "punetechmap",
        "punestartupmap", "bangalorestartupmap", "getchayan.com", "fliarbi.com",
        "echai.ventures", "goodfirms.co", "clutch.co/in/", "sortlist.com",
        "startupsgraph.com", "landed.jobs", "earlystagestartups.com", "earlystagehires.com",
        "flexiple.com/gcc", "gccexplorer.com", "gccjournal.in", "remoteintech.company",
        "hiring.ai/companies", "remoteai.io/companies", "seekter.dev/companies",
        "flyhirevia.com/companies", "apply.hardikk.dev/c/companies", "hirecept.com",
        "workfromanywhere.co", "realworkfromanywhere.com", "stillremote.com",
        "trulyremotework.com", "matcha.fm", "nodesk.co", "remoterocketship.com",
        "workingnomads.com", "weworkremotely.com", "remotive.com", "remoteok.com",
        "himalayas.app/jobs", "wellfound.com/jobs", "wellfound.com/role/",
        "ycombinator.com/jobs", "peerlist.io/jobs", "cutshort.io/jobs/",
        "haystackapp.io", "hourzerojobs.com", "gullyhire.in", "remotavia.com",
        "remotehunt.app", "remotelyscaled.com", "remjobs.works", "openroles.in",
        "opening.live", "rolenest.in", "useastra.in", "gethyr.app", "labspie.com",
        "jobs.punestartups.org", "switchly.in", "openaibuzz.com", "toolhund.com",
        "theblrcircle.beehiiv.com", "blog.resumail.in", "jobrise.io",
        "serversidestory.com", "reallyremote.co", "lets-code.co.in", "aipune.org",
        "leadsetu.io", "addressbay.com", "indianstartupmap.com",
        "codingprepguide.com/jobs/remote", "jobs.askbengaluru.com", "jobs.skynettstudio.com",
        "jobseveryhour.com", "onlinejobpotal.in", "startups.mapmyhyd.com", "tecxskill.com",
        "wokab.in", "andhrastartupmap.in", "nextknock.in", "remotide.vercel.app",
    )
    for label, u in extract_md_links_and_urls(cleaned_md):
        u_low = u.lower()
        if any(sd in u_low for sd in SEARCH_DOMAINS) or "linkedin.com/search" in u_low:
            continue
        if is_blacklisted_entity(label, u):
            continue
        if any(pat in u_low for pat in directory_hosts_or_paths):
            # Exclude individual company profile pages like clutch.co/profile/... or punestartupmap.in/?company=...
            if "clutch.co/profile/" in u_low or "?company=" in u_low:
                continue
            key = u.rstrip("/")
            if key not in sources_by_url:
                clean_lbl = re.sub(r"\s*\|.*$", "", label).strip() if label else ""
                sources_by_url[key] = classify_source(u, clean_lbl or _clean_domain_token(u))

    return list(sources_by_url.values())


def parse_master_csv(csv_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse AI_SDE_Master_Company_Database.csv into companies, leads, and specific jobs."""
    companies: list[dict[str, Any]] = []
    leads: list[dict[str, Any]] = []
    jobs: list[dict[str, Any]] = []

    with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
        for r in csv.DictReader(f):
            cname = (r.get("Company") or "").strip()
            if not cname or is_blacklisted_entity(cname):
                continue

            website = clean_url(r.get("Website") or "")
            career_raw = (r.get("Career / job links") or "").strip()
            career_urls = [clean_url(u) for u in re.findall(r"https?://[^\s,;|)\]>]+", career_raw)]
            career_urls = [u for u in career_urls if u and not is_blacklisted_entity("", u)]

            official_dom = _clean_domain_token(website)
            if official_dom and is_aggregator_or_ats_domain(official_dom):
                official_dom = ""

            # Derive official_domain from direct non-aggregator career link if Website was empty
            if not official_dom:
                for cu in career_urls:
                    cand = _clean_domain_token(cu)
                    if cand and "." in cand and not is_aggregator_or_ats_domain(cand) and not any(sd in cand for sd in SEARCH_DOMAINS):
                        official_dom = cand
                        break

            # Choose best careers_page_url
            best_careers = None
            best_rank = -1
            for cu in career_urls + ([website] if website else []):
                rk = careers_url_quality_rank(cu)
                if rk > best_rank:
                    best_rank = rk
                    best_careers = cu

            ats_prov, ats_tok = parse_ats_from_url(best_careers)
            if not ats_prov:
                for cu in career_urls:
                    ats_prov, ats_tok = parse_ats_from_url(cu)
                    if ats_prov:
                        break

            # Parse founders / contacts
            raw_founders = (r.get("Public founder / contact") or "").strip()
            founder_names = []
            if raw_founders:
                for part in re.split(r"[;|]", raw_founders):
                    pn = part.strip()
                    if pn and pn.lower() not in {x.lower() for x in founder_names} and not is_blacklisted_entity(pn):
                        founder_names.append(pn)

            pub_email = normalize_email(r.get("Public email"))

            founders_list = [{"name": fn, "title": "Founder / Contact", "email": pub_email or ""} for fn in founder_names]

            loc_targets = (r.get("Location targets") or "").strip()
            work_mode = (r.get("Work mode targets") or "").strip()
            tech_dom = (r.get("Technology / domain") or "").strip()
            batches = (r.get("Search batches") or "").strip()
            team_size = (r.get("Reported team size") or "").strip()
            prev_roles = (r.get("Previously advertised roles") or "").strip()
            exp_req = (r.get("Experience requirements") or "").strip()
            comp_adv = (r.get("Advertised compensation") or "").strip()
            notes = (r.get("Notes") or "").strip()
            sources_str = (r.get("Sources") or "").strip()
            evidence = (r.get("Evidence / verification") or "").strip()

            # Priority tiering
            is_vip = 1 if ("pune" in (loc_targets + " " + batches).lower() and ("ai" in tech_dom.lower() or pub_email or best_rank >= 3)) else 0
            tier = 1 if (is_vip or "pune" in batches.lower() or "bengaluru" in batches.lower()) else 2
            stage = "gtm_excluded" if is_self_employer(cname, official_dom) else None
            if stage == "gtm_excluded":
                tier = 2
                is_vip = 0

            meta = {
                "search_batches": batches,
                "location_targets": loc_targets,
                "work_mode_targets": work_mode,
                "previously_advertised_roles": prev_roles,
                "experience_req": exp_req,
                "advertised_comp": comp_adv,
                "evidence_verification": evidence,
                "notes": notes,
                "sources": sources_str,
                "founder_search_url": clean_url(r.get("Founder / CTO search") or ""),
                "recruiter_search_url": clean_url(r.get("Recruiter search") or ""),
                "career_search_url": clean_url(r.get("Career search") or ""),
            }
            meta = {k: v for k, v in meta.items() if v}

            companies.append({
                "company_name": cname,
                "official_domain": official_dom or None,
                "careers_page_url": best_careers,
                "ats_provider": ats_prov,
                "ats_board_token": ats_tok,
                "sector": tech_dom or None,
                "area": "Pune" if "pune" in loc_targets.lower() else ("Bengaluru" if "bengaluru" in loc_targets.lower() else None),
                "location": loc_targets or None,
                "team_size": team_size or None,
                "founders": founders_list,
                "priority_tier": tier,
                "is_vip": is_vip,
                "stage": stage,
                "metadata": meta,
            })

            # Specific jobs from Career / job links
            specific_job_url_for_lead: str | None = None
            for cu in career_urls:
                if is_specific_job_url(cu) and not is_self_employer(cname, official_dom):
                    if not specific_job_url_for_lead:
                        specific_job_url_for_lead = cu
                    role_title = prev_roles or "AI / Software Engineer"
                    # Derive a specific role title from URL slug if prev_roles is blank
                    if not prev_roles:
                        slug_part = [p for p in urlparse(cu).path.split("/") if p][-1]
                        slug_part = re.sub(r"^\d+-", "", slug_part)
                        slug_part = re.sub(r"-[a-f0-9-]{8,}$", "", slug_part)
                        cleaned_slug = slug_part.replace("-", " ").strip().title()
                        if len(cleaned_slug) >= 4:
                            role_title = cleaned_slug
                    jobs.append({
                        "url": cu,
                        "title": role_title,
                        "company": cname,
                        "location": loc_targets or work_mode or "India / Remote",
                        "site": ats_prov or _clean_domain_token(cu) or "research_csv",
                        "strategy": "chatgpt_research_ingest",
                        "description": f"{notes} | Exp: {exp_req or '0-3 yrs'} | needs live HTTP verification".strip(" |"),
                    })

            # Leads: direct email & founder mentions (skip Revcloud)
            if not is_self_employer(cname, official_dom):
                if pub_email:
                    leads.append({
                        "contact_email": pub_email,
                        "company_name": cname,
                        "company_domain": official_dom or pub_email.split("@", 1)[1],
                        "contact_name": founder_names[0] if founder_names else f"{cname} Hiring Team",
                        "role_title": f"Hiring / Careers Contact at {cname}",
                        "contact_type": "recruiter",
                        "source_platform": "chatgpt_research_csv",
                        "source_post_url": specific_job_url_for_lead,
                        "evidence_snippet": f"Public email from AI/SDE Master CSV. {evidence}".strip(),
                        "execution_route": "DUAL_ATTACK" if specific_job_url_for_lead else "EMAIL_ONLY",
                        "priority_score": 90,
                    })
                for fn in founder_names:
                    synth = make_synthetic_email(fn, cname)
                    leads.append({
                        "contact_email": synth,
                        "company_name": cname,
                        "company_domain": official_dom or None,
                        "contact_name": fn,
                        "role_title": f"Founder / Contact at {cname}",
                        "contact_type": "decision_maker",
                        "source_platform": "chatgpt_research_csv",
                        "source_post_url": None,
                        "evidence_snippet": f"Public founder/contact listed in AI/SDE Master CSV ({loc_targets}).",
                        "execution_route": "RESEARCH_NEEDED",
                        "priority_score": 82,
                    })

    return companies, leads, jobs


def parse_chatgpt_markdown(md_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str]:
    """Parse all 58 markdown tables & citation links from ChatGPT-New chat-20261126-1609.md."""
    raw_text = md_path.read_text(encoding="utf-8", errors="replace")
    cleaned = clean_markdown_text(raw_text)
    lines = cleaned.splitlines()

    companies: list[dict[str, Any]] = []
    leads: list[dict[str, Any]] = []
    jobs: list[dict[str, Any]] = []

    # Extract tables
    tables: list[list[list[str]]] = []
    curr: list[list[str]] = []
    for line in lines:
        s = line.strip()
        if s.startswith("|"):
            cols = [c.strip() for c in s.strip("|").split("|")]
            curr.append(cols)
        else:
            if len(curr) >= 3:
                tables.append(curr)
            curr = []
    if len(curr) >= 3:
        tables.append(curr)

    for tbl in tables:
        header = [h.lower().strip() for h in tbl[0]]
        if not header or header[0] in ("platform", "column"):
            continue

        # Locate semantic column indices
        idx_map: dict[str, int] = {}
        for i, h in enumerate(header):
            if "company" in h:
                idx_map.setdefault("company", i)
            elif h in ("official website", "domain", "website"):
                idx_map.setdefault("website", i)
            elif any(k in h for k in ("career", "apply", "job link", "website / careers", "careers / website")):
                idx_map.setdefault("career", i)
            elif any(k in h for k in ("founder", "person", "public contact")):
                idx_map.setdefault("founder", i)
            elif "email" in h:
                idx_map.setdefault("email", i)
            elif any(k in h for k in ("role", "position", "opportunity")):
                idx_map.setdefault("role", i)
            elif "experience" in h:
                idx_map.setdefault("exp", i)
            elif any(k in h for k in ("focus", "specialization", "category", "product area")):
                idx_map.setdefault("sector", i)
            elif "area" in h:
                idx_map.setdefault("area", i)

        if "company" not in idx_map:
            continue

        for row in tbl[1:]:
            if all(set(c) <= set("-: ") for c in row):
                continue
            if idx_map["company"] >= len(row):
                continue
            cname = re.sub(r"\*\*([^*]+)\*\*", r"\1", row[idx_map["company"]]).strip()
            if not cname or cname.isdigit() or is_blacklisted_entity(cname):
                continue

            website_cell = row[idx_map["website"]] if "website" in idx_map and idx_map["website"] < len(row) else ""
            career_cell = row[idx_map["career"]] if "career" in idx_map and idx_map["career"] < len(row) else ""
            founder_cell = row[idx_map["founder"]] if "founder" in idx_map and idx_map["founder"] < len(row) else ""
            email_cell = row[idx_map["email"]] if "email" in idx_map and idx_map["email"] < len(row) else ""
            role_cell = row[idx_map["role"]] if "role" in idx_map and idx_map["role"] < len(row) else ""
            exp_cell = row[idx_map["exp"]] if "exp" in idx_map and idx_map["exp"] < len(row) else ""
            sector_cell = row[idx_map["sector"]] if "sector" in idx_map and idx_map["sector"] < len(row) else ""
            area_cell = row[idx_map["area"]] if "area" in idx_map and idx_map["area"] < len(row) else ""

            web_links = [u for _, u in extract_md_links_and_urls(website_cell)]
            car_links = [u for _, u in extract_md_links_and_urls(career_cell)]
            all_urls = [u for u in web_links + car_links if u and not is_blacklisted_entity("", u)]

            official_dom = None
            for u in web_links:
                d = _clean_domain_token(u)
                if d and not is_aggregator_or_ats_domain(d) and not any(sd in d for sd in SEARCH_DOMAINS):
                    official_dom = d
                    break
            if not official_dom and website_cell and "." in website_cell and " " not in website_cell.strip():
                d = _clean_domain_token(website_cell)
                if d and "." in d and not is_aggregator_or_ats_domain(d):
                    official_dom = d
            if not official_dom:
                for u in car_links:
                    d = _clean_domain_token(u)
                    if d and "." in d and not is_aggregator_or_ats_domain(d) and not any(sd in d for sd in SEARCH_DOMAINS):
                        official_dom = d
                        break

            best_careers = None
            best_rank = -1
            for u in all_urls:
                if any(sd in u.lower() for sd in SEARCH_DOMAINS) or "linkedin.com/search" in u.lower():
                    continue
                rk = careers_url_quality_rank(u)
                if rk > best_rank:
                    best_rank = rk
                    best_careers = u

            ats_prov, ats_tok = parse_ats_from_url(best_careers)
            stage = "gtm_excluded" if is_self_employer(cname, official_dom or "") else None
            founders = []
            if founder_cell and not is_blacklisted_entity(founder_cell):
                for fn in re.split(r"[;|]", founder_cell):
                    fn_clean = fn.strip()
                    if fn_clean and fn_clean.lower() != "n/a":
                        founders.append({"name": fn_clean, "title": "Founder / Contact", "email": ""})

            companies.append({
                "company_name": cname,
                "official_domain": official_dom,
                "careers_page_url": best_careers,
                "ats_provider": ats_prov,
                "ats_board_token": ats_tok,
                "sector": sector_cell or None,
                "area": area_cell or None,
                "location": None,
                "team_size": None,
                "founders": founders,
                "priority_tier": 2 if stage == "gtm_excluded" else 1,
                "is_vip": 0 if stage == "gtm_excluded" else 1,
                "stage": stage,
                "metadata": {
                    "md_role_mention": role_cell,
                    "experience_req": exp_cell,
                    "source_doc": "ChatGPT-New chat-20261126-1609.md",
                },
            })

            # Specific job URLs from MD
            specific_url = None
            for u in all_urls:
                if is_specific_job_url(u) and not is_self_employer(cname, official_dom or ""):
                    specific_url = u
                    jobs.append({
                        "url": u,
                        "title": role_cell or "AI / Software Engineer",
                        "company": cname,
                        "location": area_cell or "Remote / India",
                        "site": ats_prov or _clean_domain_token(u) or "chatgpt_md",
                        "strategy": "chatgpt_research_ingest",
                        "description": f"Exp: {exp_cell or '0-3 yrs'} | Source: ChatGPT research MD | needs live HTTP verification",
                    })

            em = normalize_email(email_cell)
            if em and not is_self_employer(cname, official_dom or ""):
                leads.append({
                    "contact_email": em,
                    "company_name": cname,
                    "company_domain": official_dom or em.split("@", 1)[1],
                    "contact_name": founders[0]["name"] if founders else f"{cname} Hiring Team",
                    "role_title": f"Application / Careers Contact at {cname}",
                    "contact_type": "recruiter",
                    "source_platform": "chatgpt_research_md",
                    "source_post_url": specific_url,
                    "evidence_snippet": "Direct application email from ChatGPT research markdown.",
                    "execution_route": "DUAL_ATTACK" if specific_url else "EMAIL_ONLY",
                    "priority_score": 90,
                })

    # Enrich from prose citation links like [Careers at WallzaOS](https://wallza.in/careers)
    for lbl, u in extract_md_links_and_urls(cleaned):
        if is_blacklisted_entity(lbl, u):
            continue
        m = re.search(r"(?:careers|about)\s+at\s+([A-Za-z0-9._ -]{2,40})$", lbl, re.IGNORECASE)
        if not m:
            m = re.search(r"^about\s+([A-Z][A-Za-z0-9._ -]{1,40})$", lbl)
        if m:
            cname = re.sub(r"[™®©]", "", m.group(1)).strip()
            if cname.lower() in ("us", "our", "me", "pune", "bengaluru", "india"):
                continue
            if not is_blacklisted_entity(cname, u):
                dom = _clean_domain_token(u)
                if dom and not is_aggregator_or_ats_domain(dom):
                    companies.append({
                        "company_name": cname,
                        "official_domain": dom,
                        "careers_page_url": u if "career" in u.lower() else None,
                        "ats_provider": None,
                        "ats_board_token": None,
                        "sector": None,
                        "area": None,
                        "location": None,
                        "team_size": None,
                        "founders": [],
                        "priority_tier": 2 if is_self_employer(cname, dom) else 1,
                        "is_vip": 0,
                        "stage": "gtm_excluded" if is_self_employer(cname, dom) else None,
                        "metadata": {"source_doc": "ChatGPT-MD-citation"},
                    })

    return companies, leads, jobs, raw_text


def run_ingestion(
    db_path: Path = DB_PATH,
    master_csv: Path = DEFAULT_MASTER_CSV,
    sources_csv: Path = DEFAULT_SOURCES_CSV,
    tracker_xlsx: Path = DEFAULT_TRACKER_XLSX,
    chatgpt_md: Path = DEFAULT_CHATGPT_MD,
    commit: bool = False,
) -> dict[str, Any]:
    """Execute idempotent zero-duplication ingestion pipeline (--dry-run or --commit)."""
    conn = get_connection(db_path)
    init_db(conn)
    run_migrations(conn)

    csv_companies, csv_leads, csv_jobs = parse_master_csv(master_csv)
    md_companies, md_leads, md_jobs, md_raw_text = parse_chatgpt_markdown(chatgpt_md)
    discovery_sources = parse_discovery_sources(sources_csv, md_raw_text)
    xlsx_parity = parse_xlsx_parity(tracker_xlsx)

    # Check XLSX parity against parsed CSV+MD companies & sources
    parsed_names_lower = {c["company_name"].strip().lower() for c in csv_companies + md_companies}
    parsed_names_norm = {normalize_company_name(c["company_name"]).lower() for c in csv_companies + md_companies}
    xlsx_missing = [
        xc
        for xc in xlsx_parity.get("companies", [])
        if xc.lower() not in parsed_names_lower and normalize_company_name(xc).lower() not in parsed_names_norm
    ]

    # Build lookup maps from existing DB career_watchlist
    existing_rows = conn.execute(
        """
        SELECT company_id, company_name, official_domain, careers_page_url,
               ats_provider, ats_board_token, priority_tier, is_vip, stage,
               sector, area, location, team_size, founders_json, hr_contacts_json,
               metadata_json
        FROM career_watchlist
        """
    ).fetchall()

    records_by_cid: dict[str, dict[str, Any]] = {}
    domain_to_cid: dict[str, str] = {}
    norm_name_to_cid: dict[str, str] = {}
    alnum_name_to_cid: dict[str, str] = {}
    exact_name_to_cid: dict[str, str] = {}

    for r in existing_rows:
        cid = r["company_id"]
        rec = dict(r)
        records_by_cid[cid] = rec
        if rec["official_domain"]:
            domain_to_cid[rec["official_domain"].lower().strip()] = cid
        cname_low = (rec["company_name"] or "").strip().lower()
        if cname_low:
            exact_name_to_cid[cname_low] = cid
            norm = normalize_company_name(cname_low)
            norm_name_to_cid[norm] = cid
            alnum = re.sub(r"[^a-z0-9]", "", norm)
            if len(alnum) >= 4:
                alnum_name_to_cid[alnum] = cid

    def find_match_cid(cname: str, dom: str | None) -> tuple[str | None, str]:
        if dom and dom.lower() in domain_to_cid:
            return domain_to_cid[dom.lower()], "domain"
        c_low = cname.strip().lower()
        if c_low in exact_name_to_cid:
            return exact_name_to_cid[c_low], "exact_name"
        c_norm = normalize_company_name(c_low)
        if c_norm and c_norm in norm_name_to_cid:
            return norm_name_to_cid[c_norm], "normalized_name"
        alias_target = EXPLICIT_COMPANY_ALIASES.get(c_low) or EXPLICIT_COMPANY_ALIASES.get(c_norm)
        if alias_target:
            if alias_target in exact_name_to_cid:
                return exact_name_to_cid[alias_target], "alias"
            alias_norm = normalize_company_name(alias_target)
            if alias_norm in norm_name_to_cid:
                return norm_name_to_cid[alias_norm], "alias"
        c_alnum = re.sub(r"[^a-z0-9]", "", c_norm)
        if len(c_alnum) >= 4 and c_alnum in alnum_name_to_cid:
            return alnum_name_to_cid[c_alnum], "normalized_name"
        return None, "new"

    matched_cids: set[str] = set()
    new_cids: set[str] = set()
    near_matches: list[tuple[str, str, float]] = []
    match_reasons: dict[str, int] = {"domain": 0, "exact_name": 0, "normalized_name": 0, "alias": 0, "new": 0}
    existing_norm_keys = list(norm_name_to_cid.keys())

    # Merge CSV first (authoritative structured dataset), then MD enrichment
    for item in csv_companies + md_companies:
        cname = item["company_name"].strip()
        dom = _clean_domain_token(item.get("official_domain")) or None
        if dom and (is_aggregator_or_ats_domain(dom) or dom in BLACKLISTED_DOMAINS):
            dom = None

        cid, reason = find_match_cid(cname, dom)
        match_reasons[reason] += 1

        if cid is None:
            # Check near matches for dry-run audit
            c_norm = normalize_company_name(cname.lower())
            if len(c_norm) >= 5:
                close = difflib.get_close_matches(c_norm, existing_norm_keys, n=1, cutoff=0.88)
                if close:
                    ratio = difflib.SequenceMatcher(None, c_norm, close[0]).ratio()
                    near_matches.append((cname, records_by_cid[norm_name_to_cid[close[0]]]["company_name"], round(ratio, 3)))

            cid = f"comp_{uuid.uuid4().hex[:10]}"
            new_cids.add(cid)
            records_by_cid[cid] = {
                "company_id": cid,
                "company_name": cname,
                "official_domain": dom,
                "careers_page_url": item.get("careers_page_url"),
                "ats_provider": item.get("ats_provider"),
                "ats_board_token": item.get("ats_board_token"),
                "priority_tier": item.get("priority_tier", 2),
                "is_vip": item.get("is_vip", 0),
                "stage": item.get("stage"),
                "sector": item.get("sector"),
                "area": item.get("area"),
                "location": item.get("location"),
                "team_size": item.get("team_size"),
                "founders_json": json.dumps(item.get("founders") or [], ensure_ascii=False) if item.get("founders") else None,
                "hr_contacts_json": None,
                "metadata_json": json.dumps(item.get("metadata") or {}, ensure_ascii=False) if item.get("metadata") else None,
                "_dirty": True,
            }
            if dom:
                domain_to_cid[dom] = cid
            exact_name_to_cid[cname.lower()] = cid
            if c_norm:
                norm_name_to_cid[c_norm] = cid
                existing_norm_keys.append(c_norm)
                c_alnum = re.sub(r"[^a-z0-9]", "", c_norm)
                if len(c_alnum) >= 4:
                    alnum_name_to_cid[c_alnum] = cid
        else:
            if cid not in new_cids:
                matched_cids.add(cid)
            rec = records_by_cid[cid]
            rec["_dirty"] = True

            # Non-destructive merge rules
            if not rec.get("official_domain") and dom:
                rec["official_domain"] = dom
                domain_to_cid[dom] = cid

            new_car = item.get("careers_page_url")
            if new_car and careers_url_quality_rank(new_car) > careers_url_quality_rank(rec.get("careers_page_url")):
                rec["careers_page_url"] = new_car

            if not rec.get("ats_provider") and item.get("ats_provider"):
                rec["ats_provider"] = item["ats_provider"]
                rec["ats_board_token"] = item.get("ats_board_token")

            # Preserve gtm_excluded unconditionally
            if rec.get("stage") == "gtm_excluded" or item.get("stage") == "gtm_excluded":
                rec["stage"] = "gtm_excluded"
                rec["priority_tier"] = 2
                rec["is_vip"] = 0
            else:
                if item.get("is_vip") == 1:
                    rec["is_vip"] = 1
                if item.get("priority_tier") == 1:
                    rec["priority_tier"] = 1

            for col in ("sector", "area", "location", "team_size"):
                if not rec.get(col) and item.get(col):
                    rec[col] = item[col]

            # Merge founders deduplicated by (name, email)
            if item.get("founders"):
                try:
                    existing_f = json.loads(rec["founders_json"]) if rec.get("founders_json") else []
                    if not isinstance(existing_f, list):
                        existing_f = []
                except Exception:
                    existing_f = []
                seen_f = {
                    (str(x.get("name") or "").strip().lower(), str(x.get("email") or "").strip().lower())
                    for x in existing_f
                    if isinstance(x, dict)
                }
                for f_item in item["founders"]:
                    fk = (f_item["name"].strip().lower(), f_item.get("email", "").strip().lower())
                    if fk not in seen_f:
                        seen_f.add(fk)
                        existing_f.append(f_item)
                rec["founders_json"] = json.dumps(existing_f, ensure_ascii=False)

            # Enrich metadata_json
            if item.get("metadata"):
                try:
                    cur_meta = json.loads(rec["metadata_json"]) if rec.get("metadata_json") else {}
                    if not isinstance(cur_meta, dict):
                        cur_meta = {}
                except Exception:
                    cur_meta = {}
                for mk, mv in item["metadata"].items():
                    if mv and mk not in cur_meta:
                        cur_meta[mk] = mv
                rec["metadata_json"] = json.dumps(cur_meta, ensure_ascii=False)

    # Deduplicate leads by lowercase email
    dedup_leads: dict[str, dict[str, Any]] = {}
    for ld in csv_leads + md_leads:
        em_key = ld["contact_email"].strip().lower()
        if em_key not in dedup_leads:
            dedup_leads[em_key] = ld
        else:
            # Prefer real email / specific source_post_url
            if ld.get("source_post_url") and not dedup_leads[em_key].get("source_post_url"):
                dedup_leads[em_key]["source_post_url"] = ld["source_post_url"]
                dedup_leads[em_key]["execution_route"] = ld["execution_route"]

    # Deduplicate jobs by canonical URL and (LOWER(company), normalized_title)
    dedup_jobs: list[dict[str, Any]] = []
    seen_job_urls: set[str] = {
        r[0].rstrip("/") for r in conn.execute("SELECT url FROM jobs").fetchall() if r[0]
    }
    seen_job_ct: set[tuple[str, str]] = {
        (r[0].strip().lower(), re.sub(r"\s+", " ", r[1].strip().lower()))
        for r in conn.execute("SELECT company, title FROM jobs WHERE company IS NOT NULL AND title IS NOT NULL").fetchall()
    }
    for jb in csv_jobs + md_jobs:
        u_norm = jb["url"].rstrip("/")
        ct_key = (jb["company"].strip().lower(), re.sub(r"\s+", " ", jb["title"].strip().lower()))
        if u_norm in seen_job_urls or ct_key in seen_job_ct:
            continue
        seen_job_urls.add(u_norm)
        seen_job_ct.add(ct_key)
        dedup_jobs.append(jb)

    now_iso = datetime.now(timezone.utc).isoformat()
    if commit:
        cur = conn.cursor()
        for rec in records_by_cid.values():
            if not rec.get("_dirty"):
                continue
            cur.execute(
                """
                INSERT INTO career_watchlist (
                    company_id, company_name, official_domain, careers_page_url,
                    ats_provider, ats_board_token, priority_tier, is_vip, stage,
                    sector, area, location, team_size, founders_json, hr_contacts_json,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(company_id) DO UPDATE SET
                    official_domain = COALESCE(career_watchlist.official_domain, excluded.official_domain),
                    careers_page_url = excluded.careers_page_url,
                    ats_provider = COALESCE(career_watchlist.ats_provider, excluded.ats_provider),
                    ats_board_token = COALESCE(career_watchlist.ats_board_token, excluded.ats_board_token),
                    priority_tier = excluded.priority_tier,
                    is_vip = excluded.is_vip,
                    stage = CASE WHEN career_watchlist.stage = 'gtm_excluded' THEN 'gtm_excluded' ELSE excluded.stage END,
                    sector = COALESCE(career_watchlist.sector, excluded.sector),
                    area = COALESCE(career_watchlist.area, excluded.area),
                    location = COALESCE(career_watchlist.location, excluded.location),
                    team_size = COALESCE(career_watchlist.team_size, excluded.team_size),
                    founders_json = COALESCE(excluded.founders_json, career_watchlist.founders_json),
                    metadata_json = COALESCE(excluded.metadata_json, career_watchlist.metadata_json)
                """,
                (
                    rec["company_id"],
                    rec["company_name"],
                    rec.get("official_domain"),
                    rec.get("careers_page_url"),
                    rec.get("ats_provider"),
                    rec.get("ats_board_token"),
                    rec.get("priority_tier", 2),
                    rec.get("is_vip", 0),
                    rec.get("stage"),
                    rec.get("sector"),
                    rec.get("area"),
                    rec.get("location"),
                    rec.get("team_size"),
                    rec.get("founders_json"),
                    rec.get("hr_contacts_json"),
                    rec.get("metadata_json"),
                ),
            )

        from applypilot.database import store_recruiter_lead
        for ld in dedup_leads.values():
            store_recruiter_lead(
                contact_email=ld["contact_email"],
                role_title=ld["role_title"],
                company_name=ld["company_name"],
                company_domain=ld["company_domain"],
                contact_name=ld["contact_name"],
                contact_type=ld["contact_type"],
                source_platform=ld["source_platform"],
                source_post_url=ld["source_post_url"],
                evidence_snippet=ld["evidence_snippet"],
                execution_route=ld["execution_route"],
                conn=conn,
            )

        for jb in dedup_jobs:
            cur.execute(
                """
                INSERT INTO jobs (url, title, company, location, site, strategy, description, state, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'discovered', ?)
                ON CONFLICT(url) DO NOTHING
                """,
                (
                    jb["url"],
                    jb["title"],
                    jb["company"],
                    jb["location"],
                    jb["site"],
                    jb["strategy"],
                    jb["description"],
                    now_iso,
                ),
            )

        for src in discovery_sources:
            cur.execute(
                """
                INSERT INTO discovery_sources (url, name, region, source_type, requires_login, scope_notes, priority_tier)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    name = COALESCE(excluded.name, discovery_sources.name),
                    region = COALESCE(excluded.region, discovery_sources.region),
                    source_type = COALESCE(excluded.source_type, discovery_sources.source_type),
                    requires_login = excluded.requires_login,
                    scope_notes = COALESCE(excluded.scope_notes, discovery_sources.scope_notes),
                    priority_tier = MIN(excluded.priority_tier, discovery_sources.priority_tier)
                """,
                (
                    src["url"],
                    src["name"],
                    src["region"],
                    src["source_type"],
                    src["requires_login"],
                    src["scope_notes"],
                    src["priority_tier"],
                ),
            )

        conn.commit()
        sync_execution_routes(conn)

    return {
        "mode": "COMMIT" if commit else "DRY_RUN",
        "csv_companies_parsed": len(csv_companies),
        "md_companies_parsed": len(md_companies),
        "companies_merged": len(matched_cids),
        "companies_net_new": len(new_cids),
        "match_reasons": match_reasons,
        "near_matches_sample": near_matches[:25],
        "near_matches_total": len(near_matches),
        "leads_prepared": len(dedup_leads),
        "jobs_prepared": len(dedup_jobs),
        "discovery_sources_prepared": len(discovery_sources),
        "xlsx_companies_count": len(xlsx_parity.get("companies", [])),
        "xlsx_missing_companies": xlsx_missing,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Pune/Bengaluru/Remote AI-SDE research datasets.")
    parser.add_argument("--commit", action="store_true", help="Commit changes to SQLite DB.")
    parser.add_argument("--dry-run", action="store_true", help="Audit collisions & aliases without writing (default).")
    parser.add_argument("--db-path", type=str, default=str(DB_PATH), help="Path to SQLite DB.")
    args = parser.parse_args()

    commit = bool(args.commit and not args.dry_run)
    res = run_ingestion(db_path=Path(args.db_path), commit=commit)
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
