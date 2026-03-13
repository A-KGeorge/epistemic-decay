"""
Phase 4: Multi-Dimensional Decay Integration
Unified framework combining all four decay dimensions

Implements complete Dynamic Epistemic Decay Framework:
- Temporal decay (λt): Exponential time-based erosion
- Paradigm decay (λp): Step-function validity scoping
- Uncertainty decay (λu): Bayesian confidence updating
- Dependency decay (λd): Graph-propagated stability

Composition rules:
- Temporal: Additive stacking across components
- Paradigm: Conjunctive (valid only in intersection of all required paradigms)
- Uncertainty: Multiplicative across independent sources
- Dependency: Graph-computed from typed edges + transmission coefficients
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Phase 2'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Phase 3'))

import numpy as np
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
import spacy

# Import Phase 2 components
from constants import DECAY_RATES
from query_intent import classify_temporal_intent

# Import Phase 4 components  
from paradigm_detection import extract_paradigm_context, check_paradigm_validity, compute_paradigm_decay_score
from uncertainty_decay import compute_uncertainty_decay_score, compute_base_confidence
from dependency_graph import DependencyGraph, KnowledgeNode, EdgeType, DecayType

nlp = spacy.load("en_core_web_sm")


class MultiDimensionalDecayVector:
    """
    Complete decay vector for a knowledge statement.
    
    Attributes:
        temporal: λt (exponential decay rate)
        paradigm: λp (set of required paradigms for validity)
        uncertainty: λu (confidence level, 0-1)
        dependency: λd (graph-propagated decay)
        zero_decay: λ0 (fragile zero-decay flag)
    """
    
    def __init__(self,
                 temporal: float = 0.0,
                 paradigm_set: Set[str] = None,
                 uncertainty: float = 1.0,
                 dependency: float = 0.0,
                 is_zero_decay: bool = False):
        self.temporal = temporal  # λt
        self.paradigm_set = paradigm_set or set()  # λp (set-based, not scalar)
        self.uncertainty = uncertainty  # λu (confidence 0-1, higher = less uncertain)
        self.dependency = dependency  # λd
        self.is_zero_decay = is_zero_decay  # λ0 (fragile)
    
    def __repr__(self):
        return (f"DecayVector(λt={self.temporal:.4f}, "
                f"λp={self.paradigm_set}, "
                f"λu={self.uncertainty:.3f}, "
                f"λd={self.dependency:.4f}, "
                f"λ0={self.is_zero_decay})")


def analyze_statement_decay(text: str, acquired_date: Optional[datetime] = None) -> MultiDimensionalDecayVector:
    """
    Full multi-dimensional decay analysis of a knowledge statement.
    
    Args:
        text: Knowledge statement text
        acquired_date: When statement was acquired (for temporal decay)
    
    Returns:
        MultiDimensionalDecayVector with all four dimensions analyzed
    """
    doc = nlp(text)
    
    # 1. Temporal decay (λt) - from Phase 2
    temporal_intent = classify_temporal_intent(text)
    temporal_decay = temporal_intent.get("decay_rate", DECAY_RATES["DEFAULT"])
    
    # 2. Paradigm decay (λp)
    paradigm_ctx = extract_paradigm_context(text)
    paradigm_set = paradigm_ctx["paradigm_set"]
    
    # 3. Uncertainty decay (λu)
    uncertainty_result = compute_base_confidence(text)
    uncertainty_confidence = uncertainty_result["base_confidence"]
    
    # 4. Zero decay check (λ0 fragility)
    is_zero = (
        temporal_intent.get("status") == "PURE_ZERO_DECAY" and
        not paradigm_ctx["has_paradigm_scope"] and
        uncertainty_confidence >= 0.95
    )
    
    # If zero decay detected, override other dimensions
    if is_zero:
        temporal_decay = 0.0
        paradigm_set = set()
        uncertainty_confidence = 1.0
    
    return MultiDimensionalDecayVector(
        temporal=temporal_decay,
        paradigm_set=paradigm_set,
        uncertainty=uncertainty_confidence,
        dependency=0.0,  # Computed from graph later
        is_zero_decay=is_zero
    )


def compute_final_confidence(decay_vector: MultiDimensionalDecayVector,
                            days_elapsed: float,
                            query_paradigm_set: Set[str] = None,
                            query_text: str = "") -> Dict[str, any]:
    """
    Compute final confidence score combining all decay dimensions.
    
    Composition rules per dimension:
    - Temporal: C(t) = C₀ × e^(-λt × Δt)
    - Paradigm: C = C₀ if paradigms valid, else 0 (step function)
    - Uncertainty: C = base_confidence (already multiplicative from markers)
    - Dependency: C_effective = C × (1 - λd)
    
   Args:
        decay_vector: Multi-dimensional decay vector
        days_elapsed: Days since acquisition
        query_paradigm_set: Paradigm context from query
        query_text: Full query text (for baseline paradigm guard)
    
    Returns:
        {
            "final_confidence": float,
            "component_scores": Dict[str, float],
            "paradigm_valid": bool,
            "decay_breakdown": Dict
        }
    """
    # Zero decay fast path
    if decay_vector.is_zero_decay:
        return {
            "final_confidence": 1.0,
            "component_scores": {
                "temporal": 1.0,
                "paradigm": 1.0,
                "uncertainty": 1.0,
                "dependency": 1.0
            },
            "paradigm_valid": True,
            "decay_breakdown": {"status": "PURE_ZERO_DECAY"}
        }
    
    # 1. Temporal component: exponential decay
    temporal_conf = np.exp(-decay_vector.temporal * days_elapsed)
    
    # 2. Paradigm component: step function (with baseline guard)
    paradigm_valid, paradigm_conf = check_paradigm_validity(
        decay_vector.paradigm_set, 
        query_paradigm_set or set(),
        query_text=query_text
    )
    
    # 3. Uncertainty component: already computed confidence
    uncertainty_conf = decay_vector.uncertainty
    
    # 4. Dependency component: reduce confidence by propagated decay
    dependency_conf = 1.0 - min(decay_vector.dependency, 1.0)
    
    # Combine: multiply all components (conjunctive composition)
    final_confidence = (
        temporal_conf *
        paradigm_conf *
        uncertainty_conf *
        dependency_conf
    )
    
    return {
        "final_confidence": final_confidence,
        "component_scores": {
            "temporal": temporal_conf,
            "paradigm": paradigm_conf,
            "uncertainty": uncertainty_conf,
            "dependency": dependency_conf
        },
        "paradigm_valid": paradigm_valid,
        "decay_breakdown": {
            "temporal_decay_rate": decay_vector.temporal,
            "paradigm_set": decay_vector.paradigm_set,
            "uncertainty_level": decay_vector.uncertainty,
            "dependency_decay": decay_vector.dependency,
            "days_elapsed": days_elapsed
        }
    }


def score_document_with_full_decay(query: str, 
                                   query_vec: np.ndarray,
                                   doc_text: str,
                                   doc_vec: np.ndarray,
                                   doc_acquired: datetime,
                                   dependency_graph: Optional[DependencyGraph] = None,
                                   doc_id: Optional[str] = None) -> Dict[str, any]:
    """
    Complete document scoring with full multi-dimensional decay framework.
    
    Args:
        query: Query text
        query_vec: Query embedding vector
        doc_text: Document text
        doc_vec: Document embedding vector
        doc_acquired: Document acquisition date
        dependency_graph: Optional dependency graph for λd computation
        doc_id: Document ID (for graph lookup)
    
    Returns:
        {
            "base_score": float,  # Cosine similarity
            "final_score": float,  # Decay-adjusted score
            "decay_vector": MultiDimensionalDecayVector,
            "confidence_breakdown": Dict,
            "strategy": str
        }
    """
    # Base semantic similarity
    base_score = np.dot(query_vec, doc_vec) / (
        np.linalg.norm(query_vec) * np.linalg.norm(doc_vec)
    )
    
    # Analyze document decay
    decay_vector = analyze_statement_decay(doc_text, doc_acquired)
    
    # Add dependency decay if graph provided
    if dependency_graph and doc_id:
        stability = dependency_graph.compute_stability_score(doc_id)
        if stability:
            decay_vector.dependency = stability.get("effective_decay", 0.0)
    
    # Compute time elapsed
    now = datetime.now()
    days_elapsed = (now - doc_acquired).days if doc_acquired else 0
    
    # Extract query paradigm context
    query_paradigm_ctx = extract_paradigm_context(query)
    query_paradigm_set = query_paradigm_ctx["paradigm_set"]
    
    # Compute final confidence
    confidence_result = compute_final_confidence(
        decay_vector,
        days_elapsed,
        query_paradigm_set
    )
    
    # Apply confidence multiplier to base score
    final_score = base_score * confidence_result["final_confidence"]
    
    # Determine strategy
    if decay_vector.is_zero_decay:
        strategy = "zero_decay"
    elif confidence_result["paradigm_valid"] == False:
        strategy = "paradigm_rejection"
    elif decay_vector.dependency > 0.5:
        strategy = "dependency_unstable"
    elif days_elapsed > 1000 and decay_vector.temporal > 0.001:
        strategy = "temporal_decay"
    else:
        strategy = "multi_dimensional_decay"
    
    return {
        "base_score": base_score,
        "final_score": final_score,
        "decay_vector": decay_vector,
        "confidence_breakdown": confidence_result,
        "strategy": strategy,
        "days_elapsed": days_elapsed
    }


# Test cases
if __name__ == "__main__":
    print("=" * 80)
    print("MULTI-DIMENSIONAL DECAY INTEGRATION TEST")
    print("=" * 80)
    print()
    
    test_statements = [
        ("2 + 2 = 4", "PURE_ZERO_DECAY"),
        ("The current Pope is Francis", "HIGH_TEMPORAL_DECAY"),
        ("In Newtonian mechanics, F=ma", "PARADIGM_SCOPED"),
        ("Scientists estimate the sun will last ~5 billion years", "UNCERTAINTY_DECAY"),
        ("Water boils at 100°C at sea level", "LOW_TEMPORAL_DECAY"),
        ("The CEO of Amazon might be Andy Jassy", "UNCERTAINTY + TEMPORAL"),
    ]
    
    for statement, expected_category in test_statements:
        # Analyze with 1000 days elapsed
        doc_acquired = datetime.now() - timedelta(days=1000)
        decay_vector = analyze_statement_decay(statement, doc_acquired)
        
        confidence_result = compute_final_confidence(
            decay_vector,
            days_elapsed=1000,
            query_paradigm_set=set()
        )
        
        print(f"Statement: {statement}")
        print(f"Expected: {expected_category}")
        print(f"Decay vector: {decay_vector}")
        print(f"Final confidence: {confidence_result['final_confidence']:.3f}")
        print(f"Component scores:")
        for component, score in confidence_result['component_scores'].items():
            print(f"  {component}: {score:.3f}")
        print()
