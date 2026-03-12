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
    3. Boundary condition matching (paradigm qualifier preservation)
    
    Args:
        query_vec: 385-dim query vector
        doc_vec: 385-dim document vector
        query_intent: Output from classify_temporal_intent()
        doc_acquired: Document acquisition date
        doc_verified: Document verification date (optional)
        doc_text: Document text for content year extraction and boundary condition matching
    
    Returns:
        (base_score, aligned_score, alignment_multiplier)
    """
    from query_intent import compute_boundary_condition_match
    
    # Base cosine similarity (same as Phase 1)
    base_score = np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec))
    
    # Phase 2: Compute temporal alignment
    alignment_multiplier = compute_temporal_alignment(
        query_intent, doc_acquired, doc_verified, doc_text
    )
    
    # NEW: Compute boundary condition alignment (paradigm qualifier preservation)
    boundary_conditions = query_intent.get("boundary_conditions", {})
    boundary_multiplier = compute_boundary_condition_match(boundary_conditions, doc_text)
    
    # Combine temporal alignment and boundary condition preservation
    combined_multiplier = alignment_multiplier * boundary_multiplier
    
    # Apply alignment to the score
    aligned_score = base_score * combined_multiplier
    
    return base_score, aligned_score, combined_multiplier


# =====================================================================
# PHASE 3: Graph + Era Matching Integration
# =====================================================================

def score_with_graph_and_alignment(query, query_vec, doc_vec, query_intent,
                                  doc_acquired, knowledge_graph,  
                                  doc_verified=None, doc_text=""):
    """
    Phase 3: Score document with graph matching + era adjustment.
    
    Override-when-confident strategy:
    1. Try graph matching first
    2. If graph match ≥ 0.8 (EXACT), use graph + era score
    3. Else fallback to Phase 2 temporal alignment
    
    This handles cases where:
    - Same person across years (continuity: Jassy 2021 vs 2024)
    - Small year gaps insufficient for Phase 2 (2-5 years)
    - Succession queries requiring graph structure
    
    Args:
        query: Query string (for graph extraction)
        query_vec: 385-dim query vector
        doc_vec: 385-dim document vector
        query_intent: Output from classify_temporal_intent()
        doc_acquired: Document acquisition date
        knowledge_graph: TemporalKnowledgeGraph instance
        doc_verified: Document verification date (optional)
        doc_text: Document text for content year extraction
        
    Returns:
        (base_score, final_score, strategy, debug_info)
        - base_score: Cosine similarity
        - final_score: Graph+era or Phase 2 score
        - strategy: "graph" | "phase2_fallback"
        - debug_info: Dict with match details
    """
    import sys
    sys.path.append('Phase 3')
    from graph_matching import compute_graph_alignment, compute_era_adjusted_score
    
    # Base cosine similarity
    base_score = np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec))
    
    # Try graph matching
    graph_result = compute_graph_alignment(query, knowledge_graph, doc_acquired)
    graph_score = graph_result["score"]
    
    debug_info = {
        "graph_match_type": graph_result["match_type"],
        "graph_score": graph_score,
        "matched_entity": graph_result["matched_entity"]
    }
    
    # Don't override on directional queries - graph lacks "before/after" reasoning
    # Phase 2's directional gradients are superior for these cases
    explicit_directional = query_intent.get("explicit_directional", False)
    
    # Override-when-confident: Use graph if high-confidence structural match
    if graph_score >= 0.8 and not explicit_directional:  # EXACT or high NEAR_MATCH
        # Apply era adjustment
        query_year = query_intent.get("years", [None])[0] if query_intent.get("years") else None
        era_score = compute_era_adjusted_score(graph_result, doc_acquired, query_year)
        
        # Combine base similarity with era-adjusted graph score
        # Graph provides structural match, era provides temporal disambiguation
        final_score = base_score * era_score
        
        debug_info["era_score"] = era_score
        debug_info["strategy"] = "graph"
        
        return base_score, final_score, "graph", debug_info
    
    else:
        # Fallback to Phase 2 temporal alignment
        _, aligned_score, alignment_mult = score_with_temporal_alignment(
            query_vec, doc_vec, query_intent, doc_acquired, doc_verified, doc_text
        )
        
        debug_info["phase2_alignment"] = alignment_mult
        debug_info["strategy"] = "phase2_fallback"
        
        return base_score, aligned_score, "phase2_fallback", debug_info

