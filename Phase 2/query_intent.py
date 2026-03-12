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
    - "turn of the millennium" → [1998, 2002]
    - "around 2000" → [1998, 2002]
    """
    years = []
    text_lower = text.lower()
    
    # Fuzzy timeline patterns
    fuzzy_patterns = [
        (r'turn of (the )?millennium', [1998, 2002]),
        (r'around (the )?millennium', [1998, 2002]),
        (r'end of (the )?(\d{4})s', lambda m: [int(m.group(2)) * 10 + 8, int(m.group(2)) * 10 + 10]),
        (r'beginning of (the )?(\d{4})s', lambda m: [int(m.group(2)) * 10, int(m.group(2)) * 10 + 2]),
        (r'mid[- ](\d{4})s', lambda m: [int(m.group(1)) * 10 + 4, int(m.group(1)) * 10 + 6]),
        (r'around (\d{4})', lambda m: [int(m.group(1)) - 2, int(m.group(1)) + 2]),
    ]
    
    for pattern, result in fuzzy_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if callable(result):
                years.extend(result(match))
            else:
                years.extend(result)
    
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


def detect_historical_perspective(text: str) -> Tuple[bool, Optional[Tuple[int, int]]]:
    """
    Detect if query requests historical perspective/worldview from a specific era.
    
    Examples:
    - "Give me a 1990s perspective on..."
    - "What was the 1980s view of..."
    - "How did people in 2000s think about..."
    - "1990s era predictions about..."
    
    Returns:
        (is_historical_perspective, era_range)
        - is_historical_perspective: True if query wants era-situated beliefs
        - era_range: (start_year, end_year) of the requested era, or None
    """
    text_lower = text.lower()
    
    # Pattern 1: "[decade/year] perspective on/of/about"
    perspective_patterns = [
        r'(\d{4}s?)\s+(?:perspective|view|opinion|thoughts?|thinking|beliefs?)\s+(?:on|of|about|regarding)',
        r'(?:perspective|view|opinion|beliefs?)\s+(?:from|in)\s+(?:the\s+)?(\d{4}s?)',
        r'(\d{4}s?)\s+(?:era|time)\s+(?:perspective|view|predictions?|forecasts?)',
        r'how\s+(?:did|were)\s+(?:people|experts|analysts)\s+(?:in|during)\s+(?:the\s+)?(\d{4}s?)\s+(?:think|view|see|predict)',
        r'what\s+(?:was|were)\s+(?:the\s+)?(\d{4}s?)\s+(?:perspective|view|understanding|belief)',
    ]
    
    for pattern in perspective_patterns:
        match = re.search(pattern, text_lower)
        if match:
            year_str = match.group(1)
            
            # Parse era range
            if year_str.endswith('s'):  # Decade like "1990s"
                decade_start = int(year_str[:-1])
                decade_start = (decade_start // 10) * 10
                return True, (decade_start, decade_start + 9)
            else:  # Specific year like "1995"
                year = int(year_str)
                # Use ±2 year window for specific years
                return True, (year - 2, year + 2)
    
    return False, None


def detect_boundary_conditions(text: str) -> Dict[str, str]:
    """
    Detect boundary conditions/paradigm qualifiers in query.
    
    These are prepositional phrases that specify conditions under which
    a statement is true. They're scientifically critical, not flavor text.
    
    Examples:
    - "In a vacuum, light travels at..."
    - "At sea level, water boils at..."
    - "In Euclidean geometry, parallel lines..."
    - "According to Newton, F=ma"
    - "Under normal conditions, ice melts at..."
    
    Returns:
        Dict mapping condition type to extracted phrase
        {"environment": "vacuum", "paradigm": "Euclidean geometry", ...}
    """
    text_lower = text.lower()
    conditions = {}
    
    # Pattern: "in [a/the] X" (environmental/paradigm qualifier)
    in_match = re.search(r'\bin\s+(?:a|the)?\s*([\w\s]+?)(?:,|\s+[a-z]+\s+(?:travels|boils|is|are|meet))', text_lower)
    if in_match:
        condition_phrase = in_match.group(1).strip()
        # Categorize common conditions
        if 'vacuum' in condition_phrase:
            conditions['environment'] = 'vacuum'
        elif 'geometry' in condition_phrase:
            conditions['paradigm'] = condition_phrase
        elif 'space' in condition_phrase:
            conditions['environment'] = 'space'
        else:
            conditions['context'] = condition_phrase
    
    # Pattern: "at [sea level/normal pressure/etc]"
    at_match = re.search(r'\bat\s+([\w\s]+?)(?:,|\s+[a-z]+\s+(?:water|ice|liquid))', text_lower)
    if at_match:
        conditions['environment'] = at_match.group(1).strip()
    
    # Pattern: "according to X" (paradigm scoping)
    according_match = re.search(r'according\s+to\s+([\w\s]+?)(?:,|\s+[a-z]+)', text_lower)
    if according_match:
        conditions['paradigm'] = according_match.group(1).strip()
    
    # Pattern: "under X conditions"
    under_match = re.search(r'under\s+([\w\s]+?)\s+conditions', text_lower)
    if under_match:
        conditions['environment'] = under_match.group(1).strip() + ' conditions'
    
    return conditions


def detect_temporal_markers(text: str) -> Dict[str, bool]:
    """
    Detect temporal marker keywords in query.
    
    Returns dict of marker types found, including directional operators.
    """
    text_lower = text.lower()
    
    # Detect directional operators with context (handles  possessives and multi-word phrases)
    before_match = re.search(r'before\s+([\w\']+(?:\s+[\w\']+)*)', text_lower)
    after_match = re.search(r'(?:after|since)\s+([\w\']+(?:\s+[\w\']+)*)', text_lower)
    
    markers = {
        "current": any(word in text_lower for word in ["current", "currently", "now", "today"]),
        "recent": any(word in text_lower for word in ["recent", "recently", "latest", "new"]),
        "past": any(word in text_lower for word in ["previous", "former", "old", "historical", "past"]),
        "original": any(word in text_lower for word in ["original", "first", "initial", "founder", "founding"]),
        "future": any(word in text_lower for word in ["future", "upcoming", "next", "planned"]),
        # Directional operators
        "before": before_match is not None,
        "after": after_match is not None,
        "during": "during" in text_lower or "while" in text_lower,
        "until": "until" in text_lower or "till" in text_lower,
    }
    
    # Store the entity/event referenced by directional operators
    if before_match:
        markers["before_entity"] = before_match.group(1).strip()
    if after_match:
        markers["after_entity"] = after_match.group(1).strip()
    
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
            "preference": "historical" | "current" | "future" | "specific_date" | "agnostic" | "historical_perspective",
            "directional": "before" | "after" | "during" | None,
            "role_seal": bool,  # True if query contains inherently historical roles
            "historical_perspective": bool,  # True if query wants era-situated beliefs
            "perspective_era": (start, end) | None,  # Era range for historical perspective
            "boundary_conditions": dict  # Paradigm qualifiers like "in a vacuum"
        }
    """
    doc = nlp(query)
    
    tense = detect_query_tense(doc)
    years = extract_year_constraints(query)
    markers = detect_temporal_markers(query)
    
    # NEW: Detect historical perspective queries
    is_historical_perspective, perspective_era = detect_historical_perspective(query)
    
    # NEW: Detect boundary conditions (paradigm qualifiers)
    boundary_conditions = detect_boundary_conditions(query)
    
    # Detect directional operators
    directional = None
    if markers.get("before"):
        directional = "before"
    elif markers.get("after"):
        directional = "after"
    elif markers.get("during"):
        directional = "during"
    elif markers.get("until"):
        directional = "until"
    
    # Flag for EXPLICIT directional queries (has both operator AND entity)
    # This enables strong gradients safely without breaking TempQuestions
    explicit_directional = (
        (directional == "before" and "before_entity" in markers) or
        (directional == "after" and "after_entity" in markers)
    )
    
    # Detect inherently historical roles (founder, first X, etc.)
    role_seal = markers.get("original", False)
    
    # Determine temporal preference
    preference = "agnostic"  # default
    
    # HIGHEST PRIORITY: Historical perspective queries (era-situated beliefs)
    if is_historical_perspective:
        preference = "historical_perspective"
        # Override years with perspective era if not already set
        if not years and perspective_era:
            years = [perspective_era[0], perspective_era[1]]
    # Directional operators take precedence when present
    elif directional in ["before", "after"]:
        # Keep years for alignment filtering, but note this is a directional query
        if years:
            preference = "specific_date"  # Will use year + directional filtering
        else:
            preference = "historical"  # Entity-based directional without years
    elif years:
        preference = "specific_date"
    elif markers.get("current") or markers.get("recent"):
        # Multi-marker conflict: "current" in historical context
        if years and years[0] < datetime.now().year - 5:
            # Historical year conflicts with "current" - treat as historical with relative "current"
            preference = "specific_date"
        else:
            preference = "current"
    elif markers.get("past") or role_seal:
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
    elif len(years) == 2 and years[1] - years[0] == 4:
        # Fuzzy ranges like "turn of millennium" (1998-2002)
        decade_range = tuple(years)
    
    return {
        "tense": tense,
        "years": years,
        "decade_range": decade_range,
        "markers": markers,
        "preference": preference,
        "directional": directional,
        "role_seal": role_seal,
        "explicit_directional": explicit_directional,
        "historical_perspective": is_historical_perspective,
        "perspective_era": perspective_era,
        "boundary_conditions": boundary_conditions
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
    For historical queries: Boost older documents over recent ones.
    For current queries: Boost recent documents.
    For directional queries: Apply exclusionary filtering.
    
    IMPORTANT: This assumes acquisition date = content era (true for specific_date benchmark,
    but NOT true for TempQuestions where stale docs have wrong info).
    
    Args:
        query_intent: Output from classify_temporal_intent()
        doc_acquired: When document was acquired
        doc_verified: When document was last verified (if any)  
        doc_text: Document text (for potential future content year extraction)
    
    Returns:
        Alignment multiplier (0.60 to 1.30)
        - 1.30: Perfect year match for specific_date queries
        - 1.20: Historical boost for old docs on historical queries
        - 1.15: Current boost for recent docs on current queries
        - 1.0: Neutral
        - 0.85: Poor temporal alignment
        - 0.60: Strong negative alignment (e.g., recent doc on historical query)
    """
    preference = query_intent["preference"]
    query_years = query_intent.get("years", [])
    directional = query_intent.get("directional")
    markers = query_intent.get("markers", {})
    
    doc_year = doc_acquired.year
    reference_date = doc_verified if doc_verified else doc_acquired
    days_old = (datetime.now() - reference_date).days
    years_old = days_old / 365.25
    
    # Check if this is an EXPLICIT directional query (safe for strong gradients)
    explicit_directional = query_intent.get("explicit_directional", False)
    
    # HIGHEST PRIORITY: Historical perspective queries (era-situated beliefs)
    # User wants historical worldview, not current accuracy - REVERSE temporal logic
    if preference == "historical_perspective":
        perspective_era = query_intent.get("perspective_era")
        if perspective_era:
            era_start, era_end = perspective_era
            era_midpoint = (era_start + era_end) / 2
            
            # Documents FROM the requested era get massive boost
            if era_start <= doc_year <= era_end:
                return 1.50  # Strong boost for era-appropriate documents
            # Documents BEFORE the era are acceptable (older perspectives)
            elif doc_year < era_start:
                years_before = era_start - doc_year
                return max(0.90, 1.20 - (years_before * 0.05))  # Gentle decay
            # Documents AFTER the era are anachronistic - heavy penalty
            else:  # doc_year > era_end
                years_after = doc_year - era_end
                # Steep penalty: 5 years after = 0.60, 10 years = 0.40, 20 years = 0.30
                return max(0.30, 0.90 - (years_after * 0.06))
    
    # Entity-based directional queries - Apply STRONG gradients ONLY for explicit directional
    # For general "historical" preference (from tense), stay neutral to protect TempQuestions
    if explicit_directional and directional == "before" and "before_entity" in markers and not query_years:
        # "before X" → strong gradient favoring older documents
        # Creates differentiation: 20yo=1.40, 10yo=1.20, 5yo=1.10, 1yo=0.70
        if years_old > 1:
            return 1.0 + min(years_old * 0.02, 0.40)  # Linear boost, cap at +0.40
        else:
            return 0.70  # Strong penalty for very recent docs
    
    if explicit_directional and directional == "after" and "after_entity" in markers and not query_years:
        # "after X" or "since X" → strong inverse gradient favoring newer documents  
        # Creates differentiation: 1yo=1.40, 5yo=1.25, 31yo=0.68, 38yo=0.58
        if years_old < 15:
            return 1.45 - (years_old * 0.03)  # Steep gradient: newer is better
        else:
            return max(0.50, 1.15 - (years_old * 0.015))  # Continued gradient, low floor
    
    # Specific date preference - boost documents from matching years
    if preference == "specific_date" and query_years:
        target_year = query_years[0]
        year_distance = abs(doc_year - target_year)
        
        # Directional filtering for "before" and "after" with explicit years
        if directional == "before" and doc_year >= target_year:
            return 0.50  # Strong penalty for documents on or after the exclusion date
        elif directional == "after" and doc_year <= target_year:
            return 0.50  # Strong penalty for documents on or before the start date
        
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
    # Reason: In benchmarks like TempQuestions, acquisition date ≠ content correctness
    # Stale docs can be recent, correct docs can be old
    # Only explicit temporal constraints (years, directional operators) warrant alignment boosts
    return 1.0


def compute_boundary_condition_match(query_conditions: Dict[str, str], doc_text: str) -> float:
    """
    Compute alignment score for boundary condition preservation.
    
    Rewards documents that preserve query's boundary conditions (paradigm qualifiers).
    
    Examples:
    - Query: "In a vacuum, light travels at X"
    - Doc with "in a vacuum": 1.20 (preserved condition)
    - Doc without: 0.90 (lost precision)
    
    Args:
        query_conditions: Dict from detect_boundary_conditions()
        doc_text: Document text to check for condition preservation
    
    Returns:
        Multiplier (0.85 to 1.25)
        - 1.25: Exact condition match (scientifically precise)
        - 1.00: No conditions to match (neutral)
        - 0.90: Condition present in query but absent in doc (lossy generalization)
    """
    if not query_conditions:
        return 1.0  # No conditions to match
    
    doc_lower = doc_text.lower()
    matches = 0
    total_conditions = len(query_conditions)
    
    for condition_type, condition_value in query_conditions.items():
        condition_lower = condition_value.lower()
        
        # Check for exact phrase match
        if condition_lower in doc_lower:
            matches += 1
        # Check for key term match (e.g., "vacuum" in "in a vacuum")
        elif any(term in doc_lower for term in condition_lower.split() if len(term) > 3):
            matches += 0.5  # Partial credit for related terms
    
    if matches == 0:
        # Query has boundary conditions but doc doesn't preserve them
        # This is lossy generalization - scientific precision lost
        return 0.85
    elif matches == total_conditions:
        # Perfect preservation of all boundary conditions
        return 1.25
    else:
        # Partial preservation
        match_ratio = matches / total_conditions
        return 1.0 + (match_ratio * 0.25)


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
