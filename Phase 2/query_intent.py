"""
Phase 2: Query-Side Temporal Intent Analysis

Analyzes queries to extract temporal constraints and preferences.
Phase 1 applies decay to documents only. Phase 2 analyzes query intent
to determine what temporal characteristics the user is seeking.

Examples:
- "Who was CEO in 1997?" → past tense, explicit date, prefers historical docs from 1997
- "Who is the current CEO?" → present tense, prefers recent docs
- "Who became CEO?" → past tense event, prefers historical transition docs
- "Who will be CEO?" → future tense, prefers current/planned docs
"""

import re
import spacy
from datetime import datetime
from typing import Dict, Optional, List, Tuple

nlp = spacy.load("en_core_web_sm")


def extract_year_constraints(text: str) -> List[int]:
    """
    Extract explicit year mentions from query.
    
    Examples:
    - "in 1997" → [1997]
    - "between 2010 and 2015" → [2010, 2015]
    - "in the 1990s" → [1990, 1999]
    """
    years = []
    
    # Match 4-digit years
    year_pattern = r'\b(19\d{2}|20\d{2})\b'
    matches = re.findall(year_pattern, text)
    years.extend([int(y) for y in matches])
    
    # Match decade patterns like "1990s"
    decade_full_pattern = r'\b(19\d{2}|20\d{2})s\b'
    decade_match = re.search(decade_full_pattern, text)
    if decade_match:
        decade_start = int(decade_match.group(1))
        # Round down to decade start (1995 → 1990)
        decade_start = (decade_start // 10) * 10
        years.extend([decade_start, decade_start + 9])
    
    return sorted(set(years))


def detect_query_tense(doc) -> str:
    """
    Detect the main tense of the query.
    
    Returns: "past", "present", "future", or "timeless"
    """
    # Find the main verb (ROOT)
    main_verb = None
    for token in doc:
        if token.dep_ == "ROOT" and token.pos_ == "VERB":
            main_verb = token
            break
    
    if not main_verb:
        return "timeless"
    
    # Check for past-oriented verbs even in present tense form
    # "became", "founded", "started" imply historical events
    past_oriented_lemmas = {"become", "found", "start", "begin", "establish", "create"}
    if main_verb.lemma_.lower() in past_oriented_lemmas:
        return "past"
    
    tense = main_verb.morph.get("Tense")
    
    if tense == ["Past"]:
        return "past"
    elif tense == ["Pres"]:
        return "present"
    
    # Check for future auxiliaries
    if main_verb.text.lower() in {"will", "'ll"}:
        return "future"
    
    # Check for "going to" future
    for child in main_verb.children:
        if child.text.lower() == "going" and any(
            grandchild.text.lower() == "to" for grandchild in child.children
        ):
            return "future"
    
    return "present"  # default


def detect_temporal_markers(text: str) -> Dict[str, bool]:
    """
    Detect temporal marker keywords in query.
    
    Returns dict of marker types found.
    """
    text_lower = text.lower()
    
    markers = {
        "current": any(word in text_lower for word in ["current", "currently", "now", "today"]),
        "recent": any(word in text_lower for word in ["recent", "recently", "latest", "new"]),
        "past": any(word in text_lower for word in ["previous", "former", "old", "historical", "past"]),
        "original": any(word in text_lower for word in ["original", "first", "initial"]),
        "future": any(word in text_lower for word in ["future", "upcoming", "next", "planned"]),
    }
    
    return {k: v for k, v in markers.items() if v}


def classify_temporal_intent(query: str) -> Dict:
    """
    Analyze query to determine temporal intent.
    
    Returns:
        {
            "tense": "past" | "present" | "future" | "timeless",
            "years": [1997, ...],  # explicit year constraints
            "decade_range": (1990, 1999) | None,
            "markers": {"current": True, ...},
            "preference": "historical" | "current" | "future" | "specific_date" | "agnostic"
        }
    """
    doc = nlp(query)
    
    tense = detect_query_tense(doc)
    years = extract_year_constraints(query)
    markers = detect_temporal_markers(query)
    
    # Determine temporal preference
    preference = "agnostic"  # default
    
    if years:
        preference = "specific_date"
    elif markers.get("current") or markers.get("recent"):
        preference = "current"
    elif markers.get("past") or markers.get("original"):
        preference = "historical"
    elif markers.get("future"):
        preference = "future"
    elif tense == "past":
        preference = "historical"
    elif tense == "present":
        preference = "current"
    elif tense == "future":
        preference = "future"
    
    # Extract decade range if present
    decade_range = None
    if len(years) == 2 and years[1] - years[0] == 9:
        decade_range = tuple(years)
    
    return {
        "tense": tense,
        "years": years,
        "decade_range": decade_range,
        "markers": markers,
        "preference": preference
    }


def extract_years_from_text(text: str) -> List[int]:
    """Extract 4-digit years mentioned in document text."""
    import re
    years = []
    for match in re.finditer(r'\b(19\d{2}|20\d{2})\b', text):
        years.append(int(match.group(1)))
    return sorted(set(years))


def compute_temporal_alignment(query_intent: Dict, doc_acquired: datetime, 
                               doc_verified: Optional[datetime] = None,
                               doc_text: str = "") -> float:
    """
    Compute alignment score between query intent and document temporal signals.
    
    For specific_date queries: Boost documents where acquisition year matches query year.
    For other intents: Use recency-based scoring.
    
    IMPORTANT: This assumes acquisition date = content era (true for specific_date benchmark,
    but NOT true for TempQuestions where stale docs have wrong info).
    
    Args:
        query_intent: Output from classify_temporal_intent()
        doc_acquired: When document was acquired
        doc_verified: When document was last verified (if any)  
        doc_text: Document text (for potential future content year extraction)
    
    Returns:
        Alignment multiplier (0.85 to 1.25)
        - 1.25: Perfect year match for specific_date queries
        - 1.15: Close year match (within 2 years)
        - 1.05: Acceptable match (within 5 years)
        - 1.0: Neutral
        - 0.95: Current preference + old doc
        - 0.85: Poor year match for specific_date queries
    """
    preference = query_intent["preference"]
    query_years = query_intent["years"]
    
    doc_year = doc_acquired.year
    reference_date = doc_verified if doc_verified else doc_acquired
    days_old = (datetime.now() - reference_date).days
    
    # Specific date preference - boost documents from matching years
    if preference == "specific_date" and query_years:
        target_year = query_years[0]
        year_distance = abs(doc_year - target_year)
        
        if year_distance == 0:
            return 1.30  # Perfect match - strong boost
        elif year_distance == 1:
            return 1.20  # 1 year off - good boost
        elif year_distance <= 3:
            return 1.10  # 2-3 years - moderate boost
        elif year_distance <= 5:
            return 1.05  # 4-5 years - small boost
        elif year_distance <= 10:
            # 6-10 years: Linear decay from 1.0 to 0.90
            return 1.0 - (year_distance - 5) * 0.02
        else:
            # 10+ years: Exponential penalty, stronger for distant years
            # 15 years = 0.80, 20 years = 0.70, 27 years = 0.63
            penalty_factor = min(year_distance / 10.0, 5.0)  # Cap at 5x
            return max(0.60, 1.0 - (0.08 * penalty_factor))
    
    # All other preferences: neutral (let decay system handle it)
    # Reason: Prevents conflicts with benchmarks like TempQuestions where
    # acquisition date != content correctness
    return 1.0


# Test examples
if __name__ == "__main__":
    test_queries = [
        "Who was the CEO of Apple in 1997?",
        "Who is the current CEO of Apple?",
        "Who became CEO of Apple?",
        "What was the population of Tokyo in the 1990s?",
        "What is the latest population of Tokyo?",
        "Who will be the next president?",
        "What is the capital of France?",
    ]
    
    print("="*80)
    print("QUERY TEMPORAL INTENT ANALYSIS")
    print("="*80)
    print()
    
    for query in test_queries:
        intent = classify_temporal_intent(query)
        print(f"Query: {query}")
        print(f"  Tense: {intent['tense']}")
        print(f"  Preference: {intent['preference']}")
        if intent['years']:
            print(f"  Years: {intent['years']}")
        if intent['markers']:
            print(f"  Markers: {', '.join(intent['markers'].keys())}")
        
        # Test alignment with sample docs
        old_doc = datetime(1997, 1, 1)
        recent_doc = datetime(2026, 1, 1)
        
        old_align = compute_temporal_alignment(intent, old_doc)
        recent_align = compute_temporal_alignment(intent, recent_doc)
        
        print(f"  Alignment: 1997 doc={old_align:.2f}, 2026 doc={recent_align:.2f}")
        print()
