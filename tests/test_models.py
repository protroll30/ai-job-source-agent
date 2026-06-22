from src.models import JobLead, StageResult, StageStatus


def test_finalize_marks_partial_extraction():
    lead = JobLead(
        source_url="https://linkedin.com/jobs/1",
        company_name="Acme",
        company_website="https://acme.com",
        career_url="https://acme.com/careers",
    )
    lead.source_result = StageResult(status=StageStatus.ok)
    lead.discovery_result = StageResult(status=StageStatus.ok, method="heuristic")
    lead.extraction_result = StageResult(
        status=StageStatus.partial, error="no open position found"
    )

    lead.finalize()

    assert lead.is_partial()
    assert lead.extraction_result.status == StageStatus.partial


def test_finalize_complete_record():
    lead = JobLead(
        source_url="https://linkedin.com/jobs/1",
        company_name="Acme",
        company_website="https://acme.com",
        career_url="https://boards.greenhouse.io/acme/jobs",
        position_url="https://boards.greenhouse.io/acme/jobs/1",
    )
    lead.source_result = StageResult(status=StageStatus.ok)
    lead.discovery_result = StageResult(status=StageStatus.ok, method="heuristic")
    lead.extraction_result = StageResult(status=StageStatus.ok, method="ats_api")

    lead.finalize()

    assert lead.is_complete()
    assert lead.confidence == 0.0
