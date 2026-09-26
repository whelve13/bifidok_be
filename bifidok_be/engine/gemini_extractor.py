"""
Google AI Studio Gemini Signal Extractor with Anti-Hallucination Verbatim Guardrail.
Extracts grounded buying signals, confidence metrics, and verbatim evidence quotes
from raw document passages using gemini-2.5-flash (with heuristic fallback).
"""
import os
import re
import json
import logging
from typing import Dict, Any, Optional, List

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Default Gemini model
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODEL = "gemini-1.5-flash"


try:
    from engine.anti_hallucination import verify_verbatim_quote
except ImportError:
    try:
        from bifidok_be.engine.anti_hallucination import verify_verbatim_quote
    except ImportError:
        from anti_hallucination import verify_verbatim_quote


def get_genai_client(api_key: Optional[str] = None) -> Optional[Any]:
    """
    Initializes and returns a Google GenAI Client if a valid GEMINI_API_KEY is present.
    Returns None if the key is missing, empty, or placeholder.
    Falls back to parent directory .env if local key is a placeholder.
    """
    key = api_key or os.getenv("GEMINI_API_KEY", "")
    key = key.strip()
    
    # Check for empty or template placeholder keys
    if not key or key.lower() in ("your_gemini_api_key_here", "none", ""):
        # Check parent directory .env fallback
        cur_file = os.path.abspath(__file__)
        parent_dirs = [
            os.path.dirname(os.path.dirname(os.path.dirname(cur_file))),
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(cur_file))))
        ]
        for p_dir in parent_dirs:
            p_env = os.path.join(p_dir, ".env")
            if os.path.exists(p_env):
                try:
                    with open(p_env, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip().startswith("GEMINI_API_KEY="):
                                cand_k = line.strip().split("=", 1)[1].strip().strip("'\"")
                                if cand_k and cand_k.lower() not in ("your_gemini_api_key_here", "none", ""):
                                    key = cand_k
                                    break
                except Exception:
                    pass
            if key and key.lower() not in ("your_gemini_api_key_here", "none", ""):
                break

    if not key or key.lower() in ("your_gemini_api_key_here", "none", ""):
        return None

    try:
        from google import genai
        client = genai.Client(api_key=key)
        return client
    except Exception as exc:
        logger.warning("Could not initialize Google GenAI Client: %s", exc)
        return None


def _heuristic_extract_signal_evidence(
    raw_passage: str,
    question: str,
    guidance: str = ""
) -> Dict[str, Any]:
    """
    Clean, zero-token heuristic fallback for offline testing or when
    GEMINI_API_KEY is not configured.
    
    Extracts verbatim sentences from raw_passage using semantic keyword overlap.
    Guarantees verbatim quote compliance.
    """
    if not raw_passage or not raw_passage.strip():
        return {
            "detected": False,
            "confidence": 0.0,
            "evidence_quote": "",
            "reasoning": "Passage is empty.",
        }

    # Extract keywords from question and guidance
    stopwords = {
        "is", "are", "was", "were", "the", "a", "an", "this", "that", "these",
        "those", "for", "to", "in", "on", "at", "by", "from", "with", "about",
        "into", "through", "during", "before", "after", "above", "below", "of",
        "and", "or", "not", "no", "if", "does", "do", "did", "have", "has",
        "had", "be", "been", "being", "company", "target", "whether", "any",
        "how", "what", "which", "who", "whom", "will", "would", "can", "could",
        "should", "their", "its", "there", "they", "our", "we"
    }

    tokens = re.findall(r"\b[A-Za-z0-9_\-\./]{3,}\b", f"{question} {guidance}".lower())
    query_keywords = [t for t in tokens if t not in stopwords]

    # Split passage into sentences (preserving verbatim text)
    # Split on sentence boundaries: . ! ? or linebreaks followed by space or end
    raw_sentences = [
        s.strip() for s in re.split(r'(?<=[.!?\n])\s+', raw_passage.strip())
        if len(s.strip()) > 10
    ]
    if not raw_sentences:
        raw_sentences = [raw_passage.strip()]

    best_sentence = ""
    best_score = 0
    matched_terms: List[str] = []

    for sentence in raw_sentences:
        s_lower = sentence.lower()
        curr_matches = [kw for kw in query_keywords if kw in s_lower]
        score = len(curr_matches)
        
        # Check for explicit negation markers to avoid false positives (e.g. 'no plans for automation')
        negation_markers = [
            " no ", " not ", " none ", " never ", " halted ", " stopped ",
            " denied ", " cancelled ", " canceled ", " without ", " rejected ",
            " no plans", " not planning", " denies ", " refuted "
        ]
        padded = f" {s_lower} "
        has_explicit_negation = any(neg in padded for neg in negation_markers)

        # High-impact domain signals bonus
        domain_anchors = [
            "nis2", "dora", "automation", "rpa", "ai", "soc", "procurement",
            "tender", "rfp", "migration", "insolvency", "layoff", "restructuring",
            "legacy", "cloud", "security", "perimeter", "vulnerability"
        ]
        for anchor in domain_anchors:
            if anchor in query_keywords and anchor in s_lower:
                score += 2

        if has_explicit_negation:
            score = 0

        if score > best_score:
            best_score = score
            best_sentence = sentence
            matched_terms = curr_matches

    # If significant keyword overlap was found, confirm detection
    if best_score >= 1 and best_sentence:
        # Confidence scaled by match quality
        confidence = min(0.92, round(0.60 + min(best_score * 0.08, 0.32), 2))
        reasoning = (
            f"Heuristic signal detected with semantic keywords "
            f"({', '.join(matched_terms[:3]) if matched_terms else 'keyword match'})."
        )
        # Verify verbatim quote
        quote = best_sentence
        if verify_verbatim_quote(quote, raw_passage):
            return {
                "detected": True,
                "confidence": confidence,
                "evidence_quote": quote,
                "reasoning": reasoning,
            }

    return {
        "detected": False,
        "confidence": 0.0,
        "evidence_quote": "",
        "reasoning": "No relevant signal detected in passage via heuristic fallback.",
    }


def extract_signal_evidence(
    raw_passage: str,
    question: str,
    guidance: str = "",
    model: str = DEFAULT_MODEL,
    client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Tier 2 Grounded Structured Extraction Agent (Annex Section 4.1).
    
    Prompts Google AI Studio Gemini in JSON mode:
    Returns: {"detected": bool, "confidence": float, "evidence_quote": str, "reasoning": str}
    
    Strictly verifies verbatim compliance:
    If evidence_quote is not verbatim in raw_passage, the signal is rejected.
    If GEMINI_API_KEY is not configured or offline, falls back to heuristic extractor.
    """
    if not raw_passage or not raw_passage.strip():
        return {
            "detected": False,
            "confidence": 0.0,
            "evidence_quote": "",
            "reasoning": "Passage is empty.",
        }

    active_client = client or get_genai_client()

    if active_client is None:
        return _heuristic_extract_signal_evidence(raw_passage, question, guidance)

    prompt = f"""You are an enterprise sales intelligence signal extraction auditor.
You analyze raw passages from corporate annual reports, press releases, procurement notices, or job posts to verify specific buying signals.

EVALUATION TASK:
Question: {question}
Guidance Notes: {guidance or 'Identify concrete evidence directly supporting or refuting this question.'}

RAW PASSAGE:
\"\"\"{raw_passage}\"\"\"

RESPONSE INSTRUCTIONS:
You MUST respond with a valid JSON object conforming to this schema:
{{
  "detected": true or false,
  "confidence": float between 0.0 and 1.0,
  "evidence_quote": "exact verbatim quote from RAW PASSAGE supporting detection, or empty string if detected is false",
  "reasoning": "brief explanation (under 200 characters)"
}}

CRITICAL GROUNDING RULES:
1. If detected is true, 'evidence_quote' MUST BE AN EXACT, VERBATIM SUBSTRING copied directly from RAW PASSAGE. Do NOT alter words, grammar, or punctuation.
2. If the passage does not contain direct, verbatim evidence, set 'detected' to false and 'evidence_quote' to "".
3. Anti-hallucination verification will strictly reject any non-verbatim quote.
"""

    models_to_try = [model]
    if model != FALLBACK_MODEL:
        models_to_try.append(FALLBACK_MODEL)

    data = None
    for target_model in models_to_try:
        try:
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                )
            except Exception:
                config = None

            response = active_client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config,
            )
            content = response.text.strip()
            # Strip markdown code blocks if present
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)
            data = json.loads(content)
            break
        except Exception as exc:
            logger.warning(
                "Gemini model '%s' failed: %s. Attempting fallback.",
                target_model,
                exc,
            )

    if data is None:
        logger.info("All Gemini model attempts failed; using clean heuristic fallback.")
        return _heuristic_extract_signal_evidence(raw_passage, question, guidance)

    # Parse and normalize fields
    detected = bool(data.get("detected", False))
    try:
        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, round(confidence, 2)))
    except (ValueError, TypeError):
        confidence = 0.0

    evidence_quote = str(data.get("evidence_quote") or "").strip()
    reasoning = str(data.get("reasoning") or "").strip()

    # Anti-Hallucination Guardrail: Programmatically assert quote exists verbatim
    if detected:
        is_verbatim = verify_verbatim_quote(evidence_quote, raw_passage)
        if not is_verbatim:
            logger.warning(
                "Anti-hallucination guardrail triggered! Quote '%s' is not verbatim in passage.",
                evidence_quote,
            )
            return {
                "detected": False,
                "confidence": 0.0,
                "evidence_quote": "",
                "reasoning": f"REJECTED (Anti-Hallucination Guardrail): Extracted quote '{evidence_quote}' not found verbatim in source passage.",
                "rejection_reason": "Quote not verbatim in source passage",
            }
    else:
        evidence_quote = ""

    return {
        "detected": detected,
        "confidence": confidence,
        "evidence_quote": evidence_quote,
        "reasoning": reasoning,
    }
