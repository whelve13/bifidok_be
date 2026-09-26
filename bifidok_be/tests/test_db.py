import os
import sys
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure bifidok_be is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
pkg_dir = os.path.abspath(os.path.join(current_dir, ".."))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from db.schema import (
    Base,
    Company,
    ServiceOffering,
    SignalRule,
    SignalEvaluation,
    LeadScore,
    MCPApiKey,
    SignalWeightType,
)
from db.session import get_db, create_resilient_engine, DEFAULT_SQLITE_URL
from db.repository import (
    upsert_company,
    upsert_signal_evaluation,
    upsert_lead_score,
    get_leads_by_service,
    upsert_service_offering,
    upsert_signal_rule,
    create_mcp_api_key,
    get_mcp_api_key,
)


@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_schema_creation(db_session):
    # Verify tables can be queried without error
    assert db_session.query(Company).count() == 0
    assert db_session.query(ServiceOffering).count() == 0
    assert db_session.query(SignalRule).count() == 0
    assert db_session.query(SignalEvaluation).count() == 0
    assert db_session.query(LeadScore).count() == 0
    assert db_session.query(MCPApiKey).count() == 0


def test_upsert_company(db_session):
    # Insert new company
    data = {
        "name": "DHL Group",
        "domain": "dhl.com",
        "industry": "Logistics",
        "geography": "DE",
        "employee_count": 590000,
    }
    company = upsert_company(db_session, data)
    assert company.id is not None
    assert company.name == "DHL Group"
    assert company.domain == "dhl.com"
    assert company.employee_count == 590000

    # Upsert existing company with updated headcount and name
    update_data = {
        "domain": "dhl.com",
        "name": "DHL Supply Chain Group",
        "employee_count": 600000,
    }
    updated_company = upsert_company(db_session, update_data)
    assert updated_company.id == company.id
    assert updated_company.name == "DHL Supply Chain Group"
    assert updated_company.employee_count == 600000
    assert db_session.query(Company).count() == 1


def test_upsert_signal_evaluation_budget_discard(db_session):
    company = upsert_company(db_session, {"name": "Test Co", "domain": "test.com"})
    offering = upsert_service_offering(db_session, {"name": "Agentic Automation"})
    rule = upsert_signal_rule(db_session, {
        "service_id": offering.id,
        "question": "Is the company automating?",
        "weight": "HIGH"
    })

    # Discard case 1: detected is False
    res1 = upsert_signal_evaluation(db_session, {
        "company_id": company.id,
        "rule_id": rule.id,
        "source_url": "https://test.com/news",
        "detected": False,
        "confidence": 0.95,
        "evidence_quote": "No automation planned",
        "reasoning": "Explicit denial"
    })
    assert res1 is None
    assert db_session.query(SignalEvaluation).count() == 0

    # Discard case 2: confidence < 0.50
    res2 = upsert_signal_evaluation(db_session, {
        "company_id": company.id,
        "rule_id": rule.id,
        "source_url": "https://test.com/news",
        "detected": True,
        "confidence": 0.49,
        "evidence_quote": "Maybe automation",
        "reasoning": "Low confidence"
    })
    assert res2 is None
    assert db_session.query(SignalEvaluation).count() == 0


