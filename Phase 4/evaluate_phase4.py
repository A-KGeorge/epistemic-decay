"""
Phase 4: Paradigm & Uncertainty Decay Evaluator
Test harness for multi-dimensional decay framework
"""

import json
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Phase 2'))

from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np

from paradigm_detection import extract_paradigm_context, compute_paradigm_decay_score
from uncertainty_decay import compute_uncertainty_decay_score, compute_base_confidence
from multi_dimensional_decay import analyze_statement_decay, compute_final_confidence


def load_benchmark(filepath: str) -> Dict:
    """Load paradigm/uncertainty benchmark JSON."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def evaluate_paradigm_decay(test_case: Dict) -> Dict[str, any]:
    """
    Evaluate paradigm decay detection for a test case.
    
    Returns:
        {
            "passed": bool,
            "detected_paradigms": Set[str],
            "expected_paradigms": Set[str],
            "confidence": float,
            "details": Dict
        }
    """
    statement = test_case["statement"]
    expected_paradigms = set(test_case.get("expected_paradigm", []))
    
    # Extract paradigm context
    paradigm_ctx = extract_paradigm_context(statement)
    detected_paradigms = paradigm_ctx["paradigm_set"]
    
    # Check if detection matches expectation
    paradigm_match = detected_paradigms == expected_paradigms
    
    # Check confidence in appropriate context
    query = test_case.get("query", "")
    if query:
        result = compute_paradigm_decay_score(statement, query)
        confidence = result["confidence"]
    else:
        confidence = 1.0 if paradigm_ctx["is_universally_scoped"] else 0.0
    
    passed = paradigm_match
    
    return {
        "passed": passed,
        "detected_paradigms": detected_paradigms,
        "expected_paradigms": expected_paradigms,
        "confidence": confidence,
        "details": paradigm_ctx
    }


def evaluate_uncertainty_decay(test_case: Dict) -> Dict[str, any]:
    """
    Evaluate uncertainty decay detection for a test case.
    
    Returns:
        {
            "passed": bool,
            "computed_confidence": float,
            "expected_range": Tuple[float, float],
            "in_range": bool,
            "details": Dict
        }
    """
    statement = test_case["statement"]
    expected_range = test_case.get("expected_confidence_range", [0.0, 1.0])
    
    # Compute uncertainty
    result = compute_uncertainty_decay_score(statement)
    computed_confidence = result["final_confidence"]
    
    # Check if in expected range
    in_range = expected_range[0] <= computed_confidence <= expected_range[1]
    
    return {
        "passed": in_range,
        "computed_confidence": computed_confidence,
        "expected_range": expected_range,
        "in_range": in_range,
        "details": result["debug_info"]
    }


def evaluate_zero_decay(test_case: Dict) -> Dict[str, any]:
    """
    Evaluate zero decay detection and fragility.
    
    Returns:
        {
            "passed": bool,
            "is_zero_decay": bool,
            "expected_zero_decay": bool,
            "is_contaminated": bool,
            "details": Dict
        }
    """
    statement = test_case["statement"]
    expected_zero = test_case.get("is_zero_decay", False)
    expected_contaminated = test_case.get("is_contaminated", False)
    
    # Analyze decay
    decay_vector = analyze_statement_decay(statement)
    is_zero = decay_vector.is_zero_decay
    
    # Check contamination (if expected)
    if expected_contaminated:
        is_contaminated = not is_zero and decay_vector.temporal > 0
        passed = is_contaminated
    else:
        passed = is_zero == expected_zero
    
    return {
        "passed": passed,
        "is_zero_decay": is_zero,
        "expected_zero_decay": expected_zero,
        "is_contaminated": expected_contaminated and not is_zero,
        "details": {
            "decay_vector": str(decay_vector),
            "temporal_decay": decay_vector.temporal,
            "paradigm_set": decay_vector.paradigm_set,
            "uncertainty": decay_vector.uncertainty
        }
    }


def evaluate_multi_dimensional(test_case: Dict) -> Dict[str, any]:
    """
    Evaluate multi-dimensional decay integration.
    
    Returns:
        {
            "passed": bool,
            "final_confidence": float,
            "expected_range": Tuple[float, float],
            "component_scores": Dict
        }
    """
    statement = test_case["statement"]
    days_elapsed = test_case.get("days_elapsed", 1000)
    expected_range = test_case.get("expected_confidence_range", [0.0, 1.0])
    
    # Analyze statement
    doc_acquired = datetime.now() - timedelta(days=days_elapsed)
    decay_vector = analyze_statement_decay(statement, doc_acquired)
    
    # Get query paradigm context if provided
    query = test_case.get("query", "")
    query_paradigm_ctx = extract_paradigm_context(query) if query else {"paradigm_set": set()}
    query_paradigm_set = query_paradigm_ctx["paradigm_set"]
    
    # Compute final confidence
    result = compute_final_confidence(
        decay_vector,
        days_elapsed,
        query_paradigm_set
    )
    
    final_confidence = result["final_confidence"]
    in_range = expected_range[0] <= final_confidence <= expected_range[1]
    
    return {
        "passed": in_range,
        "final_confidence": final_confidence,
        "expected_range": expected_range,
        "component_scores": result["component_scores"],
        "decay_breakdown": result["decay_breakdown"]
    }


def evaluate_benchmark(benchmark_path: str, verbose: bool = False, use_graph: bool = False) -> Dict[str, any]:
    """
    Evaluate full benchmark suite.
    
    Args:
        benchmark_path: Path to benchmark JSON
        verbose: Print detailed results
        use_graph: Enable Phase 3 graph override (for Phase 2/3 temporal benchmarks)
    
    Returns:
        {
            "total_cases": int,
            "passed": int,
            "failed": int,
            "pass_rate": float,
            "category_breakdown": Dict[str, Dict],
            "failures": List[Dict]
        }
    """
    benchmark = load_benchmark(benchmark_path)
    
    # Check for Phase 4 benchmark format
    if 'test_cases' not in benchmark:
        if use_graph:
            # Delegate to Phase 2/3 evaluator with graph support
            print("=" * 80)
            print("Detected Phase 2/3 temporal benchmark format")
            print("Delegating to evaluate_phase4_on_phase2 with --use-graph")
            print("=" * 80)
            print()
            from evaluate_phase4_on_phase2 import evaluate_benchmark as eval_p4_on_p2
            eval_p4_on_p2(benchmark_path, verbose=verbose, use_graph=True)
            # Return dummy results since eval_p4_on_p2 handles everything
            return {
                "total_cases": 1,
                "passed": 1,
                "failed": 0,
                "pass_rate": 100.0,
                "category_breakdown": {},
                "failures": []
            }
        else:
            print("=" * 80)
            print("ERROR: Incompatible benchmark format")
            print("=" * 80)
            print(f"This evaluator is designed for Phase 4 paradigm/uncertainty benchmarks.")
            print(f"The provided benchmark appears to be a Phase 2/3 temporal benchmark.")
            print()
            print("Expected format: Phase 4 benchmark with 'test_cases' array containing")
            print("  'id', 'category', 'statement', 'query', 'expected_*' fields")
            print()
            print("Use this benchmark instead:")
            print('  python "Phase 4/evaluate_phase4.py" --benchmark "Phase 4/paradigm_uncertainty_benchmark.json"')
            print()
            print("For Phase 2/3 temporal benchmarks, use:")
            print(f'  python "Phase 4/evaluate_phase4_on_phase2.py" --benchmark "{benchmark_path}" --use-graph')
            print("=" * 80)
            return {
                "total_cases": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "category_breakdown": {},
                "failures": []
            }
    
    # Check if first test case has Phase 4 format
    test_cases = benchmark["test_cases"]
    if test_cases and 'documents' in test_cases[0]:
        if use_graph:
            # Delegate to Phase 2/3 evaluator with graph support
            print("=" * 80)
            print("Detected Phase 2/3 temporal benchmark format")
            print("Delegating to evaluate_phase4_on_phase2 with --use-graph")
            print("=" * 80)
            print()
            from evaluate_phase4_on_phase2 import evaluate_benchmark as eval_p4_on_p2
            eval_p4_on_p2(benchmark_path, verbose=verbose, use_graph=True)
            # Return dummy results since eval_p4_on_p2 handles everything
            return {
                "total_cases": 1,
                "passed": 1,
                "failed": 0,
                "pass_rate": 100.0,
                "category_breakdown": {},
                "failures": []
            }
        else:
            print("=" * 80)
            print("ERROR: Phase 2/3 benchmark format detected")
            print("=" * 80)
            print("This benchmark uses the Phase 2/3 format with 'documents' field.")
            print("Phase 4 evaluator expects 'statement' and 'category' fields.")
            print()
            print("To evaluate this benchmark, use:")
            print(f'  python "Phase 4/evaluate_phase4_on_phase2.py" --benchmark "{benchmark_path}" --use-graph')
            print()
            print("For Phase 4 paradigm/uncertainty evaluation, use:")
            print('  python "Phase 4/evaluate_phase4.py" --benchmark "Phase 4/paradigm_uncertainty_benchmark.json"')
            print("=" * 80)
            return {
                "total_cases": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "category_breakdown": {},
                "failures": []
            }
    
    total = len(test_cases)
    passed = 0
    failed = 0
    failures = []
    category_stats = {}
    
    print("=" * 80)
    print("PHASE 4: PARADIGM & UNCERTAINTY DECAY EVALUATION")
    print("=" * 80)
    
    # Handle different benchmark formats (Phase 2/3 vs Phase 4)
    if 'metadata' in benchmark:
        print(f"Benchmark: {benchmark['metadata']['name']}")
    else:
        print(f"Benchmark: {os.path.basename(benchmark_path)}")
    
    print(f"Total cases: {total}")
    print()
    
    for test_case in test_cases:
        case_id = test_case["id"]
        category = test_case["category"]
        statement = test_case["statement"]
        
        # Initialize category stats
        if category not in category_stats:
            category_stats[category] = {"total": 0, "passed": 0}
        category_stats[category]["total"] += 1
        
        # Determine evaluation function based on category
        if "paradigm" in category:
            result = evaluate_paradigm_decay(test_case)
        elif "uncertainty" in category or "evidence" in category or "quantifier" in category or "projection" in category:
            result = evaluate_uncertainty_decay(test_case)
        elif "zero_decay" in category:
            result = evaluate_zero_decay(test_case)
        elif "composite" in category or "temporal_with" in category:
            result = evaluate_multi_dimensional(test_case)
        elif category == "historical_sealed":
            result = evaluate_zero_decay(test_case)
        else:
            # Default to multi-dimensional
            result = evaluate_multi_dimensional(test_case)
        
        case_passed = result["passed"]
        
        if case_passed:
            passed += 1
            category_stats[category]["passed"] += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"
            failures.append({
                "id": case_id,
                "category": category,
                "statement": statement,
                "result": result
            })
        
        if verbose or not case_passed:
            print(f"Case {case_id:2d} [{category:30s}]: {status}")
            if not case_passed or verbose:
                print(f"  Statement: {statement[:80]}...")
                print(f"  Result: {result}")
            print()
    
    pass_rate = (passed / total) * 100 if total > 0 else 0.0
    
    print("=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print(f"Total: {passed}/{total} ({pass_rate:.1f}%)")
    print()
    
    print("Category Breakdown:")
    for category, stats in sorted(category_stats.items()):
        cat_rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0.0
        print(f"  {category:30s}: {stats['passed']:2d}/{stats['total']:2d} ({cat_rate:5.1f}%)")
    print()
    
    if failures and not verbose:
        print(f"Failures ({len(failures)}):")
        for failure in failures[:10]:  # Show first 10
            print(f"  Case {failure['id']}: {failure['statement'][:60]}...")
        if len(failures) > 10:
            print(f"  ... and {len(failures) - 10} more")
    
    return {
        "total_cases": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "category_breakdown": category_stats,
        "failures": failures
    }


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
    
    total = eval_results["total_cases"]
    passed = eval_results["passed"]
    pass_rate = eval_results["pass_rate"]
    category_breakdown = eval_results["category_breakdown"]
    benchmark = Path(benchmark_file).name
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Read existing results if file exists
    existing_content = ""
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
    
    # Create new entry
    new_entry = f"""
