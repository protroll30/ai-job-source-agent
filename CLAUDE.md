Project Overview
Jobnova AI Job Source Agent is a specialized automation pipeline designed to extract high-fidelity hiring signals from LinkedIn and company web domains. The agent processes inputs through a three-stage sequential pipeline to locate verified company details, career homepages, and live job application endpoints.

Core Pipeline Commands
Environment Setup: pip install -r requirements.txt

Execute Agent Pipeline: python src/main.py --source linkedin

Run Suite Verification: pytest tests/

Linting and Formatting: black src/ && ruff check src/

System Architecture Guidelines
Input Stage (LinkedIn Crawler): Intercept company names and base website domains from seed LinkedIn job listing URLs. Use third-party scraper APIs where necessary to bypass rate limits or CAPTCHAs, ensuring payload payloads are normalized into uniform JSON dictionaries.

Navigation Stage (Web Agent Archetype): Initialize a headless browser session via Playwright. Navigate directly to the discovered base company domain and execute semantic link matching to identify the primary career or jobs portal link.

Extraction Stage (Deep Link Discovery): Scan the target career page layout to isolate at least one valid, active opening position URL. Avoid placeholder anchors or generic registration forms; prioritize absolute URLs referencing actual job requisitions.

Required Output Format
All successful runs must serialize data to standard output or a designated CSV using the exact format sequence below:
company name,career page URL,open position's URL

Implementation Constraints
Strict Fallbacks: If a career page link is missing from the main navigation menu, the agent must fall back to programmatic search query execution via a search engine API targeting site:companywebsite.com "careers" OR "jobs".

Literal Schema Enforcement: Do not guess, auto-correct, or assume typos within target company domains or source listing fields. If an extraction boundary fails, log the precise exception state and proceed to the next record.

Session Resiliency: Enforce a strict timeout threshold of 30 seconds per page navigation event to prevent blocking loops on unresponsive target servers.

Key Integration Practices
To optimize how Claude interacts with this specific codebase during development, you can save the markdown block above directly into the root directory of your project as CLAUDE.md. This gives the agent immediate, persistent instructions regarding your formatting requirements, processing architecture, and execution commands every time a new terminal session begins.
