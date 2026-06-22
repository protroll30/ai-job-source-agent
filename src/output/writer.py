from __future__ import annotations

import csv
import sys
from typing import IO, List

from src.models import JobLead, StageStatus


HEADER = ["company_name", "career_url", "position_url"]


def write_csv(leads: List[JobLead], path: str | None = None) -> None:
    out: IO = open(path, "w", newline="", encoding="utf-8") if path else sys.stdout
    try:
        writer = csv.writer(out)
        writer.writerow(HEADER)
        for lead in leads:
            writer.writerow([
                lead.company_name or "",
                lead.career_url or "",
                lead.position_url or "",
            ])
    finally:
        if path:
            out.close()


def print_funnel(leads: List[JobLead]) -> None:
    total = len(leads)
    sourced = sum(1 for l in leads if l.company_name)
    discovered = sum(1 for l in leads if l.career_url)
    extracted = sum(1 for l in leads if l.position_url)
    complete = sum(1 for l in leads if l.is_complete())
    partial = sum(1 for l in leads if l.is_partial())

    source_ok = sum(1 for l in leads if l.source_result.status == StageStatus.ok)
    discovery_ok = sum(1 for l in leads if l.discovery_result.status == StageStatus.ok)
    extraction_ok = sum(1 for l in leads if l.extraction_result.status == StageStatus.ok)
    extraction_partial = sum(
        1 for l in leads if l.extraction_result.status == StageStatus.partial
    )

    print("\n--- Funnel Summary ---")
    print(f"  Input URLs       : {total}")
    print(f"  Sourced          : {sourced}/{total}  (stage ok: {source_ok})")
    print(f"  Discovered       : {discovered}/{total}  (stage ok: {discovery_ok})")
    print(f"  Extracted        : {extracted}/{total}  (stage ok: {extraction_ok})")
    print(f"  Partial results  : {partial}")
    print(f"  Complete records : {complete}/{total}")
    if extraction_partial:
        print(f"  No open position : {extraction_partial} (career page found)")
    print("----------------------\n")
