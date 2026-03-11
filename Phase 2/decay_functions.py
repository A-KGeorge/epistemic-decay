"""
Phase 2: Query-side temporal intent analysis + document-side decay
Extends Phase 1 with query temporal intent detection and alignment scoring
"""

import spacy
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer

from constants import (
    DECAY_RATES, TEMPORAL_MARKERS, CURRENT_EVENT_KEYWORDS,
    BREAKING_NEWS_KEYWORDS, PHYSICS_MATH_KEYWORDS, INSTITUTIONAL_ROLE_KEYWORDS,
    MATH_KEYWORDS, HISTORICAL_SEAL, CONFIDENCE_FLOOR
)
from compositional_logic import compute_compositional_decay
from query_intent import classify_temporal_intent, compute_temporal_alignment

# Load models
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer('all-MiniLM-L6-v2')


def is_main_clause_past(doc):
    """Check if the main clause verb is in past tense (non-passive)"""
    for token in doc:
        if token.dep_ == "ROOT" and token.morph.get("Tense") == ["Past"]:
            # Check if this is passive voice
            is_passive = any(
                child.dep_ in {"auxpass", "nsubjpass"} 
                for child in token.children
            )
            if is_passive:
                return False  # "was elected" — don't seal
            return True
    return False


def has_historical_role(doc):
    """
    Detect inherently historical roles that should be sealed regardless of tense.
    
    Examples: founder, first CEO, original president, etc.
    These roles describe a historical fact even when phrased in present tense.
    """
    historical_role_markers = {"founder", "founding", "first", "original", "initial", "established", "created"}
    tokens_lower = {token.text.lower() for token in doc}
    lemmas = {token.lemma_.lower() for token in doc}
    
    return bool((tokens_lower | lemmas) & historical_role_markers)


def get_category(lemmas, tokens_lower, labels):
    """Classify content category based on linguistic features"""
    checks = [
        # (condition,                                    category)
        # Order = priority — first match wins
        (bool(tokens_lower & BREAKING_NEWS_KEYWORDS),  "BREAKING_NEWS"),
        (bool(lemmas & MATH_KEYWORDS),                 "MATHEMATICAL_TRUTH"),
        (bool(lemmas & PHYSICS_MATH_KEYWORDS),         "PHYSICAL_LAW"),
        (bool(lemmas & INSTITUTIONAL_ROLE_KEYWORDS),   "INSTITUTIONAL_LEADERSHIP"),
        (bool(lemmas & CURRENT_EVENT_KEYWORDS),        "CURRENT_EVENT"),
        ("PERSON" in labels or "ORG" in labels,        "INSTITUTIONAL_LEADERSHIP"),
        ("GPE" in labels or "LOC" in labels,           "GEOGRAPHIC_FACT"),
    ]
    
    for condition, category in checks:
        if condition:
            return DECAY_RATES[category]
    
    return DECAY_RATES["DEFAULT"]


