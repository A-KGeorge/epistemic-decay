"""
Phase 2: Compositional Stacking and Contamination Rules
Implements Section 3.1 and 2.4 of the Dynamic Epistemic Decay Framework

Key principle: Zero decay is fragile. A single contaminating component 
eliminates zero-decay status for the entire sentence.
"""

import re
import spacy
from constants import DECAY_RATES, TEMPORAL_MARKERS

nlp = spacy.load("en_core_web_sm")

# Contamination markers
MORTAL_ENTITIES = {"PERSON"}  # Living people introduce mortality decay
INSTITUTIONAL_ENTITIES = {"ORG"}  # Organizations introduce succession decay
EPISTEMIC_QUALIFIERS = {
    "estimate", "think", "believe", "suggest", "claim",
    "hypothesize", "speculate", "assume", "suspect"
}


def has_zero_decay_component(doc):
    """
    Check if sentence contains mathematical/logical truth markers.
    
    Returns: (has_component, component_type)
    """
    math_markers = {"equal", "equals", "plus", "minus", "sum", "product", 
                   "theorem", "proof", "axiom", "constant", "formula",
                   "pi", "euler", "phi", "infinity"}  # named mathematical constants
    
    lemmas = {token.lemma_.lower() for token in doc}
    
    if lemmas & math_markers:
        return True, "MATHEMATICAL"
    
    # Check for mathematical equations with symbols
    text = doc.text.lower()
    MATH_PATTERNS = ["=", "+", "×", "÷", "²", "³", "π", "∞", "√"]
    if any(pattern in text for pattern in MATH_PATTERNS):
        return True, "MATHEMATICAL"
    
    # Check for high-precision numbers (4+ decimal places)
    # Numbers like 3.14159 are almost certainly mathematical constants
    MATH_NUMBER_PATTERN = r'\d+\.\d{4,}'
    if re.search(MATH_NUMBER_PATTERN, text):
        return True, "MATHEMATICAL"
    
    return False, None


def detect_contaminants(doc):
    """
    Detect contaminating elements that eliminate zero-decay status.
    
    Returns: (is_contaminated, contaminant_list)
    """
    contaminants = []
    tokens_lower = {token.text.lower() for token in doc}
    lemmas = {token.lemma_.lower() for token in doc}
    
    # 1. Temporal markers contaminate
    if tokens_lower & TEMPORAL_MARKERS:
        contaminants.append(("TEMPORAL_MARKER", list(tokens_lower & TEMPORAL_MARKERS)[0]))
    
    # 2. Mortal proper nouns contaminate
    for ent in doc.ents:
        if ent.label_ in MORTAL_ENTITIES:
            contaminants.append(("MORTAL_ENTITY", ent.text))
        elif ent.label_ in INSTITUTIONAL_ENTITIES:
            contaminants.append(("INSTITUTIONAL_ENTITY", ent.text))
    
    # 3. Epistemic qualifiers contaminate (uncertainty injection)
    if lemmas & EPISTEMIC_QUALIFIERS:
        contaminants.append(("EPISTEMIC_QUALIFIER", list(lemmas & EPISTEMIC_QUALIFIERS)[0]))
    
    # 4. Present tense with institutional/mortal subjects
    for token in doc:
        if token.dep_ == "ROOT" and token.morph.get("Tense") == ["Pres"]:
            # Check if subject is a person or organization
            subject = None
            for child in token.children:
                if child.dep_ in {"nsubj", "nsubjpass"}:
                    subject = child
                    break
            
            if subject and subject.ent_type_ in MORTAL_ENTITIES | INSTITUTIONAL_ENTITIES:
                if ("MORTAL_ENTITY", subject.text) not in contaminants and \
                   ("INSTITUTIONAL_ENTITY", subject.text) not in contaminants:
                    contaminants.append(("PRESENT_TENSE_MORTAL", subject.text))
    
    return len(contaminants) > 0, contaminants


