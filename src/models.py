from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class StageStatus(str, Enum):
    ok = "ok"
    partial = "partial"
    failed = "failed"
    skipped = "skipped"


class DiscoveryMethod(str, Enum):
    heuristic = "heuristic"
    sitemap = "sitemap"
    llm = "llm"
    search = "search"


class ExtractionMethod(str, Enum):
    ats_api = "ats_api"
    dom = "dom"
    llm = "llm"


class StageResult(BaseModel):
    status: StageStatus
    method: Optional[str] = None
    error: Optional[str] = None


class JobLead(BaseModel):
    source_url: str
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    career_url: Optional[str] = None
    position_url: Optional[str] = None
    # TODO(confidence): define scoring formula in ARCHITECTURE.md §Data model, then
    # implement in finalize() — weights should reflect stage status + method provenance.
    confidence: float = 0.0
    error: Optional[str] = None

    source_result: StageResult = StageResult(status=StageStatus.skipped)
    discovery_result: StageResult = StageResult(status=StageStatus.skipped)
    extraction_result: StageResult = StageResult(status=StageStatus.skipped)

    def is_complete(self) -> bool:
        return all([self.company_name, self.career_url, self.position_url])

    def is_partial(self) -> bool:
        return bool(self.company_name or self.career_url) and not self.is_complete()

    def to_csv_row(self) -> str:
        return f"{self.company_name or ''},{self.career_url or ''},{self.position_url or ''}"

    def finalize(self) -> "JobLead":
        """Normalize stage statuses after pipeline run."""
        if self.source_result.status not in (StageStatus.skipped, StageStatus.failed):
            pass
        elif self.company_name and self.company_website:
            self.source_result = StageResult(status=StageStatus.ok)
        elif self.company_name or self.company_website:
            self.source_result = StageResult(
                status=StageStatus.partial,
                error=self.source_result.error or "incomplete company data",
            )

        if self.discovery_result.status == StageStatus.failed and self.career_url:
            self.discovery_result = StageResult(status=StageStatus.ok)

        if (
            self.extraction_result.status == StageStatus.failed
            and self.career_url
            and not self.position_url
        ):
            self.extraction_result = StageResult(
                status=StageStatus.partial,
                error=self.extraction_result.error or "no open position found",
            )

        if not self.error:
            for result in (self.source_result, self.discovery_result, self.extraction_result):
                if result.status == StageStatus.failed and result.error:
                    self.error = result.error
                    break
        return self
