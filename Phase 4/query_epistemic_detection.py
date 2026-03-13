"""
Query-Aware Epistemic Detection
Detects uncertainty and paradigm markers in QUERIES (not documents)

Purpose: Only apply epistemic modulation when the query itself requests it.
This prevents penalizing documents for their phrasing when queries are straightforward.

Example:
- Query: "Who was PM in 2017?" → NO epistemic markers → skip epistemic analysis
- Query: "Who was probably PM in 2017?" → HAS uncertainty → apply uncertainty modulation
- Query: "According to British law, who was PM?" → HAS paradigm → apply paradigm scoping
"""

import re
from typing import Dict, Set, List

# Uncertainty markers that indicate query wants uncertainty analysis
QUERY_UNCERTAINTY_MARKERS = {
    # High uncertainty
    "allegedly", "supposedly", "might", "may", "possibly", "perhaps", "could",
    
    # Medium uncertainty
    "likely", "probably", "seems", "appears", "suggests", "indicates",
    
    # Estimation/approximation
    "approximately", "roughly", "around", "about", "circa", "nearly", "almost",
    "estimate", "estimated", "estimation",
    
    # Belief/opinion
    "believe", "think", "suspect", "assume", "hypothesize", "speculate",
    
    # Confidence qualifiers (even these indicate epistemic context)
    "definitely", "certainly", "clearly", "obviously", "undoubtedly"
}

# Paradigm markers that indicate query wants paradigm-scoped answer
QUERY_PARADIGM_MARKERS = {
    # Explicit framework markers
    "according to", "within", "under", "in the context of", "from the perspective of",
    "based on", "using", "following", "per",
    
    # Conditional framing
    "assuming", "given", "provided that", "granted that", "if we assume"
}

# Numerical uncertainty patterns (regex)
NUMERICAL_UNCERTAINTY_PATTERNS = [
    r'\±\s*\d+',  # ± 5, ± 10%, etc.
    r'plus or minus\s+\d+',  # plus or minus 5
    r'\d+\s*to\s*\d+',  # 10 to 15 (range)
    r'\d+\s*-\s*\d+',  # 10-15 (range)
    r'between\s+\d+\s+and\s+\d+',  # between 10 and 15
    r'margin of error',
    r'error bar',
    r'confidence interval'
]

# Invariant keywords (physical/mathematical constants that should bypass Phase 4)
INVARIANT_KEYWORDS = {
    "speed of light", "planck's constant", "planck constant", "gravitational constant",
    "pi", "boiling point", "freezing point", "melting point", "absolute zero",
    "parallel lines", "prime number", "pythagorean theorem", "f=ma", "e=mc",
    "avogadro", "boltzmann", "electron mass", "proton mass",
    "newton's", "einstein's", "maxwell's equations", "schrodinger"
}

# Baseline/foundational paradigms (should not be decayed or overridden by specialized paradigms)
FOUNDATIONAL_PARADIGMS = {
    "euclidean geometry", "euclidean", "newtonian mechanics", "newtonian", 
    "classical logic", "classical", "standard arithmetic", "periodic table",
    "basic", "fundamental", "traditional", "standard"
}

# Temporal operators - linguistic gates that shift temporal focus
TEMPORAL_OPERATORS = {
    "current": {"bias": "present", "window": (0, 365)},  # Focus on last year
    "present": {"bias": "present", "window": (0, 365)},
    "now": {"bias": "present", "window": (0, 90)},
    "former": {"bias": "past", "window": (366, 3650)},  # Focus on 1-10 years ago
    "previous": {"bias": "past", "window": (366, 3650)},
    "was": {"bias": "past", "window": (None, None)},  # Generic past
    "future": {"bias": "future", "window": (None, None)},
    "upcoming": {"bias": "future", "window": (None, None)}
}


def detect_query_uncertainty_markers(query: str) -> Dict:
    """
    Detect uncertainty markers in query text.
    
    Args:
        query: Query string
        
    Returns:
        dict with:
            - has_uncertainty: bool
            - markers_found: list of matched markers
            - numerical_uncertainty: bool (if has ±, ranges, etc.)
    """
    query_lower = query.lower()
    
    # Check word-based uncertainty markers
    markers_found = []
    for marker in QUERY_UNCERTAINTY_MARKERS:
        if marker in query_lower:
            markers_found.append(marker)
    
    # Check numerical uncertainty patterns
    has_numerical = False
    for pattern in NUMERICAL_UNCERTAINTY_PATTERNS:
        if re.search(pattern, query_lower):
            has_numerical = True
            markers_found.append(f"numerical_pattern:{pattern[:20]}")
            break
    
    return {
        "has_uncertainty": len(markers_found) > 0 or has_numerical,
        "markers_found": markers_found,
        "numerical_uncertainty": has_numerical
    }


