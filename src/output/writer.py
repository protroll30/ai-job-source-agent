from __future__ import annotations

import csv
import sys
from typing import IO, List

from src.models import JobLead


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
    print(f"\n--- Funnel Summary ---")
    print(f"  Input URLs : {total}")
    print(f"  Sourced    : {sourced}/{total}")
    print(f"  Discovered : {discovered}/{total}")
    print(f"  Extracted  : {extracted}/{total}")
    print(f"----------------------\n")
