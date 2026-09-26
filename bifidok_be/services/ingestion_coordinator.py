"""
Background Ingestion Coordinator for Orange Systems sales intelligence platform.
Implements the Ephemeral Stream-and-Discard Pipeline (Section 3.1),
Two-Tier Ingestion & Verification Architecture (Section 4.1),
Anti-Hallucination Verbatim Guardrail, and 3-Layer Composite Scoring (Section 4.2).
"""
import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from connectors.ats import fetch_ats_hiring_signals
from connectors.financials import fetch_financial_signals
from connectors.firmographics import resolve_company_entity
from connectors.gdelt import fetch_gdelt_signals
from connectors.news import fetch_company_news
from connectors.registries import verify_official_registry
from connectors.tenders import fetch_public_procurement_tenders
from db.repository import (
    to_uuid,
    upsert_company,
    upsert_lead_score,
    upsert_signal_evaluation,
)
from db.schema import (
    Company,
    LeadScore,
    ServiceOffering,
    SignalEvaluation,
    SignalRule,
    SignalWeightType,
)
from db.session import SessionLocal
from engine.anti_hallucination import verify_verbatim_quote
from engine.offering_catalog import (
    FLAGSHIP_OFFERINGS,
    decompose_custom_offering,
)
from services.cache import (
    get_cache,
    set_cache,
    update_job_status,
)

logger = logging.getLogger(__name__)

# Weight mapping for Section 4.2 Deterministic Scoring Logic
WEIGHT_VALUES = {
    SignalWeightType.HIGH: 35.0,
    SignalWeightType.MEDIUM: 20.0,
    SignalWeightType.LOW: 10.0,
    SignalWeightType.DISQUALIFY: 0.0,
    "HIGH": 35.0,
    "MEDIUM": 20.0,
    "LOW": 10.0,
    "DISQUALIFY": 0.0,
}
CONFIDENCE_PENALTY_BASE = 25.0


class StreamChunk:
    """Ephemeral memory buffer for streamed document snippets (discarded after extraction)."""

    def __init__(self, source_url: str, text: str, category: str):
        self.source_url = source_url
        self.text = text
        self.category = category


def tier1_filter_chunk(chunk_text: str, trigger_keywords: Optional[List[str]] = None) -> bool:
    """
    Tier 1 Fast Statistical / Keyword Pre-Filter (CPU-bound local classifier).
    Sheds 95% of routine boilerplate and noise without incurring token costs (Section 4.1).
    Returns True (Label 1: Potential Actionable Signal) or False (Label 0: Discard).
    """
    if not chunk_text or not isinstance(chunk_text, str):
        return False

    clean_text = chunk_text.strip()
    if len(clean_text) < 25:
        return False

    lowered = clean_text.lower()

    # Generic noise patterns to evict immediately
    boilerplate_patterns = [
        "all rights reserved",
        "accept all cookies",
        "privacy policy",
        "terms and conditions",
        "cookie preferences",
        "enable javascript to run this app",
        "copyright ©",
    ]
    if any(bp in lowered for bp in boilerplate_patterns) and len(clean_text) < 120:
        return False

    # Core B2B transformation & operational intent trigger tokens
    core_triggers = [
        "transform",
        "moderniz",
        "procure",
        "tender",
        "rfp",
        "contract",
        "vendor",
        "partner",
        "invest",
        "growth",
        "deploy",
        "implement",
        "automat",
        "ai",
        "agent",
        "cloud",
        "security",
        "cyber",
        "nis2",
        "dora",
        "hir",
        "recruit",
        "headcount",
        "reduc",
        "restructur",
        "insolven",
        "bankrupt",
        "efficien",
        "cost",
        "fleet",
        "cargo",
        "bike",
        "logistics",
        "delivery",
        "margin",
    ]

    if trigger_keywords:
        for kw in trigger_keywords:
            if kw and kw.lower() in lowered:
                return True

    return any(trig in lowered for trig in core_triggers)


def _stem(word: str) -> str:
    """Basic rule-based English suffix stemmer for token alignment."""
    w = word.lower().strip()
    for suffix in ["tion", "ing", "ies", "ed", "es", "ive", "ize", "ise", "s"]:
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            return w[: -len(suffix)]
    return w


