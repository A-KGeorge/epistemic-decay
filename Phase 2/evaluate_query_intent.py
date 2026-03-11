"""
Phase 2 Evaluation with Query Temporal Intent

Tests Phase 2's query-side temporal intent analysis.
Compares three approaches:
- Standard: No decay, no intent
- Phase 1: Document decay only, query confidence=1.0  
- Phase 2: Document decay + query intent alignment
"""

import json
import sys
from datetime import datetime
from pathlib import Path
import numpy as np
from numpy.linalg import norm
import importlib.util

# Load Phase 1 module
phase1_path = Path(__file__).parent.parent / "Phase 1"
sys.path.insert(0, str(phase1_path))

spec_phase1 = importlib.util.spec_from_file_location(
    "phase1_decay",
    phase1_path / "decay_functions.py"
)
phase1 = importlib.util.module_from_spec(spec_phase1)
spec_phase1.loader.exec_module(phase1)

# Load Phase 2 modules
phase2_path = Path(__file__).parent.parent / "Phase 2"
sys.path.insert(0, str(phase2_path))

from decay_functions import (
    embed_with_decay, 
    encode_query_with_intent,
    score_with_temporal_alignment,
    model
)


def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    return np.dot(vec1, vec2) / (norm(vec1) * norm(vec2))


