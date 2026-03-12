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
    """
    uncertainty_info = detect_query_uncertainty_markers(query)
    paradigm_info = detect_query_paradigm_markers(query)
    
    apply_uncertainty = uncertainty_info["has_uncertainty"]
    apply_paradigm = paradigm_info["has_paradigm"]
    apply_epistemic = apply_uncertainty or apply_paradigm
    
    # Build reason string
    if not apply_epistemic:
        reason = "Query is straightforward (no uncertainty/paradigm markers) - preserve Phase 2 score"
    else:
        parts = []
        if apply_uncertainty:
            parts.append(f"uncertainty markers: {uncertainty_info['markers_found']}")
        if apply_paradigm:
            parts.append(f"paradigm markers: {paradigm_info['markers_found']}")
        reason = "Query has epistemic markers - " + "; ".join(parts)
    
    return {
        "apply_epistemic": apply_epistemic,
        "apply_uncertainty": apply_uncertainty,
        "apply_paradigm": apply_paradigm,
        "uncertainty_info": uncertainty_info,
        "paradigm_info": paradigm_info,
        "reason": reason
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