def tier2_extract_signal(
    rule_question: str,
    rule_guidance: Optional[str],
    source_text: str,
) -> Tuple[bool, float, str, str]:
    """
    Tier 2 Grounded Structured Extraction.
    Uses Gemini LLM if configured; otherwise runs a local deterministic verbatim extractor.
    Returns: (detected, confidence, evidence_quote, reasoning)
    """
    # Attempt Gemini extraction if API key is provided
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = f"""You are an enterprise sales intelligence verification engine.
Evaluate whether the following source text provides verifiable evidence answering this business question:

Business Question: "{rule_question}"
Guidance: "{rule_guidance or ''}"

Source Text:
\"\"\"{source_text[:2000]}\"\"\"

Output strictly a JSON object with this exact schema:
{{
  "detected": true/false,
  "confidence": 0.0 to 1.0,
  "evidence_quote": "Exact verbatim sentence copied from the source text, or empty string",
  "reasoning": "1-2 sentence explanation under 200 characters"
}}
Return raw JSON only without markdown code fences.
"""
            response = model.generate_content(prompt)
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            data = json.loads(raw)
            return (
                bool(data.get("detected", False)),
                float(data.get("confidence", 0.0)),
                str(data.get("evidence_quote", "")).strip(),
                str(data.get("reasoning", ""))[:200].strip(),
            )
        except Exception as exc:
            logger.debug("Gemini extraction failed (%s). Using deterministic extractor.", exc)

    # Deterministic Rule-Based Grounded Extractor
    # Splits text into sentences and searches for the highest semantic sentence match
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", source_text) if len(s.strip()) > 20]
    if not sentences:
        sentences = [source_text.strip()]

    stopwords = {"the", "and", "for", "with", "this", "that", "does", "have", "from", "are", "was", "were", "been"}
    question_tokens = set(
        _stem(w) for w in re.findall(r"\b[a-zA-Z]{3,}\b", (rule_question + " " + (rule_guidance or "")).lower())
    ) - stopwords

    best_sentence = ""
    best_score = 0

    for sentence in sentences:
        sent_tokens = set(_stem(w) for w in re.findall(r"\b[a-zA-Z]{3,}\b", sentence.lower())) - stopwords
        overlap = len(question_tokens.intersection(sent_tokens))
        if overlap > best_score:
            best_score = overlap
            best_sentence = sentence

    if best_score >= 2:
        conf = min(0.95, 0.60 + (0.08 * best_score))
        return (
            True,
            round(conf, 2),
            best_sentence[:280],
            f"Evidence matches signal criteria ({best_score} keywords aligned with guidance).",
        )

    return (False, 0.0, "", "No verifiable signal indicators identified in text.")


def resolve_or_create_service(session, service_id: str) -> ServiceOffering:
    """
    Resolves ServiceOffering and associated SignalRules in PostgreSQL/SQLite.
    If not already present, generates rules from preset catalog or decomposes automatically.
    """
    svc_uuid = to_uuid(service_id)
    query = session.query(ServiceOffering)
    if svc_uuid:
        service = query.filter(ServiceOffering.id == svc_uuid).first()
        if service:
            return service

    # Check by name / slug
    service = query.filter(ServiceOffering.name.ilike(service_id)).first()
    if service:
        return service

    # Check flagship presets
    flagship = FLAGSHIP_OFFERINGS.get(service_id)
    if flagship:
        existing = query.filter(ServiceOffering.name.ilike(flagship.title)).first()
        if existing:
            return existing

        service = ServiceOffering(
            id=uuid.uuid4(),
            name=flagship.title,
            description=flagship.description,
        )
        session.add(service)
        session.flush()

        # Seed signal rules
        for wedge in flagship.target_wedges:
            rule = SignalRule(
                id=uuid.uuid4(),
                service_id=service.id,
                question=f"Does the enterprise demonstrate strategic demand for {wedge.name}?",
                guidance_notes=wedge.description,
                weight=SignalWeightType.HIGH,
                is_negative=False,
            )
            session.add(rule)

        # Negative / Disqualification rule
        session.add(
            SignalRule(
                id=uuid.uuid4(),
                service_id=service.id,
                question="Is the organization undergoing active insolvency or restructuring?",
                guidance_notes="Corporate insolvency eliminates contracting capacity.",
                weight=SignalWeightType.DISQUALIFY,
                is_negative=True,
            )
        )
        session.commit()
        session.refresh(service)
        return service

    # Decompose custom offering dynamically
    compiled = decompose_custom_offering(service_id)
    offering_name = compiled.get("offering_name", service_id)
    existing_custom = query.filter(ServiceOffering.name.ilike(offering_name)).first()
    if existing_custom:
        return existing_custom

    service = ServiceOffering(
        id=uuid.uuid4(),
        name=offering_name,
        description=compiled.get("description", ""),
    )
    session.add(service)
    session.flush()

    for r_data in compiled.get("signal_rules", []):
        raw_wt = str(r_data.get("weight", "MEDIUM")).upper()
        wt_enum = getattr(SignalWeightType, raw_wt, SignalWeightType.MEDIUM)
        rule = SignalRule(
            id=uuid.uuid4(),
            service_id=service.id,
            question=r_data.get("question", "Signal evaluation rule"),
            guidance_notes=r_data.get("guidance_notes", ""),
            weight=wt_enum,
            is_negative=bool(r_data.get("is_negative", False)),
        )
        session.add(rule)

    session.commit()
    session.refresh(service)
    return service


