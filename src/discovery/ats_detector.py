from __future__ import annotations

from enum import Enum
from urllib.parse import urlparse


class ATS(str, Enum):
    greenhouse = "greenhouse"
    lever = "lever"
    ashby = "ashby"
    workday = "workday"
    smartrecruiters = "smartrecruiters"
    recruitee = "recruitee"
    unknown = "unknown"


# Hostname fragments that identify each ATS in a career page URL.
_ATS_SIGNALS: list[tuple[str, ATS]] = [
    ("greenhouse.io", ATS.greenhouse),
    ("lever.co", ATS.lever),
    ("ashbyhq.com", ATS.ashby),
    ("myworkdayjobs.com", ATS.workday),
    ("smartrecruiters.com", ATS.smartrecruiters),
    ("recruitee.com", ATS.recruitee),
]


def detect(url: str) -> ATS:
    host = urlparse(url).netloc.lower()
    for fragment, ats in _ATS_SIGNALS:
        if fragment in host:
            return ats
    return ATS.unknown