def check_fragility_contamination(text):
    """
    Detects if a Zero-Decay component is contaminated by high-decay markers.
    
    Implements: sentence.λ0 = ∀(component.λ0) AND no contamination
    
    Returns: (is_contaminated, status, details)
    """
    doc = nlp(text)
    
    has_zero, zero_type = has_zero_decay_component(doc)
    is_contaminated, contaminants = detect_contaminants(doc)
    
    if has_zero and is_contaminated:
        # Contamination Rule: One impure component eliminates zero-decay status
        return True, "CONTAMINATED", {
            "zero_component": zero_type,
            "contaminants": contaminants
        }
    elif has_zero and not is_contaminated:
        return False, "PURE_ZERO_DECAY", {
            "zero_component": zero_type,
            "contaminants": []
        }
    else:
        return False, "STANDARD_DECAY", {
            "zero_component": None,
            "contaminants": contaminants if is_contaminated else []
        }


def compute_compositional_decay(text, base_decay_rate):
    """
    Apply compositional stacking rules to adjust decay rate.
    
    If zero-decay component is contaminated, override with contaminant's decay rate.
    Otherwise, return base rate.
    
    Args:
        text: The sentence to analyze
        base_decay_rate: The decay rate from category classification
    
    Returns:
        (final_decay_rate, explanation)
    """
    is_contaminated, status, details = check_fragility_contamination(text)
    
    if status == "PURE_ZERO_DECAY":
        return DECAY_RATES["MATHEMATICAL_TRUTH"], f"Pure zero decay: {details['zero_component']}"
    
    elif status == "CONTAMINATED":
        # Find highest decay contaminant
        contaminant_types = [c[0] for c in details["contaminants"]]
        
        if "TEMPORAL_MARKER" in contaminant_types:
            # Temporal markers amplify base rate
            amplified = base_decay_rate * 2.1
            return amplified, f"Contaminated by temporal marker (base × 2.1)"
        
        elif "MORTAL_ENTITY" in contaminant_types or "PRESENT_TENSE_MORTAL" in contaminant_types:
            # Mortal entities introduce institutional leadership decay
            contaminated_rate = max(base_decay_rate, DECAY_RATES["INSTITUTIONAL_LEADERSHIP"])
            return contaminated_rate, f"Contaminated by mortal entity"
        
        elif "EPISTEMIC_QUALIFIER" in contaminant_types:
            # Epistemic qualifiers introduce uncertainty
            contaminated_rate = max(base_decay_rate, DECAY_RATES["DEFAULT"])
            return contaminated_rate, f"Contaminated by epistemic qualifier"
        
        else:
            return base_decay_rate, f"Contaminated but using base rate"
    
    else:
        # STANDARD_DECAY: No zero-decay component, but check for temporal markers
        # For temporal facts (non-mathematical content), temporal markers are
        # FRESHNESS SIGNALS that indicate up-to-date information, not contamination
        contaminant_types = [c[0] for c in details["contaminants"]]
        
        if "TEMPORAL_MARKER" in contaminant_types:
            # Temporal markers in factual content indicate freshness/recency
            # Reduce decay rate to reflect higher confidence in current information
            reduced = base_decay_rate * 0.5
            return reduced, f"Temporal freshness signal (base × 0.5)"
        
        return base_decay_rate, "Standard decay (no zero-decay component)"


# Test cases for Phase 2
if __name__ == "__main__":
    test_cases = [
        "2 + 2 = 4",
        "The current Pope knows 2 + 2 = 4",
        "Scientists estimate pi is 3.14159",
        "The Pythagorean theorem states a² + b² = c²",
        "Einstein proved E=mc²",
        "Tim Cook believes the formula works",
    ]
    
    print("=" * 80)
    print("COMPOSITIONAL CONTAMINATION TEST")
    print("=" * 80)
    print()
    
    for case in test_cases:
        is_contam, status, details = check_fragility_contamination(case)
        final_rate, explanation = compute_compositional_decay(case, DECAY_RATES["DEFAULT"])
        
        print(f"Text: {case}")
        print(f"  Status: {status}")
        if details["contaminants"]:
            print(f"  Contaminants: {details['contaminants']}")
        print(f"  Final decay rate: {final_rate:.4f}")
        print(f"  Explanation: {explanation}")
        print()
