"""
Test temporal overlap with document text matching
"""

import sys
sys.path.insert(0, '.')

from knowledge_graph import TemporalKnowledgeGraph
from graph_matching import compute_graph_alignment
import json

# Load knowledge graph
with open('graph_facts.json', 'r') as f:
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

print(f"Loaded graph with {graph.graph.number_of_nodes()} nodes\n")

# Test query
query = "Who was the US President while Steve Jobs was the CEO of Apple?"

# Test with Clinton document
clinton_doc = "Bill Clinton served as US President from 1993 to 2001."
trump_doc = "Donald Trump served as US President from 2017 to 2021."

print("=" * 80)
print(f"Query: {query}")
print("=" * 80)
print()

print("Doc 1 (Clinton):")
print(f"  Text: {clinton_doc}")
result1 = compute_graph_alignment(query, graph, doc_text=clinton_doc)
print(f"  Score: {result1['score']}")
print(f"  Matched entity: {result1['matched_entity']}")
print(f"  All matches: {result1['all_matches']}")
print()

print("Doc 2 (Trump):")
print(f"  Text: {trump_doc}")
result2 = compute_graph_alignment(query, graph, doc_text=trump_doc)
print(f"  Score: {result2['score']}")
print(f"  Matched entity: {result2['matched_entity']}")
print(f"  All matches: {result2['all_matches']}")
print()

if result1['matched_entity'] == "Bill Clinton":
    print("✓ SUCCESS: Clinton document correctly matched to Bill Clinton!")
else:
    print(f"✗ FAIL: Expected Bill Clinton, got {result1['matched_entity']}")
