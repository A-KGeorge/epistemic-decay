"""
Phase 4: Uncertainty Decay (Bayesian Confidence Updating)
Implements Section 2.3 of the Dynamic Epistemic Decay Framework

Key principle: Confidence erodes as estimates are refined by new evidence.
Unlike temporal decay, uncertainty decay is Bayesian - updates based on evidence.

Mathematical form: C(evidence) = P(fact | prior) × P(evidence | fact) / P(evidence)

Stacking: Multiplicative across independent evidence sources
If component A has confidence 0.9 and component B has 0.8, combined = 0.72
"""

import re
import spacy
from typing import List, Dict, Tuple, Optional
import numpy as np

nlp = spacy.load("en_core_web_sm")

# Epistemic markers indicating uncertainty
UNCERTAINTY_MARKERS = {
    # High uncertainty (low confidence)
    "allegedly": 0.3,
    "supposedly": 0.4,
    "might": 0.5,
    "may": 0.5,
    "possibly": 0.5,
    "perhaps": 0.5,
    "could": 0.6,
    
    # Medium uncertainty
    "likely": 0.7,
    "probably": 0.7,
    "seems": 0.7,
    "appears": 0.7,
    "suggests": 0.7,
    "indicates": 0.75,
    
    # Estimation markers
    "estimate": 0.8,
    "estimated": 0.8,
    "approximately": 0.85,
    "roughly": 0.8,
    "around": 0.85,
    "about": 0.85,
    "circa": 0.8,
    
    # Belief/opinion markers  
    "believe": 0.6,
    "think": 0.6,
    "suspect": 0.5,
    "assume": 0.7,
    "hypothesize": 0.6,
    "speculate": 0.4,
    "claim": 0.6,
    
    # Confidence qualifiers
    "definitely": 0.95,
    "certainly": 0.95,
    "clearly": 0.9,
    "obviously": 0.9,
    "undoubtedly": 0.95,
}

# Evidence quality markers
EVIDENCE_QUALITY = {
    "proven": 0.95,
    "confirmed": 0.9,
    "verified": 0.9,
    "validated": 0.9,
    "demonstrated": 0.85,
    "observed": 0.85,
    "measured": 0.9,
    "tested": 0.85,
    
    # Weaker evidence
    "reported": 0.7,
    "claimed": 0.6,
    "alleged": 0.4,
    "rumored": 0.3,
    "unverified": 0.3,
    "unconfirmed": 0.4,
}

# Quantifier precision (affects uncertainty)
QUANTIFIER_PRECISION = {
    # Vague quantifiers
    "some": 0.5,
    "several": 0.6,
    "many": 0.6,
    "most": 0.7,
    "few": 0.6,
    
    # Precise quantifiers
    "all": 0.9,
    "every": 0.9,
    "none": 0.9,
    "exactly": 0.95,
}

# Temporal projection uncertainty (future predictions)
TEMPORAL_PROJECTION = {
    "will": 0.7,  # Definite future
    "will likely": 0.6,
    "expected to": 0.7,
    "projected to": 0.7,
    "anticipated": 0.65,
    "predicted": 0.6,
    "forecast": 0.6,
    "estimated to": 0.65,
    "scheduled": 0.8,
    "planned": 0.7,
}


def detect_uncertainty_markers(text: str, doc: spacy.tokens.Doc = None) -> List[Tuple[str, float]]:
    """
    Detect epistemic uncertainty markers in text.
    
    Args:
        text: Input text
        doc: Pre-parsed spaCy doc (optional)
    
    Returns:
        List of (marker, confidence_value) tuples
    """
    if doc is None:
        doc = nlp(text)
    
    markers = []
    text_lower = text.lower()
    lemmas = {token.lemma_.lower() for token in doc}
    
    # Check for single-word markers
    for marker, confidence in UNCERTAINTY_MARKERS.items():
        if marker in lemmas or marker in text_lower:
            markers.append((marker, confidence))
    
    # Check for evidence quality markers
    for marker, confidence in EVIDENCE_QUALITY.items():
        if marker in lemmas or marker in text_lower:
            markers.append((f"evidence:{marker}", confidence))
    
    # Check for quantifier precision
    for marker, confidence in QUANTIFIER_PRECISION.items():
        if marker in lemmas:
            markers.append((f"quantifier:{marker}", confidence))
    
    # Check for temporal projection
    for phrase, confidence in TEMPORAL_PROJECTION.items():
        if phrase in text_lower:
            markers.append((f"projection:{phrase}", confidence))
    
    return markers


