from __future__ import annotations

from abc import ABC, abstractmethod

from src.models import JobLead


class LinkedInSource(ABC):
    @abstractmethod
    async def fetch(self, listing_url: str) -> JobLead:
        """Extract company name and website from a LinkedIn job listing URL."""
        ...
