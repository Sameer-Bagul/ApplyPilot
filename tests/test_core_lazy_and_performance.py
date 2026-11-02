"""Unit tests for ApplyPilot Core: Lazy Loader, Pre-compiled Regex, and SQLite Performance."""

import sqlite3
import pytest

from applypilot.core.lazy_loader import LazyModuleProxy, lazy_import
from applypilot.core.regex_patterns import (
    ATS_DOMAIN_PATTERNS,
    EMAIL_COMPILED_PATTERN,
    KNOWN_ATS_DOMAINS,
    OBFUSCATED_AT_PATTERN,
    OBFUSCATED_DOT_PATTERN,
)
from applypilot.database import get_connection, init_db, stream_jobs


def test_lazy_module_proxy_deferred_loading():
    # math is a standard library module
    proxy = lazy_import("math")
    assert repr(proxy) == "<LazyModuleProxy math [deferred]>"

    # Accessing attribute triggers loading
    pi_val = proxy.pi
    assert round(pi_val, 2) == 3.14
    assert repr(proxy) == "<LazyModuleProxy math [loaded]>"
    assert proxy.sqrt(16) == 4.0


def test_lazy_attribute_proxy():
    dumps_proxy = lazy_import("json", "dumps")
    res = dumps_proxy({"status": "ok"})
    assert res == '{"status": "ok"}'


def test_compiled_regex_patterns():
    # Email extraction
    test_str = "Send CV to engineer@startup.io or founder@ai.tech. Contact at support."
    matches = EMAIL_COMPILED_PATTERN.findall(test_str)
    assert "engineer@startup.io" in matches
    assert "founder@ai.tech" in matches

    # Obfuscated patterns
    obf_text = "Reach out: dev [at] company [dot] com"
    assert OBFUSCATED_AT_PATTERN.search(obf_text) is not None
    assert OBFUSCATED_DOT_PATTERN.search(obf_text) is not None

    # ATS signatures
    assert "boards.greenhouse.io" in KNOWN_ATS_DOMAINS
    m = ATS_DOMAIN_PATTERNS["greenhouse"].search("https://boards.greenhouse.io/stripe/jobs/123")
    assert m is not None and m.group(1) == "stripe"


def test_sqlite_performance_pragmas(tmp_path):
    db_file = tmp_path / "perf_test.db"
    conn = get_connection(db_file)

    # Check WAL mode
    journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert journal_mode.lower() == "wal"

    # Check synchronous NORMAL (value 1 in SQLite)
    sync_mode = conn.execute("PRAGMA synchronous").fetchone()[0]
    assert sync_mode in (1, "NORMAL", "normal")

    # Check cache size (configured to -64000 = 64MB)
    cache_size = conn.execute("PRAGMA cache_size").fetchone()[0]
    assert cache_size == -64000


def test_stream_jobs_generator(tmp_path):
    db_file = tmp_path / "stream_test.db"
    conn = init_db(db_file)

    # Insert 10 test rows
    for i in range(10):
        conn.execute(
            "INSERT INTO jobs (url, title, company, site, discovered_at) VALUES (?, ?, ?, ?, ?)",
            (f"https://example.com/job/{i}", f"Software Engineer {i}", "Acme Corp", "test", "2026-11-02"),
        )
    conn.commit()

    # Stream in batches of 3
    streamed = list(stream_jobs(conn=conn, batch_size=3))
    assert len(streamed) == 10
    assert streamed[0]["title"] == "Software Engineer 0"
    assert streamed[9]["title"] == "Software Engineer 9"