def detect_numerical_uncertainty(text: str) -> List[Tuple[str, float]]:
    """
    Detect uncertainty from numerical expressions.
    
    Enhanced with Deepseek's recommendations:
    - Expanded patterns for ±, approximately, around, nearly
    - Better range detection (X-Y, X to Y, between X and Y)
    - Margin of error and confidence interval detection
    
    Patterns:
    - Ranges: "5-10 billion years" → moderate uncertainty
    - Plus/minus: "±10%" → quantified uncertainty  
    - Approximations: "~5 billion", "around 10", "nearly 100" → moderate uncertainty
    - Orders of magnitude: "millions" vs "5.2 million" → precision difference
    
    Returns:
        List of (pattern_type, confidence) tuples
    """
    uncertainties = []
    text_lower = text.lower()
    
    # Pattern 1: Plus/minus notation "±X" or "±X%"
    pm_pattern = r'[±]\s*(\d+(?:\.\d+)?)\s*%?'
    for match in re.finditer(pm_pattern, text):
        value = match.group(1)
        error_pct = float(value)
        # Assume % if < 100, otherwise absolute
        if error_pct <= 100 and '%' in match.group(0):
            confidence = max(0.5, 1.0 - (error_pct / 100))
        else:
            confidence = 0.8  # Absolute error, moderate uncertainty
        uncertainties.append((f"±{value}", confidence))
    
    # Pattern 1b: "plus or minus X"
    pm_text_pattern = r'plus\s+or\s+minus\s+(\d+(?:\.\d+)?)\s*%?'
    for match in re.finditer(pm_text_pattern, text_lower):
        value = match.group(1)
        uncertainties.append((f"plus_or_minus_{value}", 0.8))
    
    # Pattern 2: Ranges "X-Y", "X to Y", "between X and Y"
    range_patterns = [
        r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)',  # X-Y or X–Y
        r'(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)',  # X to Y
        r'between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)',  # between X and Y
        r'from\s+(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)',  # from X to Y
    ]
    
    for pattern in range_patterns:
        for match in re.finditer(pattern, text_lower):
            low = float(match.group(1))
            high = float(match.group(2))
            if high > 0 and high > low:
                range_width = (high - low) / high
                confidence = max(0.6, 1.0 - range_width)
                uncertainties.append((f"range:{low}-{high}", confidence))
    
    # Pattern 3: Approximation symbols and words "~", "≈", "approximately", "around", "about"
    approx_patterns = {
        r'[~≈]': ("~symbol", 0.85),
        r'\b(approximately|roughly)\b': ("approximately", 0.85),
        r'\baround\b': ("around", 0.85),
        r'\babout\b': ("about", 0.85),
        r'\bnearly\b': ("nearly", 0.88),
        r'\balmost\b': ("almost", 0.88),
        r'\bclose\s+to\b': ("close_to", 0.87),
        r'\bcirca\b': ("circa", 0.80),
        r'\bapprox\.?\b': ("approx", 0.85),
    }
    
    for pattern, (name, conf) in approx_patterns.items():
        if re.search(pattern, text_lower):
            uncertainties.append((name, conf))
    
    # Pattern 4: Vague magnitudes "millions", "billions" (no specific number)
    vague_magnitude = r'\b(millions|billions|trillions|thousands)\b(?!\s+of\s+\d)'
    if re.search(vague_magnitude, text_lower):
        uncertainties.append(("vague_magnitude", 0.7))
    
    # Pattern 5: Margin of error and confidence intervals (Deepseek recommendation)
    if re.search(r'\bmargin\s+of\s+error\b', text_lower):
        uncertainties.append(("margin_of_error", 0.75))
    
    if re.search(r'\bconfidence\s+interval\b', text_lower):
        uncertainties.append(("confidence_interval", 0.75))
    
    if re.search(r'\berror\s+bar', text_lower):
        uncertainties.append(("error_bar", 0.75))
    
    # Pattern 6: "up to X", "as many as X", "as much as X" (upper bound uncertainty)
    upper_bound_pattern = r'\b(up\s+to|as\s+many\s+as|as\s+much\s+as|at\s+most)\b'
    if re.search(upper_bound_pattern, text_lower):
        uncertainties.append(("upper_bound", 0.80))
    
    # Pattern 7: "at least X", "no less than X" (lower bound uncertainty)
    lower_bound_pattern = r'\b(at\s+least|no\s+less\s+than|minimum\s+of)\b'
    if re.search(lower_bound_pattern, text_lower):
        uncertainties.append(("lower_bound", 0.80))
    
    return uncertainties


