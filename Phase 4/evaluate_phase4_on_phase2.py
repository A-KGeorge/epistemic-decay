"""
Phase 4 Evaluation on Phase 2 Benchmarks

Tests Phase 4's multi-dimensional decay (temporal + paradigm + uncertainty + dependency)
against Phase 2's temporal-only benchmark suite.

**CRITICAL ARCHITECTURAL DECISION:**

Phase 4 does NOT replace Phase 2. Instead, Phase 4's epistemic dimensions (paradigm,
uncertainty, dependency) MODULATE Phase 2's temporal alignment scores:

    final_score = phase2_temporal_score × phase4_epistemic_modifiers

Where:
- phase2_temporal_score: Base similarity × temporal alignment (1.0-1.4×)
- phase4_epistemic_modifiers: paradigm_validity × uncertainty_confidence × (1 - dependency_decay)

This preserves Phase 2's strong temporal signal (100% accuracy on specific-date queries)
while adding Phase 4's epistemic nuance (paradigm scoping, uncertainty quantification).

Comparison:
- Phase 2 alone: Temporal alignment only (λt)
- Phase 4 integrated: Phase 2 × (λp + λu + λd + λ0)
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict
import numpy as np
from numpy.linalg import norm
import importlib.util
import argparse

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False
    print("WARNING: rank_bm25 not installed. BM25 baseline disabled. Run: pip install rank-bm25")

# Add parent directories to path
phase2_path = Path(__file__).parent.parent / "Phase 2"
phase4_path = Path(__file__).parent
sys.path.insert(0, str(phase2_path))
sys.path.insert(0, str(phase4_path))

# Import Phase 2 components
from decay_functions import embed_with_decay, encode_query_with_intent, model

# Import Phase 4 components
from multi_dimensional_decay import score_document_with_full_decay


def cosine_similarity(v1, v2):
    """Cosine similarity between two vectors."""
    return np.dot(v1, v2) / (norm(v1) * norm(v2))


def load_phase3_graph(graph_facts_file: str):
    """Load Phase 3 knowledge graph from facts file."""
    phase3_path = Path(__file__).parent.parent / "Phase 3"
    sys.path.insert(0, str(phase3_path))
    
    from knowledge_graph import TemporalKnowledgeGraph
    import json
    
    with open(graph_facts_file, 'r') as f:
        facts = json.load(f)
    
    graph = TemporalKnowledgeGraph()
    
    for case_id, case_data in facts.items():
        if case_id == "_metadata":
            continue
        
        for role_fact in case_data.get("roles", []):
            graph.add_role_fact(
                entity=role_fact["entity"],
                role=role_fact["role"],
                org=role_fact["org"],
                start_date=role_fact["start_date"],
                end_date=role_fact.get("end_date")
            )
        
        for succession in case_data.get("successions", []):
            graph.add_succession(
                predecessor_entity=succession["predecessor"],
                successor_entity=succession["successor"],
                role=succession["role"],
                org=succession["org"],
                transition_date=succession["transition_date"]
            )
    
    return graph


def evaluate_benchmark(benchmark_file: str, verbose: bool = True, use_original: bool = False, use_graph: bool = False):
    """
    Evaluate full pipeline: Phase 1 → Phase 2 → Phase 4 → Phase 3 (optional).
    
    Args:
        benchmark_file: Path to Phase 2 benchmark JSON
        verbose: Print detailed case-by-case results
        use_original: Use original_question field if available (for temporal queries)
        use_graph: Enable Phase 3 graph override (applies AFTER Phase 4 epistemic modulation)
    """
    # Load Phase 3 knowledge graph if enabled
    knowledge_graph = None
    if use_graph:
        graph_facts_path = Path(__file__).parent.parent / "Phase 3" / "graph_facts.json"
        knowledge_graph = load_phase3_graph(str(graph_facts_path))
        print(f"Loaded Phase 3 knowledge graph: {knowledge_graph.graph.number_of_nodes()} nodes")
        print()
    
    with open(benchmark_file, 'r') as f:
        data = json.load(f)
    
    test_cases = data.get("test_cases", data)
    
    # Auto-detect format and quiet mode
    if len(test_cases) > 100 and verbose:
        print(f"Auto-detected large-scale benchmark ({len(test_cases)} cases), using quiet mode.")
        verbose = False
    
    results = {
        "standard_correct": 0,
        "bm25_correct": 0,
        "recency_correct": 0,
        "phase2_correct": 0,    # Phase 2 temporal alignment
        "phase4_correct": 0,    # Phase 4 multi-dimensional decay
        "phase3_correct": 0 if use_graph else None,  # Phase 3 graph override
        "both_correct": 0,
        "both_wrong": 0,
        "phase4_rescued": 0,    # Phase 4 correct when Phase 2 wrong
        "phase4_regressed": 0,  # Phase 4 wrong when Phase 2 correct
        "phase3_over_phase4": 0 if use_graph else None,  # Phase 3 rescued from Phase 4
        "phase3_regressed": 0 if use_graph else None,  # Phase 3 regressed from Phase 4
    }
    
    strategy_distribution = {}
    
    print("="*80)
    if use_graph:
        print("FULL PIPELINE: P1 -> P2 -> P4 -> P3")
    else:
        print("PHASE 4 MULTI-DIMENSIONAL DECAY ON PHASE 2 BENCHMARKS")
    print("="*80)
    print(f"Test cases: {len(test_cases)}")
    print(f"Mode: {'Verbose' if verbose else 'Quiet (large-scale)'}")
    print(f"Query source: {'original_question (temporal)' if use_original else 'query (present tense)'}")
    print()
    print("Architecture:")
    print("  Phase 1: Temporal decay (document-side)")
    print("  Phase 2: Temporal alignment (query-side)")
    print("  Phase 4: Epistemic modulation (paradigm x uncertainty x dependency x zero-decay)")
    if use_graph:
        print("  Phase 3: Graph override (role queries with adaptive confidence)")
        print("    - High confidence (>=0.8): Always use graph")
        print("    - Medium confidence (0.5-0.8): Use if beats both document scores")
        print("    - Low confidence (<0.5): Ignore, use Phase 4")
    print()
    
    failures = []
    
    for i, test in enumerate(test_cases, 1):
        if not verbose and i % 50 == 0:
            print(f"Processing... {i}/{len(test_cases)} ({100*i/len(test_cases):.1f}%)")
        
        # Use original_question if requested
        query = test.get("original_question", test["query"]) if use_original else test["query"]
        
        # Handle different benchmark formats
        if "documents" in test and "stale" in test["documents"]:
            # TempQuestions format
            doc1_key, doc2_key = "stale", "current"
        else:
            # Temporal intent format
            doc_keys = list(test["documents"].keys())
            doc1_key, doc2_key = doc_keys[0], doc_keys[1]
        
        doc1 = test["documents"][doc1_key]
        doc2 = test["documents"][doc2_key]
        expected = test["expected_winner"]
        
        # Parse dates
        doc1_acquired = datetime.fromisoformat(doc1["acquired"].replace("Z", ""))
        doc2_acquired = datetime.fromisoformat(doc2["acquired"].replace("Z", ""))
        doc2_verified = datetime.fromisoformat(doc2["last_verified"].replace("Z", "")) if "last_verified" in doc2 else doc2_acquired
        
        # Encode query (Phase 2 style with temporal intent)
        query_vec_phase2, query_intent = encode_query_with_intent(query)
        
        # Encode query (Phase 4 style - semantic only, no confidence dimension)
        query_vec_phase4 = model.encode(query)
        
        # Embed documents with decay
        doc1_vec = embed_with_decay(doc1["text"], doc1_acquired)
        doc2_vec = embed_with_decay(doc2["text"], doc2_acquired, last_verified=doc2_verified)

        # STANDARD BASELINE (cosine similarity, no decay, no intent)
        doc1_sim_standard = cosine_similarity(query_vec_phase4, doc1_vec[:384])
        doc2_sim_standard = cosine_similarity(query_vec_phase4, doc2_vec[:384])
        standard_winner = doc2_key if doc2_sim_standard > doc1_sim_standard else doc1_key
        standard_correct = (standard_winner == expected)

        # BM25 BASELINE (lexical, no embeddings)
        bm25_winner = None
        bm25_correct = False
        if HAS_BM25:
            corpus = [doc1["text"].lower().split(), doc2["text"].lower().split()]
            bm25_model = BM25Okapi(corpus)
            bm25_scores = bm25_model.get_scores(query.lower().split())
            bm25_winner = doc2_key if bm25_scores[1] >= bm25_scores[0] else doc1_key
            bm25_correct = (bm25_winner == expected)

        # RECENCY BASELINE (newer document wins, ignoring content)
        recency_winner = doc2_key if doc2_acquired >= doc1_acquired else doc1_key
        recency_correct = (recency_winner == expected)

        # PHASE 2: Temporal alignment scoring (base signal)
        from decay_functions import score_with_temporal_alignment
        _, doc1_sim_phase2, _ = score_with_temporal_alignment(
            query_vec_phase2, doc1_vec, query_intent, doc1_acquired, doc_text=doc1["text"]
        )
        _, doc2_sim_phase2, _ = score_with_temporal_alignment(
            query_vec_phase2, doc2_vec, query_intent, doc2_acquired, doc_text=doc2["text"]
        )
        
        phase2_winner = doc2_key if doc2_sim_phase2 > doc1_sim_phase2 else doc1_key
        phase2_correct = (phase2_winner == expected)
        
        # PHASE 4: Get epistemic modifiers (paradigm/uncertainty/dependency)
        # These should MULTIPLY Phase 2's score, not replace it
        from multi_dimensional_decay import analyze_statement_decay, compute_final_confidence
        from paradigm_detection import extract_paradigm_context
        from query_epistemic_detection import should_apply_epistemic_modulation
        
        # ===== CRITICAL FIX: Query-aware epistemic modulation =====
        # Only apply epistemic analysis if QUERY contains epistemic markers
        query_epistemic_check = should_apply_epistemic_modulation(query)
        
        if not query_epistemic_check["apply_epistemic"]:
            # Query is clean (no uncertainty/paradigm markers)
            # Preserve Phase 2 score - don't penalize documents for their phrasing
            doc1_epistemic = 1.0
            doc2_epistemic = 1.0
            strategy = "temporal_alignment_preserved"
        else:
            # Query has epistemic markers - apply document-side epistemic analysis
            # Analyze documents for epistemic decay
            doc1_decay = analyze_statement_decay(doc1["text"], doc1_acquired)
            doc2_decay = analyze_statement_decay(doc2["text"], doc2_acquired)
            
            # Extract query paradigm context
            query_paradigm_ctx = extract_paradigm_context(query)
            query_paradigm_set = query_paradigm_ctx["paradigm_set"]
            
            # Compute full confidence scores (including temporal)
            now = datetime.now()
            doc1_days = (now - doc1_acquired).days
            doc2_days = (now - doc2_acquired).days
            
            doc1_confidence = compute_final_confidence(doc1_decay, doc1_days, query_paradigm_set, query)
            doc2_confidence = compute_final_confidence(doc2_decay, doc2_days, query_paradigm_set, query)
            
            # Extract ONLY epistemic components (exclude temporal since Phase 2 handles it)
            doc1_epistemic = (
                doc1_confidence["component_scores"]["paradigm"] *
                doc1_confidence["component_scores"]["uncertainty"] *
                doc1_confidence["component_scores"]["dependency"]
            )
            doc2_epistemic = (
                doc2_confidence["component_scores"]["paradigm"] *
                doc2_confidence["component_scores"]["uncertainty"] *
                doc2_confidence["component_scores"]["dependency"]
            )
            
            # Determine strategy based on which dimension had the most impact
            if doc1_decay.is_zero_decay or doc2_decay.is_zero_decay:
                strategy = "zero_decay"
            elif doc1_confidence["paradigm_valid"] == False or doc2_confidence["paradigm_valid"] == False:
                strategy = "paradigm_rejection"
            elif abs(doc1_epistemic - doc2_epistemic) > 0.2:
                # Significant epistemic difference
                if doc1_decay.uncertainty < 0.8 or doc2_decay.uncertainty < 0.8:
                    strategy = "uncertainty_modulation"
                else:
                    strategy = "epistemic_modulation"
            else:
                # Epistemic modifiers didn't change much, temporal alignment dominated
                strategy = "temporal_alignment_preserved"
        
        # PHASE 4 INTEGRATED: Phase 2 score × Phase 4 epistemic modifiers
        doc1_sim_phase4 = doc1_sim_phase2 * doc1_epistemic
        doc2_sim_phase4 = doc2_sim_phase2 * doc2_epistemic
        
        phase4_winner = doc2_key if doc2_sim_phase4 > doc1_sim_phase4 else doc1_key
        phase4_correct = (phase4_winner == expected)
        
        strategy_distribution[strategy] = strategy_distribution.get(strategy, 0) + 1
        
        # ===== PHASE 3: Graph override (role queries only) =====
        phase3_winner = phase4_winner  # Default to Phase 4 result
        phase3_override = False
        graph_confidence = 0.0
        graph_override_reason = "Graph not enabled"
        
        if use_graph:
            from graph_matching import compute_graph_alignment
            
            # Try graph matching with document text for entity-aware matching
            doc1_graph_result = compute_graph_alignment(query, knowledge_graph, doc1_acquired, doc1["text"])
            doc2_graph_result = compute_graph_alignment(query, knowledge_graph, doc2_acquired, doc2["text"])
            
            doc1_graph_score = doc1_graph_result["score"]
            doc2_graph_score = doc2_graph_result["score"]
            
            # ADAPTIVE CONFIDENCE THRESHOLD:
            # 1. EXACT match (score = 1.0): Always override (structural fact beats embeddings)
            # 2. High confidence (≥ 0.8): Use graph for strong NEAR_MATCH
            # 3. Medium confidence (0.5-0.8): Use graph if it beats BOTH document scores
            # 4. Low confidence (< 0.5): Ignore graph, use Phase 4 scores
            
            exact_match_threshold = 1.0
            high_confidence_threshold = 0.8
            medium_confidence_threshold = 0.5
            
            # Determine which document has better graph match
            better_graph_score = max(doc1_graph_score, doc2_graph_score)
            better_graph_winner = doc1_key if doc1_graph_score > doc2_graph_score else doc2_key
            better_graph_result = doc1_graph_result if doc1_graph_score > doc2_graph_score else doc2_graph_result
            
            # Check if graph should override Phase 4
            should_override = False
            
            if better_graph_score == exact_match_threshold:
                # EXACT match: Always use graph (structural fact > embeddings)
                should_override = True
                graph_confidence = better_graph_score
                graph_override_reason = f"EXACT match (score={better_graph_score:.2f})"
            elif better_graph_score >= high_confidence_threshold:
                # High confidence: Always use graph
                should_override = True
                graph_confidence = better_graph_score
                graph_override_reason = f"High confidence (score={better_graph_score:.2f} ≥ {high_confidence_threshold})"
            elif better_graph_score >= medium_confidence_threshold:
                # Medium confidence: Use graph only if it beats BOTH document scores
                # This is adaptive - graph wins if it's more confident than epistemic modulation
                if better_graph_score > doc1_sim_phase4 and better_graph_score > doc2_sim_phase4:
                    should_override = True
                    graph_confidence = better_graph_score
                    graph_override_reason = f"Medium confidence beats both docs (graph={better_graph_score:.2f} > docs={doc1_sim_phase4:.2f},{doc2_sim_phase4:.2f})"
                else:
                    graph_override_reason = f"Medium confidence doesn't beat docs (graph={better_graph_score:.2f} vs docs={doc1_sim_phase4:.2f},{doc2_sim_phase4:.2f})"
            else:
                graph_override_reason = f"Low confidence (score={better_graph_score:.2f} < {medium_confidence_threshold})"
            
            # Apply override if conditions met
            if should_override and doc1_graph_score != doc2_graph_score:
                phase3_winner = better_graph_winner
                phase3_override = True
            elif should_override and doc1_graph_score == doc2_graph_score:
                graph_override_reason = f"No override: both docs have same graph score ({doc1_graph_score:.2f})"
        
        phase3_correct = (phase3_winner == expected) if use_graph else phase4_correct
        
        # Update results
        if standard_correct:
            results["standard_correct"] += 1
        if bm25_correct:
            results["bm25_correct"] += 1
        if recency_correct:
            results["recency_correct"] += 1
        if phase2_correct:
            results["phase2_correct"] += 1
        if phase4_correct:
            results["phase4_correct"] += 1
        if use_graph and phase3_correct:
            results["phase3_correct"] += 1
        
        if phase2_correct and phase4_correct:
            results["both_correct"] += 1
        elif not phase2_correct and not phase4_correct:
            results["both_wrong"] += 1
        elif phase4_correct and not phase2_correct:
            results["phase4_rescued"] += 1
        elif phase2_correct and not phase4_correct:
            results["phase4_regressed"] += 1
        
        # Track Phase 3 improvement
        if use_graph:
            if phase3_correct and not phase4_correct:
                results["phase3_over_phase4"] += 1
            elif phase4_correct and not phase3_correct:
                results["phase3_regressed"] += 1
        
        # Verbose output
        if verbose:
            status_p2 = "[P2]" if phase2_correct else "[P2-FAIL]"
            status_p4 = "[P4]" if phase4_correct else "[P4-FAIL]"
            status_p3 = "[P3]" if (use_graph and phase3_correct) else ""
            
            print(f"\nCase {i}: {test.get('id', f'unnamed_{i}')}")
            print(f"Query: {query}")
            print(f"Expected: {expected}")
            print()
            print(f"Phase 2: {status_p2} {phase2_winner} (score: {doc2_sim_phase2:.4f} vs {doc1_sim_phase2:.4f})")
            print(f"  Intent: {query_intent['preference']}")
            print()
            print(f"Phase 4: {status_p4} {phase4_winner} (score: {doc2_sim_phase4:.4f} vs {doc1_sim_phase4:.4f})")
            print(f"  Strategy: {strategy}")
            print(f"  Doc1: P2={doc1_sim_phase2:.4f} x epistemic={doc1_epistemic:.3f} = {doc1_sim_phase4:.4f}")
            print(f"  Doc2: P2={doc2_sim_phase2:.4f} x epistemic={doc2_epistemic:.3f} = {doc2_sim_phase4:.4f}")
            
            if use_graph:
                print(f"\nPhase 3 Graph Analysis:")
                print(f"  Query classification: {doc1_graph_result['constraints'].get('query_type', 'unknown')}")
                print(f"  Role: {doc1_graph_result['constraints'].get('role', 'N/A')} | Org: {doc1_graph_result['constraints'].get('org', 'N/A')} | Entity: {doc1_graph_result['constraints'].get('entity', 'N/A')} | Year: {doc1_graph_result['constraints'].get('year', 'N/A')}")
                print(f"  Directional: {doc1_graph_result['constraints'].get('directional', 'N/A')}")
                print(f"  Doc1 graph: score={doc1_graph_score:.2f}, match={doc1_graph_result['match_type']}, entity={doc1_graph_result['matched_entity']}")
                print(f"  Doc2 graph: score={doc2_graph_score:.2f}, match={doc2_graph_result['match_type']}, entity={doc2_graph_result['matched_entity']}")
                if doc1_graph_result.get('all_matches'):
                    print(f"  All valid entities: {doc1_graph_result['all_matches']}")
                
                if phase3_override:
                    print(f"  Override: YES - {graph_override_reason}")
                    print(f"  Result: {status_p3} {phase3_winner}")
                else:
                    print(f"  Override: NO - {graph_override_reason}")
                    print(f"  Result: {status_p3} {phase3_winner} (using Phase 4)")
            
            # Show epistemic breakdown
            if abs(doc1_epistemic - doc2_epistemic) > 0.05:
                print(f"  Epistemic components:")
                print(f"    Doc1: paradigm={doc1_confidence['component_scores']['paradigm']:.3f}, "
                      f"uncertainty={doc1_confidence['component_scores']['uncertainty']:.3f}, "
                      f"dependency={doc1_confidence['component_scores']['dependency']:.3f}")
                print(f"    Doc2: paradigm={doc2_confidence['component_scores']['paradigm']:.3f}, "
                      f"uncertainty={doc2_confidence['component_scores']['uncertainty']:.3f}, "
                      f"dependency={doc2_confidence['component_scores']['dependency']:.3f}")
            
            if phase4_correct != phase2_correct:
                print(f"\n*** {'PHASE 4 RESCUE' if phase4_correct else 'PHASE 4 REGRESSION'} ***")
            
            if use_graph and phase3_override and phase3_correct != phase4_correct:
                print(f"*** {'PHASE 3 RESCUE' if phase3_correct else 'PHASE 3 REGRESSION'} ***")
        
        # Track failures for summary
        final_correct = phase3_correct if use_graph else phase4_correct
        if not final_correct:
            failures.append({
                "id": test.get('id', f'unnamed_{i}'),
                "query": query,
                "expected": expected,
                "phase2_winner": phase2_winner,
                "phase4_winner": phase4_winner,
                "phase3_winner": phase3_winner if use_graph else phase4_winner,
                "phase3_override": phase3_override if use_graph else False,
                "phase2_correct": phase2_correct,
                "phase4_correct": phase4_correct,
                "doc1_phase2": doc1_sim_phase2,
                "doc2_phase2": doc2_sim_phase2,
                "doc1_epistemic": doc1_epistemic,
                "doc2_epistemic": doc2_epistemic,
                "doc1_final": doc1_sim_phase4,
                "doc2_final": doc2_sim_phase4,
                "strategy": strategy,
            })
    
    # Print summary
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    
    total = len(test_cases)
    print(f"\nBaselines:")
    print(f"  Standard (cosine, no decay):       {results['standard_correct']}/{total} ({100*results['standard_correct']/total:.1f}%)")
    if HAS_BM25:
        print(f"  BM25 (lexical, no semantics):      {results['bm25_correct']}/{total} ({100*results['bm25_correct']/total:.1f}%)")
    print(f"  Recency (newest doc wins):         {results['recency_correct']}/{total} ({100*results['recency_correct']/total:.1f}%)")
    print(f"\nAccuracy by Phase:")
    print(f"  Phase 2 (temporal only):           {results['phase2_correct']}/{total} ({100*results['phase2_correct']/total:.1f}%)")
    print(f"  Phase 4 (integrated P2×modifiers): {results['phase4_correct']}/{total} ({100*results['phase4_correct']/total:.1f}%)")
    if use_graph:
        print(f"  Phase 3 (graph override):          {results['phase3_correct']}/{total} ({100*results['phase3_correct']/total:.1f}%)")
    
    delta_p4_vs_p2 = results['phase4_correct'] - results['phase2_correct']
    delta_sign = "+" if delta_p4_vs_p2 >= 0 else ""
    print(f"\nPhase 4 vs Phase 2: {delta_sign}{delta_p4_vs_p2} cases ({delta_sign}{100*delta_p4_vs_p2/total:.1f} pts)")
    
    if use_graph:
        delta_p3_vs_p4 = results['phase3_correct'] - results['phase4_correct']
        delta_sign_p3 = "+" if delta_p3_vs_p4 >= 0 else ""
        print(f"Phase 3 vs Phase 4: {delta_sign_p3}{delta_p3_vs_p4} cases ({delta_sign_p3}{100*delta_p3_vs_p4/total:.1f} pts)")
    
    print(f"\nPhase-over-Phase Breakdown:")
    print(f"  P4 rescued from P2: {results['phase4_rescued']}/{total} ({100*results['phase4_rescued']/total:.1f}%)")
    print(f"  P4 regressed from P2: {results['phase4_regressed']}/{total} ({100*results['phase4_regressed']/total:.1f}%)")
    
    if use_graph:
        print(f"  P3 rescued from P4: {results['phase3_over_phase4']}/{total} ({100*results['phase3_over_phase4']/total:.1f}%)")
        print(f"  P3 regressed from P4: {results['phase3_regressed']}/{total} ({100*results['phase3_regressed']/total:.1f}%)")
    
    print(f"\nStrategy Distribution:")
    for strategy, count in sorted(strategy_distribution.items(), key=lambda x: -x[1]):
        print(f"  {strategy:25s}: {count:3d} ({100*count/total:.1f}%)")
    
    if failures and len(failures) <= 20:
        print(f"\n{'='*80}")
        if use_graph:
            print(f"FINAL FAILURES ({len(failures)} cases)")
        else:
            print(f"PHASE 4 FAILURES ({len(failures)} cases)")
        print("="*80)
        for fail in failures:
            print(f"\nID: {fail['id']}")
            print(f"Query: {fail['query']}")
            final_winner = fail.get('phase3_winner', fail['phase4_winner'])
            print(f"Expected: {fail['expected']}, Got: {final_winner}")
            print(f"  Phase 2: {fail['phase2_winner']} ({'OK' if fail['phase2_correct'] else 'FAIL'})")
            print(f"  Phase 4: {fail['phase4_winner']} ({'OK' if fail['phase4_correct'] else 'FAIL'})")
            if use_graph:
                override_str = " (graph override)" if fail.get('phase3_override') else ""
                print(f"  Phase 3: {fail['phase3_winner']}{override_str}")
            print(f"  Doc1: P2={fail['doc1_phase2']:.4f} x {fail['doc1_epistemic']:.3f} = {fail['doc1_final']:.4f}")
            print(f"  Doc2: P2={fail['doc2_phase2']:.4f} x {fail['doc2_epistemic']:.3f} = {fail['doc2_final']:.4f}")
            print(f"  Strategy: {fail['strategy']}")
    elif failures:
        print(f"\n({len(failures)} failures - too many to display individually)")
    
    return results


def write_results_to_file(eval_results: Dict, benchmark_file: str, output_path=None):
    """Write evaluation results to RESULTS.md with timestamp."""
    from datetime import datetime
    from pathlib import Path
    
    # Default to RESULTS.md in the project root (two levels up from this script)
    if output_path is None:
        script_dir = Path(__file__).parent
        output_path = script_dir.parent / "RESULTS.md"
    else:
        output_path = Path(output_path)
    
    # Calculate total from results
    total = (eval_results["phase2_correct"] + 
             eval_results["both_wrong"] + 
             eval_results["phase4_rescued"] + 
             eval_results["phase4_regressed"])
    
    phase2_correct = eval_results["phase2_correct"]
    phase4_correct = eval_results["phase4_correct"]
    rescued = eval_results["phase4_rescued"]
    regressed = eval_results["phase4_regressed"]
    benchmark = Path(benchmark_file).name
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Read existing results if file exists
    existing_content = ""
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
    
    # Create new entry
    delta = phase4_correct - phase2_correct
    delta_sign = "+" if delta >= 0 else ""
    delta_pts = delta / total * 100 if total > 0 else 0.0
    
    new_entry = f"""
