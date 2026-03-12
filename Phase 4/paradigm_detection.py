"""
Phase 4: Paradigm Decay Detection
Implements Section 2.2 of the Dynamic Epistemic Decay Framework

Key principle: Facts get domain-scoped by theoretical frameworks.
Paradigm decay is NOT continuous erosion but step-function validity gating.

Mathematical form: C(context) = C₀ if context ∈ valid_paradigm_set, else 0

Examples:
- "F=ma describes planetary motion" → valid in Newtonian physics only
- "Parallel lines never meet" → valid in Euclidean geometry only  
- "In quantum mechanics, particles have wave properties" → quantum paradigm scope
"""

import re
import spacy
from typing import List, Dict, Set, Optional, Tuple

nlp = spacy.load("en_core_web_sm")

# Paradigm qualifier patterns
PARADIGM_QUALIFIERS = {
    # Explicit framework markers
    "according to", "within", "under", "in the context of", "from the perspective of",
    "in", "assuming", "given", "based on", "using", "following", "per",
    
    # Conditional framing
    "if we assume", "if we accept", "if", "when", "provided that", "granted that"
}

# Known theoretical frameworks and their domains
# EXPANDED per Deepseek's recommendation: use word vectors or small classifier
KNOWN_PARADIGMS = {
    # Physics paradigms
    "newtonian": ["newtonian mechanics", "newtonian physics", "classical mechanics", 
                  "newton's laws", "classical physics", "newtonian dynamics"],
    "relativistic": ["relativity", "special relativity", "general relativity", 
                     "einstein's theory", "relativistic physics", "relativistic mechanics",
                     "special theory of relativity", "general theory of relativity"],
    "quantum": ["quantum mechanics", "quantum physics", "quantum theory", 
                "quantum field theory", "qm", "quantum dynamics", "wave mechanics",
                "matrix mechanics", "quantum electrodynamics", "qed"],
    "thermodynamics": ["thermodynamics", "statistical mechanics", "thermal physics",
                       "heat transfer", "entropy", "thermodynamic equilibrium"],
    
    # Mathematics paradigms  
    "euclidean": ["euclidean geometry", "euclidean space", "flat geometry", 
                  "plane geometry", "euclid's geometry"],
    "non_euclidean": ["non-euclidean geometry", "hyperbolic geometry", 
                      "elliptic geometry", "curved space", "riemannian geometry",
                      "spherical geometry"],
    "standard_math": ["standard mathematics", "classical mathematics", 
                      "conventional math", "traditional mathematics"],
    "set_theory": ["set theory", "zermelo-fraenkel", "zfc", "axiomatic set theory"],
    "category_theory": ["category theory", "categorical", "functors", "morphisms"],
    "constructive_math": ["constructive mathematics", "intuitionism", "constructivism"],
    
    # Economics paradigms
    "neoclassical": ["neoclassical economics", "neoclassical theory", 
                     "rational actor model", "utility maximization"],
    "keynesian": ["keynesian economics", "keynesian theory", "keynes", 
                  "neo-keynesian", "new keynesian"],
    "austrian": ["austrian economics", "austrian school", "praxeology"],
    "marxian": ["marxian economics", "marxist economics", "marx", "dialectical materialism"],
    "behavioral": ["behavioral economics", "behavioral finance", "prospect theory"],
    
    # Biology/Medicine paradigms
    "germ_theory": ["germ theory", "infectious disease model", "pathogen theory"],
    "evolutionary": ["evolutionary theory", "darwinian evolution", "natural selection",
                     "modern synthesis", "neo-darwinism"],
    "cell_theory": ["cell theory", "cellular biology", "cytology"],
    "genetics": ["mendelian genetics", "molecular genetics", "genomics"],
    
    # Philosophy paradigms
    "empiricist": ["empiricism", "empirical philosophy", "sensory experience"],
    "rationalist": ["rationalism", "rationalist philosophy", "innate ideas"],
    "materialist": ["materialism", "physicalism", "physical monism"],
    "idealist": ["idealism", "idealist philosophy", "mental monism"],
    "pragmatist": ["pragmatism", "pragmatic philosophy", "practical consequences"],
    "phenomenology": ["phenomenology", "phenomenological", "lived experience"],
    "existentialism": ["existentialism", "existentialist philosophy"],
    
    # Computer Science paradigms
    "procedural": ["procedural programming", "imperative programming"],
    "functional": ["functional programming", "fp", "lambda calculus", "pure functions"],
    "object_oriented": ["object-oriented programming", "oop", "object oriented"],
    "declarative": ["declarative programming", "logic programming", "prolog"],
    
    # Law/Legal paradigms
    "common_law": ["common law", "case law", "precedent-based"],
    "civil_law": ["civil law", "code-based law", "statutory law"],
    "constitutional": ["constitutional law", "constitutional framework"],
    
    # Psychology paradigms
    "behaviorist": ["behaviorism", "behavioral psychology", "stimulus-response"],
    "cognitive": ["cognitive psychology", "information processing", "cognitivism"],
    "psychoanalytic": ["psychoanalysis", "psychoanalytic theory", "freudian"],
    "humanistic": ["humanistic psychology", "self-actualization"],
    
    # Sociology paradigms
    "functionalist": ["structural functionalism", "functionalist sociology"],
    "conflict": ["conflict theory", "marxist sociology"],
    "symbolic_interactionist": ["symbolic interactionism", "interactionist"],
}

