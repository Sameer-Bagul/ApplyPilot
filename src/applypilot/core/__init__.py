"""ApplyPilot Core Module.

Contains high-performance primitives:
- Transparent PEP 810 / PEP 562 Lazy Import Proxies
- High-throughput Pre-compiled Regex Registry
- Database Engine Tuning Primitives
"""

from __future__ import annotations

from applypilot.core.lazy_loader import LazyModuleProxy, lazy_import
from applypilot.core.regex_patterns import (
    ATS_DOMAIN_PATTERNS,
    EMAIL_COMPILED_PATTERN,
    OBFUSCATED_AT_PATTERN,
    OBFUSCATED_DOT_PATTERN,
    PHONE_COMPILED_PATTERN,
    URL_COMPILED_PATTERN,
)

__all__ = [
    "LazyModuleProxy",
    "lazy_import",
    "EMAIL_COMPILED_PATTERN",
    "PHONE_COMPILED_PATTERN",
    "URL_COMPILED_PATTERN",
    "OBFUSCATED_AT_PATTERN",
    "OBFUSCATED_DOT_PATTERN",
    "ATS_DOMAIN_PATTERNS",
]
