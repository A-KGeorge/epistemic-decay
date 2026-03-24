import json
import sys
sys.path.append("Phase 2")
from evaluate_query_intent import evaluate_query_intent

with open("TempQuestions/cache/benchmarks/complex_bench.json", "r") as f:
    data = json.load(f)

# The evaluate_query_intent prints standard, phase1, phase2, phase3 correct.
# It doesn't return the failures, so let's just make a quick loop here like in the evaluator.

from phase_1 import compute_relevance_score
from query_intent import classify_temporal_intent, compute_temporal_alignment
from datetime import datetime
import os
sys.path.append("Phase 3")
from graph_matching import StructuralMatcher
from knowledge_graph import TemporalKnowledgeGraph
import warnings
warnings.filterwarnings('ignore')

matcher = StructuralMatcher()
try:
    matcher.graph = TemporalKnowledgeGraph.load("Phase 3/graph_facts.json")
except Exception:
    pass

fails = []
for test in data["test_cases"]:
    query = test.get("original_question", test["query"])
    query_intent = classify_temporal_intent(query)
    
    # Just look at standard evaluation of bm25 or whatever fail
    # We want to find cases that phase 2 still fails.
    doc1 = test["documents"][0]
    doc2 = test["documents"][1]
    
    # Expected is doc1 if standard is perfect? Unclear, let's just find "Airlines" cases
