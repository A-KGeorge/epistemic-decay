import sys
sys.path.insert(0, "./Phase 2")
from evaluate_query_intent import load_phase3_graph
kg = load_phase3_graph("Phase 3/graph_facts.json")
for u, v, data in kg.graph.edges(data=True):
    print(data)
    break
