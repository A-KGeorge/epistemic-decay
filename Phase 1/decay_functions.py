"""
Core functions for temporal decay classification and embedding
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

# Load models
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer('all-MiniLM-L6-v2')


def is_main_clause_past(doc):
    """Check if the main clause verb is in past tense (non-passive)"""
    for token in doc:
        if token.dep_ == "ROOT" and token.morph.get("Tense") == ["Past"]:
            # Check if this is passive voice
            # Passive: auxpass child exists, or nsubjpass dependency
            is_passive = any(
                child.dep_ in {"auxpass", "nsubjpass"} 
                for child in token.children
            )
            if is_passive:
                return False  # "was elected" — don't seal
            return True
    return False


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
    Auto-classify temporal decay rate using NLP analysis.
    
    Returns decay rate (lambda) based on:
    - Tense (past tense → historical seal)
    - Temporal markers (currently, now → amplified decay)
    - Entity types and keywords (institutional, geographic, etc.)
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

    # Historical seal only for permanent historical facts with explicit date anchors
    # NOT for simple past tense like "served as CEO" (which is an outdated temporal fact)
    if has_historical_anchor and is_past_tense and not has_temporal_present:
        return HISTORICAL_SEAL

    # 2. Classify and apply multiplier
    multiplier = 2.1 if has_temporal_present else 1.0
    base_rate = get_category(lemmas, tokens_lower, labels)

    return base_rate * multiplier


def embed_with_decay(text, acquired_date, category=None, last_verified=None):
    """
    Embed text with temporal decay confidence.
    
    Args:
        text: The text to embed
        acquired_date: When the fact was first acquired
        category: Optional explicit category (otherwise auto-classified)
        last_verified: When the fact was last confirmed current (defaults to acquired_date)
    
    Returns:
        385-dimensional vector: 384 semantic + 1 confidence dimension
    """
    reference_date = last_verified if last_verified else acquired_date
    days_elapsed = (datetime.now() - reference_date).days
    decay_rate = DECAY_RATES[category] if category else classify_decay_rate(text)
    
    if decay_rate == 0.0:
        confidence = 1.0  # historically sealed — always full confidence
    else:
        raw_confidence = np.exp(-decay_rate * days_elapsed)
        confidence = max(raw_confidence, CONFIDENCE_FLOOR)
    
    semantic = model.encode(text)
    return np.append(semantic, confidence)