# Framework-specific terminology that implies paradigm scope
# EXPANDED per Deepseek's recommendation
PARADIGM_TERMS = {
    "newtonian": {"inertia", "momentum", "gravitational constant", "absolute time", 
                  "absolute space", "galilean transformation", "action-reaction",
                  "conservation of momentum", "force equals mass times acceleration"},
    "relativistic": {"spacetime", "light cone", "time dilation", "length contraction",
                     "lorentz transformation", "invariant mass", "c", "speed of light",
                     "proper time", "worldline", "minkowski space", "covariant"},
    "quantum": {"wave function", "uncertainty principle", "superposition", "entanglement",
                "quantization", "planck constant", "eigenstate", "observable", 
                "hamiltonian", "schrödinger", "heisenberg", "wave-particle duality",
                "quantum state", "measurement problem", "decoherence", "spin"},
    "thermodynamics": {"entropy", "enthalpy", "gibbs free energy", "carnot cycle",
                       "second law", "boltzmann", "partition function", "heat engine"},
    "euclidean": {"parallel postulate", "straight line", "flat plane", "pythagorean",
                  "angles sum to 180", "euclid", "planar"},
    "non_euclidean": {"geodesic", "curvature", "hyperbolic", "elliptic", "riemann",
                      "gaussian curvature", "parallel transport"},
    "set_theory": {"axiom of choice", "power set", "ordinal", "cardinal", "zfc"},
    "category_theory": {"functor", "natural transformation", "morphism", "commutative diagram"},
    "neoclassical": {"utility function", "marginal utility", "equilibrium", "supply and demand",
                     "rational expectations", "pareto efficiency"},
    "keynesian": {"aggregate demand", "multiplier effect", "liquidity trap", "sticky prices",
                  "animal spirits", "propensity to consume"},
    "austrian": {"praxeology", "subjective value", "time preference", "catallactics"},
    "evolutionary": {"natural selection", "fitness", "adaptation", "mutation", "speciation",
                     "common descent", "gene pool", "allele frequency"},
    "genetics": {"mendelian", "dominant", "recessive", "genotype", "phenotype", "dna", 
                 "gene expression", "allele"},
    "behaviorist": {"stimulus", "response", "conditioning", "reinforcement", "punishment",
                    "operant", "pavlovian"},
    "cognitive": {"schema", "semantic network", "working memory", "encoding", "retrieval"},
    "psychoanalytic": {"unconscious", "id", "ego", "superego", "defense mechanism", 
                       "repression", "transference"},
    "functional_prog": {"pure function", "immutable", "lambda", "higher-order function",
                        "map", "reduce", "fold", "monad"},
    "object_oriented": {"class", "inheritance", "polymorphism", "encapsulation", "abstraction",
                        "interface", "method"},
}


