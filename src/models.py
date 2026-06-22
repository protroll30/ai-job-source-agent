from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, HttpUrl


class StageStatus(str, Enum):
    ok = "ok"
    partial = "partial"
    failed = "failed"
    skipped = "skipped"


class DiscoveryMethod(str, Enum):
    heuristic = "heuristic"
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
    confidence: float = 0.0

    source_result: StageResult = StageResult(status=StageStatus.skipped)
    discovery_result: StageResult = StageResult(status=StageStatus.skipped)
    extraction_result: StageResult = StageResult(status=StageStatus.skipped)

    def is_complete(self) -> bool:
        return all([self.company_name, self.career_url, self.position_url])

    def to_csv_row(self) -> str:
        return f"{self.company_name or ''},{self.career_url or ''},{self.position_url or ''}"