def evaluate_query_intent(benchmark_file: str = "cache/benchmarks/tempquestions_retrieval_large.json",
                         verbose: bool = True, use_original: bool = False):
    """
    Evaluate Phase 2 query intent on TempQuestions.
    
    Args:
        benchmark_file: Path to JSON benchmark
        verbose: Print detailed results
    """
    with open(benchmark_file, 'r') as f:
        data = json.load(f)
    
    test_cases = data["test_cases"] if isinstance(data, dict) else data
    
    # Auto-detect quiet mode for large benchmarks
    if len(test_cases) > 100 and verbose:
        print(f"Auto-detected large-scale benchmark, using quiet mode.")
        verbose = False
    
    results = {
        "standard_correct": 0,
        "phase1_correct": 0,
        "phase2_correct": 0,
        "phase2_over_phase1": 0,
        "phase2_regressed": 0,
    }
    
    intent_stats = {
        "specific_date": {"total": 0, "phase2_helped": 0},
        "current": {"total": 0, "phase2_helped": 0},
        "historical": {"total": 0, "phase2_helped": 0},
        "agnostic": {"total": 0, "phase2_helped": 0},
    }
    
    print("="*80)
    print("PHASE 2 QUERY INTENT EVALUATION")
    print("="*80)
    print(f"Test cases: {len(test_cases)}")
    print(f"Mode: {'Verbose' if verbose else 'Quiet (large-scale)'}")
    print(f"Query source: {'original_question (temporal)' if use_original else 'query (present tense)'}")
    print()
    
    for i, test in enumerate(test_cases, 1):
        if not verbose and i % 50 == 0:
            print(f"Processing... {i}/{len(test_cases)} ({100*i/len(test_cases):.1f}%)")
        
        # Use original_question if requested (for temporal queries with years)
        query = test.get("original_question", test["query"]) if use_original else test["query"]
        
        # Handle different benchmark formats
        if "documents" in test and "stale" in test["documents"]:
            # TempQuestions format
            doc1_key, doc2_key = "stale", "current"
        else:
            # Temporal intent format (uses first two document keys)
            doc_keys = list(test["documents"].keys())
            doc1_key, doc2_key = doc_keys[0], doc_keys[1]
        
        doc1 = test["documents"][doc1_key]
        doc2 = test["documents"][doc2_key]
        expected = test["expected_winner"]
        
        # Parse dates
        doc1_acquired = datetime.fromisoformat(doc1["acquired"].replace("Z", ""))
        doc2_acquired = datetime.fromisoformat(doc2["acquired"].replace("Z", ""))
        doc2_verified = datetime.fromisoformat(doc2["last_verified"].replace("Z", "")) if "last_verified" in doc2 else doc2_acquired
        
        # Phase 1: Standard query encoding (confidence=1.0)
        query_vec_phase1 = phase1.model.encode(query)
        query_vec_phase1 = np.append(query_vec_phase1, 1.0)
        
        # Phase 2: Query intent analysis
        query_vec_phase2, query_intent = encode_query_with_intent(query)
        
        # Track intent distribution
        preference = query_intent["preference"]
        if preference in intent_stats:
            intent_stats[preference]["total"] += 1
        
        # Embed documents (same for both phases)
        doc1_vec = embed_with_decay(doc1["text"], doc1_acquired)
        doc2_vec = embed_with_decay(doc2["text"], doc2_acquired, last_verified=doc2_verified)
        
        # STANDARD (no decay)
        doc1_sim_standard = cosine_similarity(query_vec_phase1[:384], doc1_vec[:384])
        doc2_sim_standard = cosine_similarity(query_vec_phase1[:384], doc2_vec[:384])
        standard_winner = doc2_key if doc2_sim_standard > doc1_sim_standard else doc1_key
        standard_correct = (standard_winner == expected)
        
        # PHASE 1 (document decay only)
        doc1_sim_phase1 = cosine_similarity(query_vec_phase1, doc1_vec)
        doc2_sim_phase1 = cosine_similarity(query_vec_phase1, doc2_vec)
        phase1_winner = doc2_key if doc2_sim_phase1 > doc1_sim_phase1 else doc1_key
        phase1_correct = (phase1_winner == expected)
        
        # PHASE 2 (document decay + query intent alignment)
        _, doc1_sim_phase2, doc1_align = score_with_temporal_alignment(
            query_vec_phase2, doc1_vec, query_intent, doc1_acquired, doc_text=doc1["text"]
        )
        _, doc2_sim_phase2, doc2_align = score_with_temporal_alignment(
            query_vec_phase2, doc2_vec, query_intent, doc2_acquired, doc2_verified, doc_text=doc2["text"]
        )
        phase2_winner = doc2_key if doc2_sim_phase2 > doc1_sim_phase2 else doc1_key
        phase2_correct = (phase2_winner == expected)
        
        # Update results
        if standard_correct:
            results["standard_correct"] += 1
        if phase1_correct:
            results["phase1_correct"] += 1
        if phase2_correct:
            results["phase2_correct"] += 1
        
        # Track Phase 2 improvement
        if phase2_correct and not phase1_correct:
            results["phase2_over_phase1"] += 1
            if preference in intent_stats:
                intent_stats[preference]["phase2_helped"] += 1
        elif phase1_correct and not phase2_correct:
            results["phase2_regressed"] += 1
        
        if verbose:
            print(f"Case {i}: {query}")
            print(f"  Intent: {query_intent['preference']} (tense: {query_intent['tense']})")
            if query_intent['years']:
                print(f"  Years: {query_intent['years']}")
            print(f"  Expected winner: {expected}")
            print(f"  Standard: {'OK' if standard_correct else 'FAIL'} ({standard_winner})")
            print(f"  Phase 1:  {'OK' if phase1_correct else 'FAIL'} ({phase1_winner})")
            print(f"  Phase 2:  {'OK' if phase2_correct else 'FAIL'} ({phase2_winner}) (align: {doc1_key}={doc1_align:.2f}, {doc2_key}={doc2_align:.2f})")
            if phase2_correct and not phase1_correct:
                print(f"  [+] Phase 2 rescued via temporal alignment!")
            elif phase1_correct and not phase2_correct:
                print(f"  [-] Phase 2 regressed!")
            print()
    
    # Print summary
    total = len(test_cases)
    print()
    print("="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    print(f"Standard:  {results['standard_correct']}/{total} ({100*results['standard_correct']/total:.1f}%)")
    print(f"Phase 1:   {results['phase1_correct']}/{total} ({100*results['phase1_correct']/total:.1f}%)")
    print(f"Phase 2:   {results['phase2_correct']}/{total} ({100*results['phase2_correct']/total:.1f}%)")
    print()
    print(f"Phase 2 over Phase 1: +{results['phase2_over_phase1']} cases")
    print(f"Phase 2 regressions:  -{results['phase2_regressed']} cases")
    print(f"Net improvement:      {results['phase2_over_phase1'] - results['phase2_regressed']:+d} cases")
    print()
    print("="*80)
    print("QUERY INTENT BREAKDOWN")
    print("="*80)
    for intent_type, stats in intent_stats.items():
        if stats["total"] > 0:
            help_rate = 100 * stats["phase2_helped"] / stats["total"]
            print(f"{intent_type:15s}: {stats['total']:4d} queries, Phase 2 helped on {stats['phase2_helped']:3d} ({help_rate:.1f}%)")
    
    # Return results for writing to file
    return {
        "total_cases": total,
        "results": results,
        "intent_stats": intent_stats,
        "benchmark_file": benchmark_file,
    }


def write_results_to_file(eval_results, output_path=None):
    """Write evaluation results to RESULTS.md with timestamp."""
    from datetime import datetime
    
    # Default to RESULTS.md in the project root (one level up from this script)
    if output_path is None:
        script_dir = Path(__file__).parent
        output_path = script_dir.parent / "RESULTS.md"
    else:
        output_path = Path(output_path)
    
    total = eval_results["total_cases"]
    results = eval_results["results"]
    intent_stats = eval_results["intent_stats"]
    benchmark = Path(eval_results["benchmark_file"]).name
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Read existing results if file exists
    existing_content = ""
    if output_path.exists():
        with open(output_path, 'r') as f:
            existing_content = f.read()
    
    # Create new entry
    new_entry = f"""
## Run: {timestamp}

**Benchmark**: `{benchmark}`  
**Test Cases**: {total}

### Results

| Method    | Correct | Accuracy | vs Phase 1 |
|-----------|---------|----------|------------|
| Standard  | {results['standard_correct']}/{total} | {100*results['standard_correct']/total:.1f}% | - |
| Phase 1   | {results['phase1_correct']}/{total} | {100*results['phase1_correct']/total:.1f}% | baseline |
| Phase 2   | {results['phase2_correct']}/{total} | {100*results['phase2_correct']/total:.1f}% | +{results['phase2_over_phase1']} cases |

**Phase 2 Improvement**:
- Cases rescued: {results['phase2_over_phase1']}
- Regressions: {results['phase2_regressed']}
- Net improvement: {results['phase2_over_phase1'] - results['phase2_regressed']:+d} cases

### Query Intent Breakdown

"""
    
    for intent_type, stats in intent_stats.items():
        if stats["total"] > 0:
            help_rate = 100 * stats["phase2_helped"] / stats["total"]
            new_entry += f"- **{intent_type}**: {stats['total']} queries, Phase 2 helped on {stats['phase2_helped']} ({help_rate:.1f}%)\n"
    
    new_entry += "\n---\n"
    
    # Write to file (prepend new entry)
    with open(output_path, 'w') as f:
        f.write(f"# Evaluation Results\n\n")
        f.write(f"<!-- AUTO-GENERATED by evaluate_query_intent.py - Last updated: {timestamp} -->\n\n")
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


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate Phase 2 query intent")
    parser.add_argument("--benchmark", default="../TempQuestions/cache/benchmarks/tempquestions_retrieval_large.json")
    parser.add_argument("--verbose", action="store_true", help="Show each case")
    parser.add_argument("--use-original", action="store_true", 
                        help="Use original_question field instead of query (for temporal queries with years)")
    args = parser.parse_args()
    
    eval_results = evaluate_query_intent(args.benchmark, verbose=args.verbose, use_original=args.use_original)
    
    # Write results to RESULTS.md
    write_results_to_file(eval_results)