def detect_explicit_paradigm_qualifiers(text: str, doc: spacy.tokens.Doc = None) -> List[Tuple[str, str]]:
    """
    Detect explicit paradigm qualifiers like "according to", "within", "in X".
    
    Args:
        text: Input text
        doc: Pre-parsed spaCy doc (optional, will parse if not provided)
    
    Returns:
        List of (qualifier_type, matched_text) tuples
    """
    if doc is None:
        doc = nlp(text)
    
    qualifiers = []
    text_lower = text.lower()
    
    # Pattern 1: "according to [framework]"
    pattern1 = r'\b(?:according to|within|under|in the context of|from the perspective of)\s+([a-z\s]+?)(?:\s+theory|\s+mechanics|\s+physics|\s+geometry|\s+economics|,|\.|\s+the|\s+a)'
    for match in re.finditer(pattern1, text_lower):
        framework = match.group(1).strip()
        qualifiers.append(("explicit_qualifier", f"{match.group(0).split()[0:2]} {framework}"))
    
    # Pattern 2: "in [framework]" (more specific)
    pattern2 = r'\bin\s+(newtonian|euclidean|quantum|classical|relativistic|keynesian|neoclassical)\s+(?:mechanics|physics|geometry|economics|theory)'
    for match in re.finditer(pattern2, text_lower):
        qualifiers.append(("framework_scope", match.group(0)))
    
    # Pattern 3: Conditional framing "if we assume", "assuming"
    pattern3 = r'\b(?:if we assume|if we accept|assuming|given|provided that|granted that)\s+([^,\.]+)'
    for match in re.finditer(pattern3, text_lower):
        assumption = match.group(1).strip()
        qualifiers.append(("conditional", f"assuming {assumption}"))
    
    return qualifiers


def detect_implicit_paradigm_scope(text: str, doc: spacy.tokens.Doc = None) -> List[Tuple[str, str]]:
    """
    Detect implicit paradigm scope through framework-specific terminology.
    
    Args:
        text: Input text
        doc: Pre-parsed spaCy doc (optional)
    
    Returns:
        List of (paradigm_name, term_matched) tuples
    """
    if doc is None:
        doc = nlp(text)
    
    text_lower = text.lower()
    lemmas = {token.lemma_.lower() for token in doc}
    
    detected_paradigms = []
    
    # Check for paradigm-specific terms
    for paradigm, terms in PARADIGM_TERMS.items():
        matched_terms = lemmas & terms
        if matched_terms:
            for term in matched_terms:
                detected_paradigms.append((paradigm, term))
    
    # Check for explicit paradigm names
    for paradigm, variants in KNOWN_PARADIGMS.items():
        for variant in variants:
            if variant in text_lower:
                detected_paradigms.append((paradigm, variant))
    
    return detected_paradigms


def extract_paradigm_context(text: str) -> Dict[str, any]:
    """
    Full paradigm context extraction combining explicit and implicit detection.
    
    Returns:
        {
            "has_paradigm_scope": bool,
            "explicit_qualifiers": List[Tuple[str, str]],
            "implicit_paradigms": List[Tuple[str, str]],
            "paradigm_set": Set[str],  # Union of all detected paradigms
            "is_universally_scoped": bool,  # True if no paradigm limits detected
            "validity_function": "step"  # Always step function for paradigm decay
        }
    """
    doc = nlp(text)
    
    explicit = detect_explicit_paradigm_qualifiers(text, doc)
    implicit = detect_implicit_paradigm_scope(text, doc)
    
    paradigm_set = set()
    
    # Extract paradigm names from explicit qualifiers
    for _, matched_text in explicit:
        for paradigm, variants in KNOWN_PARADIGMS.items():
            if any(variant in matched_text.lower() for variant in variants):
                paradigm_set.add(paradigm)
    
    # Add implicit paradigms
    for paradigm, _ in implicit:
        paradigm_set.add(paradigm)
    
    has_scope = len(explicit) > 0 or len(implicit) > 0
    
    return {
        "has_paradigm_scope": has_scope,
        "explicit_qualifiers": explicit,
        "implicit_paradigms": implicit,
        "paradigm_set": paradigm_set,
        "is_universally_scoped": not has_scope,
        "validity_function": "step"
    }