def detect_query_paradigm_markers(query: str) -> Dict:
    """
    Detect paradigm/framework markers in query text.
    
    Args:
        query: Query string
        
    Returns:
        dict with:
            - has_paradigm: bool
            - markers_found: list of matched markers
            - paradigm_context: extracted framework name (if found)
    """
    query_lower = query.lower()
    
    markers_found = []
    paradigm_context = None
    
    # Check for explicit paradigm markers
    for marker in QUERY_PARADIGM_MARKERS:
        if marker in query_lower:
            markers_found.append(marker)
            
            # Try to extract what comes after the marker
            marker_pos = query_lower.find(marker)
            after_marker = query[marker_pos + len(marker):].strip()
            # Take next 3-5 words as potential paradigm context
            words = after_marker.split()[:5]
            if words:
                paradigm_context = ' '.join(words)
    
    # Also check for specific theory/framework mentions
    framework_keywords = [
        "theory", "model", "framework", "paradigm", "system",
        "physics", "economics", "geometry", "mathematics", "philosophy",
        "newtonian", "quantum", "relativistic", "euclidean", "keynesian"
    ]
    
    for keyword in framework_keywords:
        if keyword in query_lower:
            markers_found.append(f"framework:{keyword}")
    
    return {
        "has_paradigm": len(markers_found) > 0,
        "markers_found": markers_found,
        "paradigm_context": paradigm_context
    }


def detect_invariant_context(text: str) -> bool:
    """
    Detect if the query involves a physical or mathematical invariant.
    
    These are universal constants/laws that should bypass Phase 4 modulation
    to protect the most accurate/nuanced formulation from being penalized.
    
    CRITICAL: This should only trigger for STATEMENTS about constants,
    not QUESTIONS about them. Questions about foundational concepts
    should go through paradigm validation.
    
    Args:
        text: Query or document text
        
    Returns:
        bool: True if text involves an invariant constant/law (as a statement)
    """
    text_lower = text.lower()
    
    # If it's a question (has question mark or starts with question words),
    # don't treat it as an invariant statement - it needs paradigm analysis
    is_question = (
        '?' in text or 
        text_lower.startswith(('what', 'who', 'where', 'when', 'why', 'how', 'do', 'does', 'did', 'is', 'are', 'was', 'were', 'can', 'could', 'would', 'should'))
    )
    
    if is_question:
        # Questions about constants/concepts need paradigm validation, not bypass
        return False
    
    # For statements, check if they involve invariant constants
    return any(keyword in text_lower for keyword in INVARIANT_KEYWORDS)


def is_baseline_query(query: str, detected_paradigms: Set[str] = None) -> bool:
    """
    Check if a query is asking for a general/foundational fact rather than specialized.
    
    If the query mentions a foundational paradigm or NO paradigm, it's a baseline.
    This protects Euclidean geometry, Newtonian mechanics, etc. from being
    overridden by more specialized modern paradigms.
    
    Args:
        query: Query text
        detected_paradigms: Set of paradigms detected in query (optional)
        
    Returns:
        bool: True if query wants baseline/foundational answer
    """
    query_lower = query.lower()
    
    # If the user explicitly asks for the foundational version
    if any(p.replace("_", " ") in query_lower for p in FOUNDATIONAL_PARADIGMS):
        return True
    
    # If the user did NOT provide a specialized context (e.g., "In Relativity...")
    specialized_markers = [
        "relativity", "relativistic", "quantum", "non-euclidean", 
        "non euclidean", "modern", "advanced", "hyperbolic", "elliptic"
    ]
    if not any(m in query_lower for m in specialized_markers):
        return True
    
    return False


def extract_temporal_operators(query: str) -> Dict:
    """
    Detect linguistic operators that shift the temporal focus.
    
    These are words like "current", "former", "was" that indicate
    WHEN the query is focused, not just WHAT it's asking.
    
    Args:
        query: Query text
        
    Returns:
        dict with:
            - bias: "present" | "past" | "future" | "neutral"
            - window: (min_days, max_days) for matching documents, or (None, None)
            - operator_found: str (which operator triggered)
    """
    query_lower = query.lower()
    found_ops = []
    
    for op, config in TEMPORAL_OPERATORS.items():
        # Check for word boundaries to avoid false matches
        if f" {op} " in f" {query_lower} " or query_lower.startswith(f"{op} ") or query_lower.endswith(f" {op}"):
            found_ops.append((op, config))
    
    if not found_ops:
        return {"bias": "neutral", "window": (None, None), "operator_found": None}
    
    # Priority: if 'former' and 'current' are both present, it's a comparison
    # For now, take the first operator (simplification)
    operator, config = found_ops[0]
    
    return {
        "bias": config["bias"],
        "window": config["window"],
        "operator_found": operator
    }