def compute_3_layer_composite_score(
    evaluations: List[Dict[str, Any]],
    firmographics: Dict[str, Any],
    catalysts: Dict[str, Any],
) -> Tuple[int, bool, Optional[str], str]:
    """
    Computes the 3-Layer Composite Lead Propensity Score:
    - Layer 1: Rule-Based Signal Engine (Section 4.2 Deterministic Logic)
    - Layer 2: Firmographic & Financial Capacity (Solvency, Headcount, Operating Margin)
    - Layer 3: Dynamic Intent & Buying Velocity (ATS hiring roles, Tenders, Press Momentum)

    Returns:
        (composite_score: int [0-100], is_disqualified: bool, disqualification_reason: Optional[str], summary: str)
    """
    # ----------------------------------------------------
    # HARD GATE CHECK: Solvency & Bankruptcy
    # ----------------------------------------------------
    if not firmographics.get("is_solvent", True):
        return (
            0,
            True,
            "Account disqualified: active insolvency, restructuring, or liquidation proceedings.",
            "Disqualified: Credit/insolvency risk prohibits commercial contract approval.",
        )

    # ----------------------------------------------------
    # LAYER 1: Rule-Based Signal Evaluation (Annex 4.2)
    # S = max(0, min(100, sum(Pos * Conf) - sum(Neg * Conf)))
    # ----------------------------------------------------
    pos_sum = 0.0
    neg_sum = 0.0
    is_disqualified = False
    disqualification_reason = None

    for ev in evaluations:
        if not ev.get("detected"):
            continue
        weight = ev.get("weight", "MEDIUM")
        conf = float(ev.get("confidence", 0.0))
        is_neg = bool(ev.get("is_negative", False))

        if weight == "DISQUALIFY" and conf >= 0.80:
            is_disqualified = True
            disqualification_reason = (
                f"Disqualifying rule triggered ({ev.get('question', 'Negative gate')}) with confidence {conf:.2f}."
            )
            return (0, True, disqualification_reason, "Disqualified by high-confidence negative indicator.")

        if is_neg:
            neg_sum += CONFIDENCE_PENALTY_BASE * conf
        else:
            wt_val = WEIGHT_VALUES.get(weight, 20.0)
            pos_sum += wt_val * conf

    layer1_score = max(0.0, min(100.0, pos_sum - neg_sum))

    # ----------------------------------------------------
    # LAYER 2: Firmographic & Financial Capacity Fit
    # ----------------------------------------------------
    headcount = firmographics.get("headcount") or 500
    op_margin = firmographics.get("operating_margin")

    layer2_score = 20.0  # baseline
    if headcount >= 10000:
        layer2_score += 40.0
    elif headcount >= 1000:
        layer2_score += 25.0
    elif headcount >= 100:
        layer2_score += 15.0

    if op_margin is not None:
        if op_margin >= 0.15:
            layer2_score += 40.0  # Strong capital/budget capacity
        elif op_margin > 0.0:
            layer2_score += 25.0  # Cost-reduction / margin pressure
        else:
            layer2_score += 10.0
    else:
        layer2_score += 25.0

    layer2_score = max(0.0, min(100.0, layer2_score))

    # ----------------------------------------------------
    # LAYER 3: Dynamic Public Intent & Velocity
    # ----------------------------------------------------
    matched_roles = catalysts.get("matched_roles", [])
    has_tenders = catalysts.get("has_tenders", False)
    has_news = catalysts.get("has_news", False)

    layer3_score = 15.0
    if matched_roles:
        layer3_score += min(45.0, 15.0 + (10.0 * len(matched_roles)))
    if has_tenders:
        layer3_score += 25.0
    if has_news:
        layer3_score += 15.0

    layer3_score = max(0.0, min(100.0, layer3_score))

    # ----------------------------------------------------
    # FINAL COMPOSITE SYNTHESIS
    # ----------------------------------------------------
    if evaluations:
        blended = (0.50 * layer1_score) + (0.25 * layer2_score) + (0.25 * layer3_score)
    else:
        blended = (0.60 * layer2_score) + (0.40 * layer3_score)

    composite_score = int(round(max(0, min(100, blended))))

    summary = (
        f"Composite Score: {composite_score}/100 "
        f"[Layer 1 Signals: {layer1_score:.0f}, Layer 2 Firmographics: {layer2_score:.0f}, Layer 3 Intent: {layer3_score:.0f}]"
    )

    return (composite_score, False, None, summary)


