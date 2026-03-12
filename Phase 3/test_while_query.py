"""
Test temporal overlap ("while") query handling
"""

import sys
sys.path.insert(0, 'Phase 3')

from knowledge_graph import TemporalKnowledgeGraph
from query_graph import extract_query_constraints
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
    
    for succession in case_data.get("successions", []):
        graph.add_succession(
            predecessor_entity=succession["predecessor"],
            successor_entity=succession["successor"],
            role=succession["role"],
            org=succession["org"],
            transition_date=succession["transition_date"]
        )

print(f"Loaded graph with {graph.graph.number_of_nodes()} nodes")
print()

# Test query
query = "Who was the US President while Steve Jobs was the CEO of Apple?"

print("=" * 80)
print(f"Query: {query}")
print("=" * 80)
print()

# Extract constraints
constraints = extract_query_constraints(query)
print("Extracted constraints:")
for key, value in constraints.items():
    print(f"  {key}: {value}")
print()

# Test graph alignment
result = compute_graph_alignment(query, graph)
print("Graph alignment result:")
for key, value in result.items():
    if key != "constraints":
        print(f"  {key}: {value}")
print()

# Test Steve Jobs interval
print("Testing get_role_interval for Steve Jobs:")
try:
    interval = graph.get_role_interval("Apple", "CEO", "Steve Jobs")
    print(f"  Steve Jobs CEO of Apple: {interval}")
except Exception as e:
    print(f"  ERROR: {e}")
print()

# Test get_role_holders_in_interval
if interval and interval[0]:
    print(f"Testing get_role_holders_in_interval for US Presidents during {interval}:")
    try:
        holders = graph.get_role_holders_in_interval("United States", "President", interval)
        print(f"  Found {len(holders)} holders:")
        for h in holders:
            print(f"    - {h['entity']}: {h.get('overlap_years', 0):.2f} years overlap")
    except Exception as e:
        print(f"  ERROR: {e}")