def compute_base_confidence(text: str) -> Dict[str, any]:
    """
    Compute base confidence level from text analysis.
    
    Returns:
        {
            "base_confidence": float,  # Combined confidence score
            "uncertainty_markers": List[Tuple[str, float]],
            "numerical_uncertainty": List[Tuple[str, float]],
            "has_uncertainty": bool,
            "confidence_level": str  # "high", "medium", "low"
        }
    """
    doc = nlp(text)
    
    uncertainty_markers = detect_uncertainty_markers(text, doc)
    numerical_uncertainty = detect_numerical_uncertainty(text)
    
    # Multiplicative composition: confidence values multiply
    confidence = 1.0
    
    # Apply uncertainty markers (multiplicative)
    for marker, marker_conf in uncertainty_markers:
        confidence *= marker_conf
    
    # Apply numerical uncertainties (multiplicative)
    for pattern, pattern_conf in numerical_uncertainty:
        confidence *= pattern_conf
    
    # Classify confidence level
    if confidence >= 0.85:
        level = "high"
    elif confidence >= 0.65:
        level = "medium"
    else:
        level = "low"
    
    has_uncertainty = len(uncertainty_markers) > 0 or len(numerical_uncertainty) > 0
    
    return {
        "base_confidence": confidence,
        "uncertainty_markers": uncertainty_markers,
        "numerical_uncertainty": numerical_uncertainty,
        "has_uncertainty": has_uncertainty,
        "confidence_level": level
    }


def bayesian_update(prior: float, likelihood: float, evidence_strength: float = 0.8) -> float:
    """
    Simple Bayesian confidence update.
    
    Args:
        prior: Prior confidence in statement
        likelihood: P(evidence | statement true)
        evidence_strength: How strong the evidence is (0-1)
    
    Returns:
        Updated confidence (posterior)
    
    Simplified Bayes: posterior ∝ prior × likelihood
    """
    # Weighted update based on evidence strength
    posterior = prior * (evidence_strength * likelihood + (1 - evidence_strength))
    
    # Normalize to [0, 1]
    return min(1.0, max(0.0, posterior))


def compute_uncertainty_decay_score(statement: str, evidence_list: Optional[List[float]] = None) -> Dict[str, any]:
    """
    Compute uncertainty decay score for a statement.
    
    Args:
        statement: Knowledge statement text
        evidence_list: Optional list of evidence confidence values for updates
    
    Returns:
        {
            "initial_confidence": float,
            "final_confidence": float,  # After Bayesian updates if evidence provided
            "decay_type": "uncertainty",
            "composition": "multiplicative",
            "evidence_count": int,
            "confidence_level": str
        }
    """
    base = compute_base_confidence(statement)
    initial_conf = base["base_confidence"]
    
    # If evidence provided, apply Bayesian updates
    final_conf = initial_conf
    if evidence_list:
        for evidence_conf in evidence_list:
            final_conf = bayesian_update(final_conf, evidence_conf)
    
    # Classify final confidence
    if final_conf >= 0.85:
        level = "high"
    elif final_conf >= 0.65:
        level = "medium"
    else:
        level = "low"
    
    return {
        "initial_confidence": initial_conf,
        "final_confidence": final_conf,
        "decay_type": "uncertainty",
        "composition": "multiplicative",
        "evidence_count": len(evidence_list) if evidence_list else 0,
        "confidence_level": level,
        "debug_info": base
    }


# Test cases
if __name__ == "__main__":
    test_cases = [
        "The sun will likely explode in approximately 5 billion years",
        "Scientists estimate the age of the universe at 13.8 billion years",
        "The experiment allegedly showed positive results",
        "It is confirmed that water boils at 100°C at sea level",
        "The projected GDP growth is 2-3% for next year",
        "Some researchers believe climate change may accelerate",
        "The population is roughly 8 billion ± 2%",
    ]
    
    print("=" * 80)
    print("UNCERTAINTY DECAY TESTS")
    print("=" * 80)
    print()
    
    for statement in test_cases:
        result = compute_uncertainty_decay_score(statement)
        
        print(f"Statement: {statement}")
        print(f"Initial confidence: {result['initial_confidence']:.3f}")
        print(f"Confidence level: {result['confidence_level']}")
        print(f"Markers: {result['debug_info']['uncertainty_markers']}")
        print()