def classify_decay_rate(text):
    """
    Auto-classify temporal decay rate with compositional contamination logic.
    
    Phase 2: Enabled by default, applies fragility contamination rules.
    
    Returns decay rate (lambda) based on:
    - Tense (past tense → historical seal)
    - **Role-based sealing** (founder, first CEO → historical seal)
    - Temporal markers (currently, now → amplified decay)
    - Entity types and keywords (institutional, geographic, etc.)
    - **Compositional contamination** (zero-decay fragility)
    """
    doc = nlp(text)
    lemmas = {token.lemma_.lower() for token in doc}
    tokens_lower = {token.text.lower() for token in doc}
    labels = {ent.label_ for ent in doc.ents}

    # 1. Tense sealing
    is_past_tense = is_main_clause_past(doc)

    PRESENT_DATE_WORDS = {"today", "now", "currently", "this year", "this month"}

    has_historical_anchor = any(
        ent.label_ == "DATE"
        and ent.text.lower() not in PRESENT_DATE_WORDS
        and not any(marker in ent.text.lower() for marker in PRESENT_DATE_WORDS)
        for ent in doc.ents
    )

    has_temporal_present = bool(tokens_lower & TEMPORAL_MARKERS)
    
    # Role-based sealing: "founder", "first CEO", etc. are inherently historical
    has_hist_role = has_historical_role(doc)

    # Historical seal for:
    # 1. Permanent historical facts with explicit date anchors (existing logic)
    # 2. Inherently historical roles (NEW: Gemini Case D)
    if has_historical_anchor and is_past_tense and not has_temporal_present:
        return HISTORICAL_SEAL
    
    if has_hist_role and not has_temporal_present:
        # "Who is the founder?" → sealed, despite present tense
        return HISTORICAL_SEAL

    # 2. Get base category rate
    base_rate = get_category(lemmas, tokens_lower, labels)
    
    # 3. Phase 2: Apply compositional contamination logic
    # This handles temporal marker amplification internally
    final_rate, explanation = compute_compositional_decay(text, base_rate)
    
    return final_rate


def embed_with_decay(text, acquired_date, category=None, last_verified=None):
    """
    Embed text with temporal decay confidence.
    
    Phase 2: Uses compositional contamination-aware decay classification.
    
    Args:
        text: The text to embed
        acquired_date: When the fact was first acquired
        category: Optional explicit category (otherwise auto-classified with contamination check)
        last_verified: When the fact was last confirmed current (defaults to acquired_date)
    
    Returns:
        385-dimensional vector: 384 semantic + 1 confidence dimension
    """
    reference_date = last_verified if last_verified else acquired_date
    days_elapsed = (datetime.now() - reference_date).days
    
    # Phase 2: Use compositional-aware classification unless category explicitly provided
    decay_rate = DECAY_RATES[category] if category else classify_decay_rate(text)
    
    if decay_rate == 0.0:
        confidence = 1.0  # historically sealed or pure zero-decay — always full confidence
    else:
        raw_confidence = np.exp(-decay_rate * days_elapsed)
        confidence = max(raw_confidence, CONFIDENCE_FLOOR)
    
    semantic = model.encode(text)
    return np.append(semantic, confidence)


def encode_query_with_intent(query: str):
    """
    Phase 2: Encode query with temporal intent analysis.
    
    Unlike Phase 1 (which always uses confidence=1.0), Phase 2 analyzes
    the query's temporal requirements.
    
    Args:
        query: The query string
    
    Returns:
        (query_vector, temporal_intent)
        - query_vector: 385-dim (384 semantic + 1 confidence=1.0)
        - temporal_intent: Dict with tense, preference, years, etc.
    """
    semantic = model.encode(query)
    query_vec = np.append(semantic, 1.0)
    intent = classify_temporal_intent(query)
    
    return query_vec, intent


def score_with_temporal_alignment(query_vec, doc_vec, query_intent, 
                                  doc_acquired, doc_verified=None, doc_text=""):
    """
    Phase 2: Score document with temporal alignment bonus/penalty.
    
    Combines:
    1. Standard cosine similarity (semantic + confidence)
    2. Temporal alignment multiplier based on query intent
    
    Args:
        query_vec: 385-dim query vector
        doc_vec: 385-dim document vector
        query_intent: Output from classify_temporal_intent()
        doc_acquired: Document acquisition date
        doc_verified: Document verification date (optional)
        doc_text: Document text for content year extraction
    
    Returns:
        (base_score, aligned_score, alignment_multiplier)
    """
    # Base cosine similarity (same as Phase 1)
    base_score = np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec))
    
    # Phase 2: Compute temporal alignment
    alignment_multiplier = compute_temporal_alignment(
        query_intent, doc_acquired, doc_verified, doc_text
    )
    
    # Apply alignment to the score
    aligned_score = base_score * alignment_multiplier
    
    return base_score, aligned_score, alignment_multiplier

