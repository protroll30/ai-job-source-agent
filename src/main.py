from __future__ import annotations

import argparse
import asyncio
import os
import sys

from src.agent.browser import BrowserSession
from src.agent.llm import LLMClient
from src.config import load_config
from src.discovery.career_finder import CareerFinder
from src.extraction.position_finder import PositionFinder
from src.models import JobLead, StageResult, StageStatus
from src.output.writer import print_funnel, write_csv
from src.pipeline import Pipeline
from src.sources.linkedin.api_adapter import ProxycurlAdapter
from src.sources.linkedin.fixture_adapter import FixtureAdapter
from src.utils.cache import DiskCache
from src.utils.http import CachedHttpClient
from src.utils.rate_limit import RateLimiter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Job Source Agent")
    parser.add_argument(
        "--source",
        choices=["linkedin", "fixture", "demo"],
        default="linkedin",
        help="Input source adapter",
    )
    parser.add_argument(
        "--urls",
        nargs="*",
        help="LinkedIn job listing URLs to process (space-separated)",
    )
    parser.add_argument(
        "--urls-file",
        help="Path to a file with one LinkedIn URL per line",
    )
    parser.add_argument(
        "--output",
        help="Output CSV path (default: stdout)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable disk cache for HTTP responses",
    )
    parser.add_argument(
        "--clear-checkpoint",
        action="store_true",
        help="Delete checkpoint file before run",
    )
    return parser.parse_args()


def load_urls(args: argparse.Namespace) -> list[str]:
    if args.source == "demo":
        return ["https://www.linkedin.com/jobs/view/fixture-1"]

    urls: list[str] = []
    if args.urls:
        urls.extend(args.urls)
    if args.urls_file:
        with open(args.urls_file) as f:
            urls.extend(line.strip() for line in f if line.strip())
    if not urls:
        print("No URLs provided. Use --urls, --urls-file, or --source demo.", file=sys.stderr)
        sys.exit(1)
    return urls


def demo_lead() -> JobLead:
    """Hardcoded end-to-end record for smoke testing without network."""
    lead = JobLead(
        source_url="demo://local",
        company_name="Acme Corp",
        company_website="https://www.acme.com",
        career_url="https://boards.greenhouse.io/acme/jobs",
        position_url="https://boards.greenhouse.io/acme/jobs/12345",
    )
    lead.source_result = StageResult(status=StageStatus.ok)
    lead.discovery_result = StageResult(status=StageStatus.ok, method="heuristic")
    lead.extraction_result = StageResult(status=StageStatus.ok, method="ats_api")
    return lead.finalize()


async def main() -> None:
    args = parse_args()
    config = load_config()

    if args.output:
        config.output_path = args.output

    if args.clear_checkpoint and os.path.exists(config.checkpoint_path):
        os.remove(config.checkpoint_path)

    urls = load_urls(args)

    if args.source == "demo":
        leads = [demo_lead()]
        output_path = config.output_path if args.output else None
        write_csv(leads, path=output_path)
        print_funnel(leads)
        return

    cache = None if args.no_cache else DiskCache(config.cache_dir)
    rate_limiter = RateLimiter(config.requests_per_second)
    http = CachedHttpClient(cache=cache, rate_limiter=rate_limiter, timeout=config.page_timeout_ms // 1000)

    llm = LLMClient(api_key=config.anthropic_api_key, model=config.llm_model)

    if args.source == "fixture":
        source = FixtureAdapter()
    else:
        source = ProxycurlAdapter(api_key=config.proxycurl_api_key)

    career_finder = CareerFinder(
        llm=llm,
        http=http,
        serp_api_key=config.serp_api_key,
    )

    async with BrowserSession.managed(timeout_ms=config.page_timeout_ms) as browser:
        position_finder = PositionFinder(
            llm=llm,
            browser=browser,
            http=http,
            timeout=config.page_timeout_ms // 1000,
        )
        pipeline = Pipeline(
            source=source,
            career_finder=career_finder,
            position_finder=position_finder,
            config=config,
        )
        leads = await pipeline.run(urls)

    output_path = config.output_path if args.output else None
    write_csv(leads, path=output_path)
    print_funnel(leads)


if __name__ == "__main__":
    asyncio.run(main())
