from __future__ import annotations

import argparse
import asyncio
import sys

from src.agent.browser import BrowserSession
from src.agent.llm import LLMClient
from src.config import load_config
from src.discovery.career_finder import CareerFinder
from src.extraction.position_finder import PositionFinder
from src.output.writer import print_funnel, write_csv
from src.pipeline import Pipeline
from src.sources.linkedin.api_adapter import ProxycurlAdapter
from src.sources.linkedin.fixture_adapter import FixtureAdapter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Job Source Agent")
    parser.add_argument(
        "--source",
        choices=["linkedin", "fixture"],
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
    return parser.parse_args()


def load_urls(args: argparse.Namespace) -> list[str]:
    urls: list[str] = []
    if args.urls:
        urls.extend(args.urls)
    if args.urls_file:
        with open(args.urls_file) as f:
            urls.extend(line.strip() for line in f if line.strip())
    if not urls:
        print("No URLs provided. Use --urls or --urls-file.", file=sys.stderr)
        sys.exit(1)
    return urls


async def main() -> None:
    args = parse_args()
    config = load_config()

    if args.output:
        config.output_path = args.output

    urls = load_urls(args)

    llm = LLMClient(api_key=config.anthropic_api_key, model=config.llm_model)

    if args.source == "fixture":
        source = FixtureAdapter()
    else:
        source = ProxycurlAdapter(api_key=config.proxycurl_api_key)

    career_finder = CareerFinder(
        llm=llm,
        serp_api_key=config.serp_api_key,
        timeout=config.page_timeout_ms // 1000,
    )

    async with BrowserSession.managed(timeout_ms=config.page_timeout_ms) as browser:
        position_finder = PositionFinder(
            llm=llm,
            browser=browser,
            timeout=config.page_timeout_ms // 1000,
        )
        pipeline = Pipeline(
            source=source,
            career_finder=career_finder,
            position_finder=position_finder,
            config=config,
        )
        leads = await pipeline.run(urls)

    output_path = config.output_path if config.output_path != "results.csv" else None
    write_csv(leads, path=output_path)
    print_funnel(leads)


if __name__ == "__main__":
    asyncio.run(main())