def test_upsert_signal_evaluation_truncation_and_upsert(db_session):
    company = upsert_company(db_session, {"name": "Test Co", "domain": "test.com"})
    offering = upsert_service_offering(db_session, {"name": "Agentic Automation"})
    rule = upsert_signal_rule(db_session, {
        "service_id": offering.id,
        "question": "Is the company automating?",
        "weight": "HIGH"
    })

    long_quote = "A" * 500
    long_reasoning = "B" * 400

    res = upsert_signal_evaluation(db_session, {
        "company_id": company.id,
        "rule_id": rule.id,
        "source_url": "https://test.com/news/1",
        "detected": True,
        "confidence": 0.85,
        "evidence_quote": long_quote,
        "reasoning": long_reasoning
    })
    assert res is not None
    assert len(res.evidence_quote) == 280
    assert res.evidence_quote == "A" * 280
    assert len(res.reasoning) == 200
    assert res.reasoning == "B" * 200
    assert db_session.query(SignalEvaluation).count() == 1

    # Conflict on (company_id, rule_id, source_url) updates record
    updated_res = upsert_signal_evaluation(db_session, {
        "company_id": str(company.id),
        "rule_id": str(rule.id),
        "source_url": "https://test.com/news/1",
        "detected": True,
        "confidence": 0.99,
        "evidence_quote": "Updated quote",
        "reasoning": "Updated reasoning"
    })
    assert updated_res.id == res.id
    assert updated_res.confidence == 0.99
    assert updated_res.evidence_quote == "Updated quote"
    assert db_session.query(SignalEvaluation).count() == 1


def test_upsert_lead_score_and_get_leads(db_session):
    comp1 = upsert_company(db_session, {"name": "Lead Alpha", "domain": "alpha.com"})
    comp2 = upsert_company(db_session, {"name": "Lead Beta", "domain": "beta.com"})
    offering = upsert_service_offering(db_session, {"name": "Cybersecurity SOC"})

    # Upsert lead score for comp1
    score1 = upsert_lead_score(db_session, {
        "company_id": comp1.id,
        "service_id": offering.id,
        "composite_score": 85,
        "is_disqualified": False,
        "executive_summary": "Top lead for Managed SOC"
    })
    assert score1.composite_score == 85

    # Upsert lead score for comp2
    score2 = upsert_lead_score(db_session, {
        "company_id": comp2.id,
        "service_id": offering.id,
        "composite_score": 60,
        "is_disqualified": False,
        "executive_summary": "Moderate lead"
    })
    assert score2.composite_score == 60

    # Query with min_score = 70
    top_leads = get_leads_by_service(db_session, offering.id, min_score=70)
    assert len(top_leads) == 1
    assert top_leads[0].company_id == comp1.id

    # Query with min_score = 50 (should return both sorted desc)
    all_leads = get_leads_by_service(db_session, offering.id, min_score=50)
    assert len(all_leads) == 2
    assert all_leads[0].composite_score == 85
    assert all_leads[1].composite_score == 60

    # Update comp2 score on conflict
    updated_score2 = upsert_lead_score(db_session, {
        "company_id": str(comp2.id),
        "service_id": str(offering.id),
        "composite_score": 95,
        "is_disqualified": False,
        "executive_summary": "Upgraded lead"
    })
    assert updated_score2.id == score2.id
    assert updated_score2.composite_score == 95

    # Query again with min_score = 70: both should now match with comp2 first
    new_top = get_leads_by_service(db_session, str(offering.id), min_score=70)
    assert len(new_top) == 2
    assert new_top[0].company_id == comp2.id
    assert new_top[0].composite_score == 95
    assert new_top[1].company_id == comp1.id
    assert new_top[1].composite_score == 85


def test_mcp_api_key_helpers(db_session):
    key = create_mcp_api_key(db_session, {
        "tenant_name": "Antigravity Agent",
        "key_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "is_active": True
    })
    assert key.id is not None

    found = get_mcp_api_key(db_session, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    assert found is not None
    assert found.tenant_name == "Antigravity Agent"

    missing = get_mcp_api_key(db_session, "nonexistent_key_hash")
    assert missing is None


def test_session_generator_and_fallback():
    # Test session generator
    gen = get_db()
    s = next(gen)
    assert s is not None
    s.close()

    # Test resilient engine with unreachable postgres url
    old_env = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = "postgresql://user:wrongpassword@127.0.0.1:54329/fake_db"
        resilient_eng = create_resilient_engine()
        # Should fall back gracefully to sqlite
        assert "sqlite" in str(resilient_eng.url)
    finally:
        if old_env is not None:
            os.environ["DATABASE_URL"] = old_env
        else:
            os.environ.pop("DATABASE_URL", None)
