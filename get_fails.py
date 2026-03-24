import json
import sys
sys.path.append("Phase 2")
from evaluate_query_intent import evaluate_query_intent

res = evaluate_query_intent("TempQuestions/cache/benchmarks/complex_bench.json", use_original=True, use_graph=True, verbose=False)

print(res.keys())