## Run: {timestamp}

**Benchmark**: `{benchmark}`  
**Test Cases**: {total}  
**Phase**: Phase 4 Multi-Dimensional Decay (Integrated on Phase 2)

### Results

| Method    | Correct | Accuracy | vs Phase 2 |
|-----------|---------|----------|------------|
| Phase 2 (temporal only)   | {phase2_correct}/{total} | {100*phase2_correct/total:.1f}% | baseline |
| Phase 4 (integrated)      | {phase4_correct}/{total} | {100*phase4_correct/total:.1f}% | {delta_sign}{delta} cases ({delta_sign}{delta_pts:.1f} pts) |

**Phase 4 Integration**:
- Cases rescued: {rescued}
- Regressions: {regressed}
- Net improvement: {delta_sign}{delta} cases
- Architecture: Phase 2 × epistemic modifiers (paradigm × uncertainty × dependency)

---
"""
    
    # Write to file (prepend new entry)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Evaluation Results\n\n")
        f.write(f"<!-- AUTO-GENERATED by Phase 4 evaluators - Last updated: {timestamp} -->\n\n")
        f.write(new_entry)
        if existing_content and "# Evaluation Results" in existing_content:
            # Strip header from existing content
            existing_lines = existing_content.split('\n')
            start_idx = 0
            for i, line in enumerate(existing_lines):
                if line.startswith("## Run:"):
                    start_idx = i
                    break
            if start_idx > 0:
                f.write('\n'.join(existing_lines[start_idx:]))


def main():
    parser = argparse.ArgumentParser(description="Evaluate Phase 4 on Phase 2 benchmarks")
    parser.add_argument(
        "--benchmark",
        type=str,
        default="../TempQuestions/cache/benchmarks/verified_specific_date_benchmark.json",
        help="Path to Phase 2 benchmark JSON file"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed case-by-case results"
    )
    parser.add_argument(
        "--use-original",
        action="store_true",
        help="Use original_question field if available (for temporal queries with years)"
    )
    parser.add_argument(
        "--use-graph",
        action="store_true",
        help="Enable Phase 3 graph override (applies AFTER Phase 4 epistemic modulation)"
    )
    
    args = parser.parse_args()
    
    # Resolve benchmark path
    benchmark_path = Path(args.benchmark)
    if not benchmark_path.is_absolute():
        benchmark_path = Path(__file__).parent / benchmark_path
    
    if not benchmark_path.exists():
        print(f"ERROR: Benchmark file not found: {benchmark_path}")
        print()
        print("Available Phase 2 benchmarks:")
        print("  --benchmark ../TempQuestions/cache/benchmarks/verified_specific_date_benchmark.json")
        print("  --benchmark ../TempQuestions/cache/benchmarks/specific_date_benchmark_large.json")
        print("  --benchmark ../TempQuestions/cache/benchmarks/tempquestions_retrieval_large.json")
        print("  --benchmark ../TempQuestions/cache/benchmarks/fuzzy_logic_benchmark.json")
        print("  --benchmark ../TempQuestions/cache/benchmarks/edge_cases_benchmark.json")
        return
    
    results = evaluate_benchmark(
        str(benchmark_path),
        verbose=args.verbose,
        use_original=args.use_original,
        use_graph=args.use_graph
    )
    
    # Write results to RESULTS.md
    if results:
        write_results_to_file(results, str(benchmark_path))


if __name__ == "__main__":
    main()
