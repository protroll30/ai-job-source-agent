from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # LinkedIn / scraper API
    proxycurl_api_key: str = field(default_factory=lambda: os.environ.get("PROXYCURL_API_KEY", ""))

    # Search engine fallback
    serp_api_key: str = field(default_factory=lambda: os.environ.get("SERP_API_KEY", ""))

    # Claude API
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    llm_model: str = "claude-sonnet-4-6"

    # Orchestration
    concurrency: int = int(os.environ.get("CONCURRENCY", "5"))
    page_timeout_ms: int = 30_000  # CLAUDE.md: strict 30s per page
    requests_per_second: float = float(os.environ.get("RPS", "2.0"))

    # I/O
    output_path: str = os.environ.get("OUTPUT_PATH", "results.csv")
    cache_dir: str = os.environ.get("CACHE_DIR", ".cache")
    checkpoint_path: str = os.environ.get("CHECKPOINT_PATH", ".checkpoint.json")


def load_config() -> Config:
    return Config()