def should_apply_epistemic_modulation(query: str) -> Dict:
    """
    Determine if epistemic modulation should be applied based on query.
    
    This is the CRITICAL GATE: epistemic analysis only runs if query asks for it.
    
    Args:
        query: Query string
        
    Returns:
        dict with:
            - apply_epistemic: bool (master switch)
            - apply_uncertainty: bool
            - apply_paradigm: bool
            - uncertainty_info: dict from detect_query_uncertainty_markers
            - paradigm_info: dict from detect_query_paradigm_markers
            - reason: str explaining decision
            - is_invariant: bool (if query involves physical/mathematical constant)
            - is_baseline: bool (if query wants foundational paradigm)
            - temporal_op: dict (temporal operator info)
    """
    # CRITICAL GATE 1: Check if query involves an invariant (physical/math constant)
    is_invariant = detect_invariant_context(query)
    
    if is_invariant:
        return {
            "apply_epistemic": False,
            "apply_uncertainty": False,
            "apply_paradigm": False,
            "uncertainty_info": {},
            "paradigm_info": {},
            "reason": "Invariant Truth detected (Physical/Math Constant) - Phase 4 bypass active",
            "is_invariant": True,
            "is_baseline": False,
            "temporal_op": {"bias": "neutral", "window": (None, None), "operator_found": None}
        }
    
    # Detect markers
    uncertainty_info = detect_query_uncertainty_markers(query)
    paradigm_info = detect_query_paradigm_markers(query)
    
    # CRITICAL GATE 2: Check if query wants baseline/foundational paradigm
    is_baseline = is_baseline_query(query)
    
    # CRITICAL GATE 3: Check temporal operators
    temporal_op = extract_temporal_operators(query)
    
    # NEW: If query mentions foundational domains (geometry, physics) but has no explicit
    # paradigm markers, we still need to apply paradigm checking to protect baseline answers
    query_lower = query.lower()
    foundational_domains = ["geometry", "physics", "mechanics", "mathematics", "math"]
    mentions_foundational_domain = any(domain in query_lower for domain in foundational_domains)
    
    # Filter out "approximately" from uncertainty markers for physical constants
    # "approximately" is precision language, not uncertainty, for constants
    if uncertainty_info.get("has_uncertainty"):
        markers = uncertainty_info.get("markers_found", [])
        precision_words = ["approximately", "roughly", "around", "about", "nearly", "almost"]
        if any(p in markers for p in precision_words):
            # Check if this is a statement about a constant (has numbers)
            if re.search(r'\d+', query):
                # Remove precision markers, keep only true uncertainty
                filtered_markers = [m for m in markers if m not in precision_words]
                uncertainty_info["markers_found"] = filtered_markers
                uncertainty_info["has_uncertainty"] = len(filtered_markers) > 0
    
    apply_uncertainty = uncertainty_info["has_uncertainty"]
    apply_paradigm = paradigm_info["has_paradigm"] or (mentions_foundational_domain and is_baseline)
    apply_epistemic = apply_uncertainty or apply_paradigm
    
    # Build reason string
    if not apply_epistemic:
        reason = "Query is straightforward (no uncertainty/paradigm markers) - preserve Phase 2 score"
    else:
        parts = []
        if apply_uncertainty:
            parts.append(f"uncertainty markers: {uncertainty_info['markers_found']}")
        if apply_paradigm:
            if paradigm_info["has_paradigm"]:
                parts.append(f"paradigm markers: {paradigm_info['markers_found']}")
            elif mentions_foundational_domain:
                parts.append(f"baseline paradigm guard active (foundational domain detected)")
        reason = "Query has epistemic markers - " + "; ".join(parts)
    
    return {
        "apply_epistemic": apply_epistemic,
        "apply_uncertainty": apply_uncertainty,
        "apply_paradigm": apply_paradigm,
        "uncertainty_info": uncertainty_info,
        "paradigm_info": paradigm_info,
        "reason": reason,
        "is_invariant": is_invariant,
        "is_baseline": is_baseline,
        "temporal_op": temporal_op
    }


# Test cases
if __name__ == "__main__":
    test_queries = [
        "Who was the Prime Minister of the United Kingdom in 2017?",  # Clean
        "Who was probably PM in 2017?",  # Uncertainty
        "According to British constitutional law, who was PM in 2017?",  # Paradigm
        "What is approximately 5 ± 2?",  # Numerical uncertainty
        "Who might have been CEO?",  # Uncertainty
        "In quantum mechanics, what is the uncertainty principle?",  # Paradigm
    ]
    
    for query in test_queries:
        result = should_apply_epistemic_modulation(query)
        print(f"\nQuery: {query}")
        print(f"Apply epistemic: {result['apply_epistemic']}")
        print(f"Reason: {result['reason']}")
