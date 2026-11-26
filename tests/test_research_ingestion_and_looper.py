"""Unit & integration tests for Pune/Bengaluru/Remote research ingestion, Phase 0 migrations, and looper fixes."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from applypilot.database import (  # noqa: E402
    get_connection,
    init_db,
    store_recruiter_lead,
    sync_execution_routes,
    upsert_career_watchlist,
)
from applypilot.learning.migrations import (  # noqa: E402
    is_aggregator_or_ats_domain,
    run_migrations,
    v4_research_dedup_and_sources,
)
from ingest_pune_blr_remote_research import (  # noqa: E402
    DEFAULT_CHATGPT_MD,
    DEFAULT_MASTER_CSV,
    DEFAULT_SOURCES_CSV,
    DEFAULT_TRACKER_XLSX,
    clean_markdown_text,
    clean_url,
    is_blacklisted_entity,
    normalize_email,
    parse_ats_from_url,
    parse_chatgpt_markdown,
    parse_discovery_sources,
    parse_master_csv,
    parse_xlsx_parity,
    run_ingestion,
)
from run_all_companies_looper import (  # noqa: E402
    DATA_DIR,
    crawl_custom_careers_page,
    is_ai_sde_role,
    process_single_company,
    resolve_ats_from_url,
)
from crawl_discovery_sources import (  # noqa: E402
    _infer_company_name,
    _resolve_job_title,
    crawl_discovery_sources,
)


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    conn = get_connection(db_path)
    init_db(conn)
    run_migrations(conn)
    yield db_path, conn
    conn.close()
    for ext in ("", "-wal", "-shm"):
        p = Path(str(db_path) + ext)
        if p.exists():
            p.unlink()


def test_markdown_and_email_normalization():
    raw = r"[\@test](https://example.com/careers?utm_source=chatgpt.com&foo=1) \ue200entity\ue202[\"Foo\"]\ue201 careers\@vobiz.ai."
    # Simulate actual unicode private-use chars
    raw_u = "careers\\@vobiz.ai. \ue200entity\ue202[\"Foo\"]\ue201"
    cleaned = clean_markdown_text(raw_u)
    assert "\ue200" not in cleaned
    assert "careers@vobiz.ai." in cleaned
    assert normalize_email(cleaned) == "careers@vobiz.ai"
    assert clean_url("https://example.com/careers?utm_source=chatgpt.com&role=ai") == "https://example.com/careers?role=ai"
    assert clean_url("https://example.com/careers/?utm_source=chatgpt.com") == "https://example.com/careers/"


def test_blacklisting_and_aggregator_rejection():
    assert is_blacklisted_entity("Sameer Bagul", "https://in.linkedin.com/in/sameer-bagul") is True
    assert is_blacklisted_entity("Random", "https://chatgpt.com/c/123") is True
    assert is_blacklisted_entity("Random", "https://chatgptexporter.com/") is True
    assert is_aggregator_or_ats_domain("wellfound.com") is True
    assert is_aggregator_or_ats_domain("himalayas.app") is True
    assert is_aggregator_or_ats_domain("apply.workable.com") is True
    assert is_aggregator_or_ats_domain("wednesday.zohorecruit.in") is True
    assert is_aggregator_or_ats_domain("apptware.com") is False


def test_parse_all_four_research_files_cleanly():
    csv_cos, csv_leads, csv_jobs = parse_master_csv(DEFAULT_MASTER_CSV)
    assert len(csv_cos) == 917
    assert any(l["contact_email"] == "careers@vobiz.ai" for l in csv_leads)

    md_cos, md_leads, md_jobs, md_raw = parse_chatgpt_markdown(DEFAULT_CHATGPT_MD)
    assert len(md_cos) > 800
    assert not any("sameer bagul" in c["company_name"].lower() for c in md_cos)
    assert not any("chatgpt" in (c.get("official_domain") or "") for c in md_cos)
    assert len(md_jobs) >= 8

    sources = parse_discovery_sources(DEFAULT_SOURCES_CSV, md_raw)
    assert len(sources) >= 50
    urls = {s["url"] for s in sources}
    assert any("aipune.org" in u for u in urls)
    assert any("builtinbengaluru.in" in u for u in urls)
    assert any("awesome-ai-startups-hiring" in u for u in urls)

    xlsx = parse_xlsx_parity(DEFAULT_TRACKER_XLSX)
    assert xlsx["exists"] is True
    assert len(xlsx["companies"]) == 142
    csv_names_low = {c["company_name"].strip().lower() for c in csv_cos}
    missing = [xc for xc in xlsx["companies"] if xc.lower() not in csv_names_low]
    assert missing == []


def test_phase0_migration_and_non_destructive_merge(temp_db):
    db_path, conn = temp_db

    # Seed duplicate companies, NULL company_id, aggregator official_domain, and gtm_excluded company
    conn.execute(
        "INSERT INTO career_watchlist (company_id, company_name, official_domain, priority_tier, is_vip, stage) VALUES (?, ?, ?, ?, ?, ?)",
        ("comp_meta1", "MetaMorphoSys Technologies", "metamorphosystech.com", 2, 0, None),
    )
    conn.execute(
        "INSERT INTO career_watchlist (company_id, company_name, official_domain, priority_tier, is_vip, stage) VALUES (?, ?, ?, ?, ?, ?)",
        (None, " CrowdStrike ", None, 2, 0, None),
    )
    conn.execute(
        "INSERT INTO career_watchlist (company_id, company_name, official_domain, priority_tier, is_vip, stage) VALUES (?, ?, ?, ?, ?, ?)",
        ("comp_cs1", "CrowdStrike", None, 1, 1, None),
    )
    conn.execute(
        "INSERT INTO career_watchlist (company_id, company_name, official_domain, priority_tier, is_vip, stage) VALUES (?, ?, ?, ?, ?, ?)",
        ("comp_wf1", "WellfoundTest", "wellfound.com", 2, 0, None),
    )
    conn.execute(
        "INSERT INTO career_watchlist (company_id, company_name, official_domain, priority_tier, is_vip, stage) VALUES (?, ?, ?, ?, ?, ?)",
        ("comp_rev1", "Revcloud", "revcloud.com", 2, 0, "gtm_excluded"),
    )
    # Seed duplicate recruiter_leads emails (drop index temporarily to simulate legacy pre-v4 DB)
    conn.execute("DROP INDEX IF EXISTS idx_leads_unique_email")
    conn.execute(
        "INSERT INTO recruiter_leads (lead_id, company_name, role_title, contact_email, outreach_status) VALUES (?, ?, ?, ?, ?)",
        ("lead_a", "Acme", "CEO", "test@acme.com", "queued"),
    )
    conn.execute(
        "INSERT INTO recruiter_leads (lead_id, company_name, role_title, contact_email, outreach_status) VALUES (?, ?, ?, ?, ?)",
        ("lead_b", "Acme", "CTO", "TEST@acme.com", "drafted"),
    )
    conn.commit()

    stats = v4_research_dedup_and_sources(conn)
    assert stats["watchlist_name_groups_merged"] == 1
    assert stats["agg_domains_stripped"] >= 1
    assert stats["leads_dups_deleted"] == 1
    assert conn.execute("SELECT COUNT(*) FROM career_watchlist WHERE company_id IS NULL").fetchone()[0] == 0
    wf_row = conn.execute("SELECT official_domain, careers_page_url FROM career_watchlist WHERE company_id = 'comp_wf1'").fetchone()
    assert wf_row["official_domain"] is None
    assert wf_row["careers_page_url"] == "https://wellfound.com"

    # Run full ingestion commit on temp DB
    res = run_ingestion(db_path=db_path, commit=True)
    assert res["xlsx_missing_companies"] == []
    assert res["companies_net_new"] > 500

    # Revcloud MUST stay gtm_excluded and tier 2
    rev = conn.execute("SELECT stage, priority_tier, is_vip FROM career_watchlist WHERE LOWER(company_name) = 'revcloud'").fetchone()
    assert rev["stage"] == "gtm_excluded"
    assert rev["priority_tier"] == 2
    assert rev["is_vip"] == 0

    # Sameer Bagul & chatgpt.com MUST NOT be ingested
    assert conn.execute("SELECT COUNT(*) FROM career_watchlist WHERE LOWER(company_name) LIKE '%sameer bagul%'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM career_watchlist WHERE LOWER(official_domain) LIKE '%chatgpt%'").fetchone()[0] == 0

    # Zero duplicate company names, domains, or lead emails
    assert conn.execute("SELECT COUNT(*) FROM (SELECT LOWER(TRIM(company_name)), COUNT(*) c FROM career_watchlist GROUP BY 1 HAVING c > 1)").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM (SELECT LOWER(official_domain), COUNT(*) c FROM career_watchlist WHERE official_domain IS NOT NULL AND official_domain != '' GROUP BY 1 HAVING c > 1)").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM (SELECT LOWER(contact_email), COUNT(*) c FROM recruiter_leads WHERE contact_email IS NOT NULL GROUP BY 1 HAVING c > 1)").fetchone()[0] == 0

    # sync_execution_routes must NOT create /careers index job rows
    assert conn.execute("SELECT COUNT(*) FROM jobs WHERE url LIKE '%/careers%' AND strategy = 'recruiter_email_discovery'").fetchone()[0] == 0

    # Idempotency check
    res2 = run_ingestion(db_path=db_path, commit=False)
    assert res2["companies_net_new"] == 0
    assert res2["jobs_prepared"] == 0


def test_sync_execution_routes_rejects_careers_index_and_matches_case_insensitive(temp_db):
    _, conn = temp_db
    conn.execute(
        "INSERT INTO jobs (url, title, company, execution_route, state) VALUES (?, ?, ?, ?, ?)",
        ("https://example.com/jobs/123", "AI Engineer", "acme corp", "PORTAL_ONLY", "discovered"),
    )
    store_recruiter_lead(
        contact_email="jobs@acmecorp.com",
        role_title="Recruiter at Acme Corp",
        company_name="ACME CORP",
        source_platform="social_discovery",
        source_post_url="https://acmecorp.com/careers",
        execution_route="EMAIL_ONLY",
        conn=conn,
    )
    sync_execution_routes(conn)

    # Case-insensitive upgrade to DUAL_ATTACK
    route = conn.execute("SELECT execution_route FROM jobs WHERE url = 'https://example.com/jobs/123'").fetchone()[0]
    assert route == "DUAL_ATTACK"

    # Must NOT materialize /careers as a job URL
    assert conn.execute("SELECT COUNT(*) FROM jobs WHERE url = 'https://acmecorp.com/careers'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM jobs WHERE url LIKE 'mailto:jobs@acmecorp.com%'").fetchone()[0] == 1


def test_looper_fixes_lead_storage_no_blind_com_and_indian_ats(temp_db):
    _, conn = temp_db

    # 1. Indian ATS detection
    assert resolve_ats_from_url("https://wednesday.zohorecruit.in/jobs/Careers/123") == ("zohorecruit", "wednesday")
    assert resolve_ats_from_url("https://bolt.keka.com/careers/161979") == ("keka", "bolt")
    assert resolve_ats_from_url("https://foo.freshteam.com/jobs") == ("freshteam", "foo")
    assert resolve_ats_from_url("https://bar.param.ai/jobs") == ("param", "bar")
    assert resolve_ats_from_url("https://jobs.jobvite.com/careers/saama/search") == ("jobvite", "saama")
    assert parse_ats_from_url("https://wednesday.zohorecruit.in/jobs/Careers") == ("zohorecruit", "wednesday")

    # 2. gtm_excluded skipped immediately
    conn.execute(
        "INSERT INTO career_watchlist (company_id, company_name, official_domain, stage) VALUES (?, ?, ?, ?)",
        ("comp_rev", "Revcloud", "revcloud.com", "gtm_excluded"),
    )
    res_excl = process_single_company(
        {"company_id": "comp_rev", "company_name": "Revcloud", "official_domain": "revcloud.com", "stage": "gtm_excluded"},
        conn=conn,
    )
    assert res_excl.get("skipped") == "gtm_excluded"

    # 3. No blind {slug}.com guessing when domainless and resolve_missing=False
    conn.execute(
        "INSERT INTO career_watchlist (company_id, company_name, official_domain) VALUES (?, ?, ?)",
        ("comp_nodom", "Mystery Startup XYZ", None),
    )
    res_nodom = process_single_company(
        {"company_id": "comp_nodom", "company_name": "Mystery Startup XYZ", "official_domain": None, "sector": "Retail"},
        conn=conn,
        resolve_missing=False,
    )
    assert res_nodom["domain"] is None
    assert conn.execute("SELECT official_domain FROM career_watchlist WHERE company_id = 'comp_nodom'").fetchone()[0] is None

    # 4. Fixed store_recruiter_lead keyword-args & custom /careers page crawling with mock transport
    html_body = """
    <html><head><title>ValidStartup AI Careers</title></head><body>
      <a href="/careers/applied-ai-engineer">Applied AI Engineer</a>
      <a href="mailto:recruiting@validstartup.ai">Email Us</a>
    </body></html>
    """
    def _mock_handler(req: httpx.Request) -> httpx.Response:
        if "validstartup.ai" in req.url.host:
            return httpx.Response(200, text=html_body)
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(_mock_handler)
    with httpx.Client(transport=transport) as mock_client:
        jobs_found, emails_found, ats_u = crawl_custom_careers_page("https://validstartup.ai/careers", "ValidStartup AI", client=mock_client)
        assert len(jobs_found) == 1
        assert jobs_found[0]["url"] == "https://validstartup.ai/careers/applied-ai-engineer"
        assert emails_found == ["recruiting@validstartup.ai"]
        assert ats_u is None

        conn.execute(
            "INSERT INTO career_watchlist (company_id, company_name, official_domain, careers_page_url, sector) VALUES (?, ?, ?, ?, ?)",
            ("comp_val", "ValidStartup AI", "validstartup.ai", "https://validstartup.ai/careers", "AI"),
        )
        with patch("run_all_companies_looper.get_cached_mx", return_value=(True, "google_workspace")):
            res_ok = process_single_company(
                {
                    "company_id": "comp_val",
                    "company_name": "ValidStartup AI",
                    "official_domain": "validstartup.ai",
                    "careers_page_url": "https://validstartup.ai/careers",
                    "sector": "AI",
                },
                client=mock_client,
                conn=conn,
            )
    # 5 MX standard prefixes + 1 distinct scraped careers email = 6 leads stored cleanly without TypeError!
    assert res_ok["emails_added"] == 6
    assert res_ok["new_jobs_stored"] == 1
    assert conn.execute("SELECT COUNT(*) FROM recruiter_leads WHERE company_name = 'ValidStartup AI'").fetchone()[0] == 6
    assert conn.execute("SELECT execution_route FROM jobs WHERE company = 'ValidStartup AI'").fetchone()[0] == "DUAL_ATTACK"


def test_role_filter_and_upsert_domain_conflict_safety(temp_db):
    _, conn = temp_db

    # 1. Word-bounded AI/SDE title filter must reject Legal/Accounting/Sales despite boilerplate descriptions
    assert is_ai_sde_role("Litigation Paralegal", "At Coinbase our available AI platform scales globally") is False
    assert is_ai_sde_role("Accounting Intern", "We build software and data infrastructure") is False
    assert is_ai_sde_role("Principal Recruiter", "Hiring AI and ML engineers") is False
    assert is_ai_sde_role("Forward Deployed Engineer, Finance", "") is True
    assert is_ai_sde_role("Applied AI Engineer", "") is True
    assert is_ai_sde_role("SDE-1", "") is True

    # 2. upsert_career_watchlist must never crash with IntegrityError on domain conflict
    cid1 = upsert_career_watchlist(company_name="Parent Corp", official_domain="parentcorp.com", conn=conn)
    cid2 = upsert_career_watchlist(company_name="Subsidiary Corp", official_domain="parentcorp.com", company_id="comp_sub_123", conn=conn)
    assert cid1 != cid2
    row2 = conn.execute("SELECT official_domain FROM career_watchlist WHERE company_id = ?", (cid2,)).fetchone()
    assert row2["official_domain"] is None

    # 3. Looper DATA_DIR is repo-relative (not hardcoded user home path)
    assert DATA_DIR == PROJECT_ROOT / "data-we-can-use"


def test_discovery_source_crawler_company_title_and_pollution_guards(temp_db):
    db_path, conn = temp_db
    conn.execute(
        "INSERT INTO discovery_sources (url, name, region, source_type, requires_login, priority_tier) VALUES (?, ?, ?, ?, ?, ?)",
        ("https://example-dir.in/list", "Example Dir", "Bengaluru", "directory", 0, 1),
    )
    conn.commit()

    html_page = """
    <html><body>
      <a href="https://www.ycombinator.com/companies/waybill/jobs/l28KKVa-founding-engineer">Apply →</a>
      <a href="https://www.ycombinator.com/companies/aiprise/jobs/cu6W9ZM-product-designer-ii">Apply →</a>
      <a href="https://www.sarvam.ai/careers/jobs/730c1766-ad62-4d5d-aa75-b5b0e03409aa">Apply →</a>
      <a href="https://www.turing.com/jobs/remote-react-js-developer">https://www.turing.com/jobs/remote-react-js-developer</a>
      <a href="https://jobs.ashbyhq.com/skylo/908a159a-1178-4c72-968d-373cdf96f35b">Principal Software Engineer, Backend</a>
      <a href="https://topmate.io/resume-templates">Premium Resume Templates</a>
      <a href="https://en.wikipedia.org/wiki/List_of_countries">rich countries</a>
      <a href="https://realstartup.ai/careers">RealStartup AI</a>
    </body></html>
    """

    def _mock_handler(req: httpx.Request) -> httpx.Response:
        if "example-dir.in" in req.url.host:
            return httpx.Response(200, text=html_page)
        return httpx.Response(404, text="Not Found")

    with patch("crawl_discovery_sources.httpx.Client", return_value=httpx.Client(transport=httpx.MockTransport(_mock_handler))):
        res = crawl_discovery_sources(db_path=db_path, limit=10, global_remote_cap=50)

    assert res["companies_added"] == 1
    assert res["jobs_added"] == 2

    # Verify RealStartup AI added, polluted hosts/prose skipped
    cos = [r["company_name"] for r in conn.execute("SELECT company_name FROM career_watchlist").fetchall()]
    assert cos == ["RealStartup AI"]

    # Verify every stored job has populated company & clean title (no 'Apply →', no turing, no aiprise designer)
    jobs = conn.execute("SELECT url, title, company FROM jobs ORDER BY company").fetchall()
    assert len(jobs) == 2
    assert {(j["company"], j["title"]) for j in jobs} == {
        ("Skylo", "Principal Software Engineer, Backend"),
        ("Waybill", "Founding Engineer"),
    }
