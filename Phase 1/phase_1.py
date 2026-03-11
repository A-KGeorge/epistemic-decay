import numpy as np
from numpy.linalg import norm
from datetime import datetime

# Import functions and benchmark data from shared modules
from decay_functions import embed_with_decay, model
from benchmark_data import benchmark

# Run benchmark

def cosine_similarity(a, b):
    return np.dot(a, b) / (norm(a) * norm(b))

def run_benchmark_case(query, kb_entries):
    """
    Returns: (standard_is_correct, decay_is_correct, diagnostics)
    """
    query_vec = model.encode(query)
    current_date = datetime.now()
    
    standard_scores = []
    decay_scores = []
    
    for entry in kb_entries:
        last_verified = entry.get("last_verified")
        category = entry.get("category")
        vec = embed_with_decay(entry["text"], entry["acquired"], category, last_verified)
        semantic_sim = cosine_similarity(query_vec, vec[:-1])  # First 384 dims
        confidence = vec[-1]  # Last dim
        decay_score = semantic_sim * confidence
        
        standard_scores.append((semantic_sim, entry, confidence))
        decay_scores.append((decay_score, entry, confidence))
    
    standard_scores_sorted = sorted(standard_scores, key=lambda x: x[0], reverse=True)
    decay_scores_sorted = sorted(decay_scores, key=lambda x: x[0], reverse=True)
    
    standard_top = standard_scores_sorted[0]
    decay_top = decay_scores_sorted[0]
    
    # Infer correctness from valid_until dates
    standard_is_correct = (standard_top[1]["valid_until"] is None or 
                          standard_top[1]["valid_until"] >= current_date)
    decay_is_correct = (decay_top[1]["valid_until"] is None or 
                       decay_top[1]["valid_until"] >= current_date)
    
    # Diagnostics
    diagnostics = {
        "standard_top_score": standard_top[0],
        "decay_top_score": decay_top[0],
        "standard_top_confidence": standard_top[2],
        "decay_top_confidence": decay_top[2],
        "standard_top_text": standard_top[1]["text"],
        "decay_top_text": decay_top[1]["text"],
        "all_confidences": [(entry["text"][:60], conf) for _, entry, conf in standard_scores]
    }
    
    return standard_is_correct, decay_is_correct, diagnostics

# Run all 23 cases
results = {
    "both_correct": 0,
    "decay_correct_only": 0,
    "standard_correct_only": 0,
    "both_wrong": 0
}

rescued_cases = []
stable_cases = []

print("=" * 80)
print("ADVERSARIAL BENCHMARK: Standard vs. Decay Retrieval")
print("=" * 80)
print()

for i, case in enumerate(benchmark, 1):
    standard_correct, decay_correct, diagnostics = run_benchmark_case(case["query"], case["entries"])
    
    if standard_correct and decay_correct:
        outcome = "both_correct"
        symbol = "[=]"
        stable_cases.append((case["query"], diagnostics))
    elif decay_correct and not standard_correct:
        outcome = "decay_correct_only"
        symbol = "[+]"
        rescued_cases.append((case["query"], diagnostics))
    elif standard_correct and not decay_correct:
        outcome = "standard_correct_only"
        symbol = "[-]"
    else:
        outcome = "both_wrong"
        symbol = "[X]"
    
    results[outcome] += 1
    
    print(f"{symbol} Case {i:2d}: {case['query']}")
    print(f"         Standard: {'+' if standard_correct else '-'}  |  Decay: {'+' if decay_correct else '-'}  |  [{outcome}]")
    print()

print("=" * 80)
print("RESULTS SUMMARY")
print("=" * 80)
print(f"Both correct:           {results['both_correct']:2d}  (decay adds no value but doesn't hurt)")
print(f"Decay correct only:     {results['decay_correct_only']:2d}  (decay rescued a case standard got wrong) [+]")
print(f"Standard correct only:  {results['standard_correct_only']:2d}  (decay hurt a case - failure mode) [-]")
print(f"Both wrong:             {results['both_wrong']:2d}  (neither works)")
print()

if results['decay_correct_only'] > 0 and results['standard_correct_only'] <= 1:
    print("[SUCCESS] DECAY RETRIEVAL ADDS VALUE")
    print(f"  Rescued {results['decay_correct_only']} cases where standard retrieval failed")
    print(f"  Only {results['standard_correct_only']} regression(s)")
elif results['decay_correct_only'] == 0:
    print("[FAIL] DECAY RETRIEVAL ADDS NO VALUE")
    print("  No cases where decay outperformed standard retrieval")
else:
    print("[MIXED] RESULTS")
    print(f"  Decay rescued {results['decay_correct_only']} cases")
    print(f"  But caused {results['standard_correct_only']} regressions")

# VERIFICATION 1: Check confidence values on stable facts
print("\n" + "=" * 80)
print("VERIFICATION 1: Confidence Values on Stable Facts")
print("=" * 80)
print("Stable facts should maintain high confidence despite age")
print("Mathematical truths (decay=0.0) should have conf=1.0")
print("Physical laws (decay=0.0001) and geographic facts (decay=0.0002) should have conf>0.5")
print()

for query, diag in stable_cases:
    print(f"Query: {query}")
    for text, conf in diag["all_confidences"]:
        status = ""
        if conf >= 0.99:
            status = "[PERFECT]"
        elif conf >= 0.5:
            status = "[GOOD]"
        elif conf >= 0.3:
            status = "[OK]"
        else:
            status = "[LOW]"
        print(f"  confidence: {conf:.4f} {status} | {text}")
    print()

# VERIFICATION 2: Score margins on rescued cases
print("=" * 80)
print("VERIFICATION 2: Decay Correctly Flips Rankings")
print("=" * 80)
print("For each rescued case:")
print("- Standard picks stale (high semantic, low confidence)")
print("- Decay picks current (lower semantic, higher confidence)")
print("- Margin shows how strongly decay prefers current")
print()

for query, diag in rescued_cases:
    print(f"Query: {query}")
    
    # The standard top is the stale doc, decay top is the current doc
    print(f"  Standard picked (STALE):")
    print(f"    Semantic similarity: {diag['standard_top_score']:.4f}")
    print(f"    Confidence: {diag['standard_top_confidence']:.4f}")
    print(f"    Weighted score (if using decay): {diag['standard_top_score'] * diag['standard_top_confidence']:.4f}")
    print(f"    Text: {diag['standard_top_text'][:65]}")
    
    print(f"  Decay picked (CURRENT):")
    print(f"    Weighted score: {diag['decay_top_score']:.4f}")
    print(f"    Confidence: {diag['decay_top_confidence']:.4f}")
    print(f"    Text: {diag['decay_top_text'][:65]}")
    
    # Calculate margin - how much better current is than stale under decay weighting
    stale_under_decay = diag['standard_top_score'] * diag['standard_top_confidence']
    current_under_decay = diag['decay_top_score']
    margin = current_under_decay - stale_under_decay
    
    status = "[STRONG]" if margin > 0.1 else "[ROBUST]" if margin > 0.01 else "[WEAK]" if margin > 0 else "[FAIL]"
    print(f"  Decay margin: {margin:+.4f} {status}")
    print()
    