def _process_domain_sync(
    domain: str,
    service: ServiceOffering,
    session,
) -> Dict[str, Any]:
    """
    Synchronous per-domain worker executing:
    1. Stream-and-discard ingestion
    2. Tier 1 filter
    3. Tier 2 extraction
    4. Anti-hallucination verification
    5. PostgreSQL evaluation upsert
    6. 3-Layer composite score computation and lead score upsert
    """
    clean_domain = domain.strip().lower()

    # 1. Firmographics & Entity Resolution via Database
    cand = None
    session_comp = SessionLocal()
    try:
        companies = session_comp.query(Company).all()
        for c in companies:
            c_dom = str(c.domain or "").strip().lower()
            if c_dom and (clean_domain == c_dom or clean_domain.endswith(f".{c_dom}") or c_dom in clean_domain):
                cand = {"name": c.name, "domain": c.domain}
                break
        if not cand:
            for c in companies:
                c_name = str(c.name or "").strip().lower()
                if c_name and (clean_domain in c_name or c_name in clean_domain):
                    cand = {"name": c.name, "domain": c.domain}
                    break
    finally:
        session_comp.close()

    canonical_entry = None
    if cand and cand.get("name"):
        company_name = cand["name"]
    else:
        company_name = clean_domain.split(".")[0].replace("-", " ").title()

    entity = resolve_company_entity(company_name, domain_hint=clean_domain)
    resolved_name = cand.get("name") if (cand and cand.get("name")) else (entity.get("name") or company_name)

    # Official Registry check
    registry_data = verify_official_registry(resolved_name)
    is_solvent = registry_data.get("is_solvent", True)
    if cand and cand.get("operational_attributes", {}).get("physical_footprint_level") == "Insolvent":
        is_solvent = False

    # Financials
    financials = fetch_financial_signals(resolved_name)

    # Upsert Company in PostgreSQL
    headcount = financials.get("headcount") or (cand.get("headcount") if cand else None) or 500
    industry = financials.get("sector") or (cand.get("sector") if cand else None) or "Enterprise Technology"
    geography = financials.get("country") or entity.get("country") or "EU"

    company_record = upsert_company(
        session=session,
        data={
            "name": resolved_name,
            "domain": clean_domain,
            "industry": industry,
            "geography": geography,
            "employee_count": headcount,
        },
    )

    # 2. Ephemeral Stream-and-Discard Ingestion
    streamed_chunks: List[StreamChunk] = []

    # A. GDELT Doc API
    try:
        gdelt_signals = fetch_gdelt_signals(resolved_name)
        for g_art in gdelt_signals:
            text = f"{g_art.get('title', '')}. {g_art.get('raw_text', '')}"
            url = g_art.get("url") or f"https://{clean_domain}/news"
            streamed_chunks.append(StreamChunk(source_url=url, text=text, category="gdelt"))
    except Exception as exc:
        logger.debug("GDELT fetch failed for %s: %s", resolved_name, exc)

    # B. News RSS
    try:
        news_items = fetch_company_news(resolved_name)
        for n_item in news_items:
            text = f"{n_item.get('title', '')}. {n_item.get('snippet', '')}"
            url = n_item.get("link") or f"https://{clean_domain}/news"
            streamed_chunks.append(StreamChunk(source_url=url, text=text, category="news"))
    except Exception as exc:
        logger.debug("News fetch failed for %s: %s", resolved_name, exc)

    # C. Tenders
    try:
        tender_res = fetch_public_procurement_tenders(resolved_name)
        for t_item in tender_res.get("tenders", []):
            text = f"{t_item.get('title', '')}. {t_item.get('description', '')}"
            url = t_item.get("source_url") or f"https://ted.europa.eu"
            streamed_chunks.append(StreamChunk(source_url=url, text=text, category="tenders"))
    except Exception as exc:
        tender_res = {}
        logger.debug("Tenders fetch failed for %s: %s", resolved_name, exc)

    # D. ATS Hiring
    try:
        ats_res = fetch_ats_hiring_signals(resolved_name)
        for role_name in ats_res.get("matched_roles", []):
            text = f"Active recruitment opening for role: {role_name} at {resolved_name}."
            streamed_chunks.append(StreamChunk(source_url=f"https://{clean_domain}/careers", text=text, category="ats"))
    except Exception as exc:
        ats_res = {}
        logger.debug("ATS fetch failed for %s: %s", resolved_name, exc)

    # E. Wikipedia Summary
    if entity.get("description"):
        streamed_chunks.append(
            StreamChunk(
                source_url=f"https://en.wikipedia.org/wiki/{resolved_name.replace(' ', '_')}",
                text=entity["description"],
                category="overview",
            )
        )

    # F. Canonical verified signals from Annex Section 6
    if canonical_entry:
        for ev in canonical_entry.get("evaluations", []):
            streamed_chunks.append(
                StreamChunk(
                    source_url=ev.get("source_url", f"https://{clean_domain}/strategy"),
                    text=ev.get("evidence_quote", ""),
                    category="canonical_signal",
                )
            )

    # G. Candidate operational attributes & descriptions
    if cand and cand.get("description"):
        streamed_chunks.append(
            StreamChunk(
                source_url=f"https://{clean_domain}/about",
                text=cand["description"],
                category="overview",
            )
        )
    if cand and cand.get("operational_attributes"):
        op_attrs = cand["operational_attributes"]
        if op_attrs.get("esg_net_zero_target"):
            streamed_chunks.append(
                StreamChunk(
                    source_url=f"https://{clean_domain}/sustainability",
                    text=f"Official corporate ESG targets and climate strategy: {op_attrs['esg_net_zero_target']}.",
                    category="esg",
                )
            )

    # 3. Tier 1 Filter & Discard
    candidate_chunks: List[StreamChunk] = []
    for chunk in streamed_chunks:
        if tier1_filter_chunk(chunk.text):
            candidate_chunks.append(chunk)

    # 4. Tier 2 Grounded Extraction & Anti-Hallucination Guardrail
    rules: List[SignalRule] = session.query(SignalRule).filter(SignalRule.service_id == service.id).all()
    evaluations_for_scoring: List[Dict[str, Any]] = []

    combined_text = "\n\n".join(c.text for c in candidate_chunks)

    for rule in rules:
        best_eval = None
        for chunk in candidate_chunks:
            detected, conf, quote, reason = tier2_extract_signal(
                rule_question=rule.question,
                rule_guidance=rule.guidance_notes,
                source_text=chunk.text,
            )

            if detected:
                # Anti-Hallucination Verbatim Assertion
                if not verify_verbatim_quote(quote, chunk.text):
                    logger.warning("Anti-hallucination guardrail rejected non-verbatim quote: %s", quote[:60])
                    continue

                if conf >= 0.50:
                    if best_eval is None or conf > best_eval["confidence"]:
                        best_eval = {
                            "company_id": company_record.id,
                            "rule_id": rule.id,
                            "source_url": chunk.source_url,
                            "detected": True,
                            "confidence": conf,
                            "evidence_quote": quote,
                            "reasoning": reason,
                            "weight": rule.weight.value if hasattr(rule.weight, "value") else str(rule.weight),
                            "is_negative": rule.is_negative,
                            "question": rule.question,
                        }

        # Ephemeral Stream-and-Discard: persist to PostgreSQL, drop raw text buffers
        if best_eval is not None:
            upsert_signal_evaluation(session=session, data=best_eval)
            evaluations_for_scoring.append(best_eval)

    # Evict candidate text payloads from memory
    del streamed_chunks
    del candidate_chunks
    del combined_text

    # 5. Compute 3-Layer Composite Score
    firmographics_data = {
        "is_solvent": is_solvent,
        "headcount": headcount,
        "operating_margin": financials.get("operating_margin"),
    }
    catalysts_data = {
        "matched_roles": ats_res.get("matched_roles", []),
        "has_tenders": bool(tender_res.get("tenders")),
        "has_news": bool(news_items if "news_items" in locals() else False),
    }

    composite_score, is_disq, disq_reason, summary = compute_3_layer_composite_score(
        evaluations=evaluations_for_scoring,
        firmographics=firmographics_data,
        catalysts=catalysts_data,
    )

    # 6. Upsert LeadScore
    lead_score_record = upsert_lead_score(
        session=session,
        data={
            "company_id": company_record.id,
            "service_id": service.id,
            "composite_score": composite_score,
            "is_disqualified": is_disq,
            "disqualification_reason": disq_reason,
            "executive_summary": summary,
        },
    )

    # 7. Cache results for fast MCP lookup
    evidence_payload = {
        "company": resolved_name,
        "domain": clean_domain,
        "score": composite_score,
        "is_disqualified": is_disq,
        "evaluations": [
            {
                "source_url": e["source_url"],
                "confidence": e["confidence"],
                "evidence_quote": e["evidence_quote"],
                "reasoning": e["reasoning"],
            }
            for e in evaluations_for_scoring
        ],
    }
    set_cache(f"evidence:{clean_domain}", evidence_payload, ttl=86400)

    return {
        "domain": clean_domain,
        "company": resolved_name,
        "score": composite_score,
        "is_disqualified": is_disq,
        "summary": summary,
    }