def check_paradigm_validity(statement_paradigms: Set[str], query_paradigms: Set[str]) -> Tuple[bool, float]:
    """
    Check if statement is valid in query context using conjunctive composition.
    
    Paradigm decay stacks conjunctively: a statement is valid only within the 
    intersection of all its required paradigm contexts.
    
    Args:
        statement_paradigms: Set of paradigms statement requires
        query_paradigms: Set of paradigms in query context
    
    Returns:
        (is_valid, confidence)
        - is_valid: True if statement_paradigms ⊆ query_paradigms
        - confidence: 1.0 if valid, 0.0 if invalid (step function)
    """
    # If statement has no paradigm scope, it's universally valid
    if not statement_paradigms:
        return True, 1.0
    
    # If query has no paradigm context specified, assume universal context
    # (accept all paradigm-scoped statements)
    if not query_paradigms:
        return True, 1.0
    
    # Conjunctive: statement requires ALL its paradigms to be present in query
    is_valid = statement_paradigms.issubset(query_paradigms)
    
    # Step function: full confidence if valid, zero if invalid
    confidence = 1.0 if is_valid else 0.0
    
    return is_valid, confidence


def compute_paradigm_decay_score(statement: str, query: str) -> Dict[str, any]:
    """
    Compute paradigm decay score for statement given query context.
    
    Args:
        statement: Knowledge statement text
        query: Query text (provides paradigm context)
    
    Returns:
        {
            "statement_paradigms": Set[str],
            "query_paradigms": Set[str],
            "is_valid": bool,
            "confidence": float,  # 1.0 or 0.0 (step function)
            "paradigm_mismatch": bool,
            "matched_paradigms": Set[str],
            "debug_info": Dict
        }
    """
    statement_ctx = extract_paradigm_context(statement)
    query_ctx = extract_paradigm_context(query)
    
    statement_paradigms = statement_ctx["paradigm_set"]
    query_paradigms = query_ctx["paradigm_set"]
    
    is_valid, confidence = check_paradigm_validity(statement_paradigms, query_paradigms)
    
    matched = statement_paradigms & query_paradigms
    
    return {
        "statement_paradigms": statement_paradigms,
        "query_paradigms": query_paradigms,
        "is_valid": is_valid,
        "confidence": confidence,
        "paradigm_mismatch": not is_valid,
        "matched_paradigms": matched,
        "debug_info": {
            "statement_context": statement_ctx,
            "query_context": query_ctx
        }
    }


# Test cases for validation
if __name__ == "__main__":
    test_cases = [
        ("F=ma describes planetary motion", "What governs planetary motion?"),
        ("In Newtonian mechanics, F=ma describes force", "How does force work in classical physics?"),
        ("Time dilation occurs near massive objects", "What happens to time in relativity?"),
        ("Parallel lines never meet", "Do parallel lines meet?"),
        ("In Euclidean geometry, parallel lines never meet", "Do parallel lines meet?"),
        ("The wave function collapses upon measurement", "What happens during measurement?"),
    ]
    
    print("=" * 80)
    print("PARADIGM DECAY DETECTION TESTS")
    print("=" * 80)
    print()
    
    for statement, query in test_cases:
        result = compute_paradigm_decay_score(statement, query)
        
        print(f"Statement: {statement}")
        print(f"Query: {query}")
        print(f"Statement paradigms: {result['statement_paradigms']}")
        print(f"Query paradigms: {result['query_paradigms']}")
        print(f"Valid: {result['is_valid']} (confidence: {result['confidence']})")
        print(f"Paradigm mismatch: {result['paradigm_mismatch']}")
        print()
