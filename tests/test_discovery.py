import pytest

from src.discovery.ats_detector import ATS, detect


def test_detect_greenhouse():
    assert detect("https://boards.greenhouse.io/acme/jobs") == ATS.greenhouse


def test_detect_lever():
    assert detect("https://jobs.lever.co/acme") == ATS.lever


def test_detect_ashby():
    assert detect("https://jobs.ashbyhq.com/acme") == ATS.ashby


def test_detect_unknown():
    assert detect("https://careers.acme.com/jobs") == ATS.unknown


def test_detect_workday():
    assert detect("https://acme.myworkdayjobs.com/careers") == ATS.workday