async def run_async_ingestion(
    job_id: str,
    service_id: str,
    domains: List[str],
) -> None:
    """
    Coordinates asynchronous enterprise sales intelligence ingestion:
    - Runs ephemeral stream-and-discard pipeline across target domains
    - Triggers Tier 1 fast statistical noise filter and Tier 2 Gemini structured extraction
    - Verifies evidence against anti-hallucination verbatim guardrail
    - Upserts signal evaluations and bounded audit trails to PostgreSQL
    - Computes 3-Layer composite lead scores
    - Continuously publishes job progress to Redis / cache
    """
    total = len(domains)
    update_job_status(
        job_id=job_id,
        status="STARTED",
        progress=0.0,
        meta={"domains_total": total, "service_id": service_id},
    )

    if total == 0:
        update_job_status(
            job_id=job_id,
            status="COMPLETED",
            progress=1.0,
            meta={"domains_total": 0, "domains_completed": 0, "results": []},
        )
        return

    session = SessionLocal()
    results: List[Dict[str, Any]] = []

    try:
        service = resolve_or_create_service(session, service_id)

        for idx, domain in enumerate(domains):
            progress = idx / total
            update_job_status(
                job_id=job_id,
                status="PROCESSING",
                progress=progress,
                meta={
                    "current_domain": domain,
                    "domains_completed": idx,
                    "domains_total": total,
                },
            )

            # Execute synchronous domain worker in thread pool to prevent event loop blocking
            domain_result = await asyncio.to_thread(
                _process_domain_sync,
                domain=domain,
                service=service,
                session=session,
            )
            results.append(domain_result)

        # Mark job complete
        update_job_status(
            job_id=job_id,
            status="COMPLETED",
            progress=1.0,
            meta={
                "domains_total": total,
                "domains_completed": total,
                "results": results,
            },
        )
        logger.info("Ingestion job %s completed successfully for %d domains.", job_id, total)

    except Exception as exc:
        logger.exception("Ingestion job %s encountered an error: %s", job_id, exc)
        update_job_status(
            job_id=job_id,
            status="FAILED",
            progress=0.0,
            meta={"error": str(exc), "service_id": service_id},
        )
        raise exc
    finally:
        session.close()