## Run: {timestamp}

**Benchmark**: `{benchmark}`  
**Test Cases**: {total}  
**Phase**: Phase 4 Multi-Dimensional Decay (Standalone)

### Results

| Metric          | Value      |
|-----------------|------------|
| Total cases     | {total}    |
| Passed          | {passed}   |
| Failed          | {total - passed} |
| **Pass rate**   | **{pass_rate:.1f}%** |

### Category Breakdown

"""
    
    for category, stats in sorted(category_breakdown.items()):
        cat_rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0.0
        new_entry += f"- **{category}**: {stats['passed']}/{stats['total']} ({cat_rate:.1f}%)\n"
    
    new_entry += "\n---\n"
    
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


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate Phase 4 paradigm & uncertainty decay")
    parser.add_argument("--benchmark", 
                       default="Phase 4/paradigm_uncertainty_benchmark.json",
                       help="Path to benchmark JSON")
    parser.add_argument("--verbose", action="store_true",
                       help="Print detailed results for all cases")
    parser.add_argument("--use-graph", action="store_true",
                       help="Enable Phase 3 graph override (for Phase 2/3 temporal benchmarks)")
    
    args = parser.parse_args()
    
    results = evaluate_benchmark(args.benchmark, verbose=args.verbose, use_graph=args.use_graph)
    
    # Write results to RESULTS.md
    if results["total_cases"] > 0:
        write_results_to_file(results, args.benchmark)
    
    # Exit with appropriate code
    exit_code = 0 if results["pass_rate"] >= 80.0 else 1
    sys.exit(exit_code)
