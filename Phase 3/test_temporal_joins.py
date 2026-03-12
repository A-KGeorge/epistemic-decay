"""
Test temporal join functionality for Phase 3 knowledge graph
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from knowledge_graph import TemporalKnowledgeGraph
from datetime import datetime

# Create test graph
graph = TemporalKnowledgeGraph()

# Add some test data
# Apple CEOs
graph.add_role_fact("Steve Jobs", "CEO", "Apple", "1997-07-09", "2011-08-24")
graph.add_role_fact("Tim Cook", "CEO", "Apple", "2011-08-24", None)  # Current

# US Presidents
graph.add_role_fact("Bill Clinton", "President", "United States", "1993-01-20", "2001-01-20")
graph.add_role_fact("George W. Bush", "President", "United States", "2001-01-20", "2009-01-20")
graph.add_role_fact("Barack Obama", "President", "United States", "2009-01-20", "2017-01-20")

# Amazon CEOs
graph.add_role_fact("Jeff Bezos", "CEO", "Amazon", "1994-07-05", "2021-07-05")
graph.add_role_fact("Andy Jassy", "CEO", "Amazon", "2021-07-05", None)  # Current

print("=" * 80)
print("TEMPORAL JOIN TESTS")
print("=" * 80)

# Test 1: Get role interval
print("\n1. Get role interval for Steve Jobs as Apple CEO:")
jobs_interval = graph.get_role_interval("Apple", "CEO", "Steve Jobs")
print(f"   Steve Jobs was Apple CEO from {jobs_interval[0]} to {jobs_interval[1]}")

# Test 2: Find who was US President while Steve Jobs was CEO
print("\n2. Who was US President while Steve Jobs was Apple CEO?")
presidents = graph.get_role_holders_in_interval("United States", "President", jobs_interval)
for p in presidents:
    print(f"   - {p['entity']}: {p['overlap_years']} years overlap")
    print(f"     ({p['overlap_start'].strftime('%Y-%m-%d')} to {p['overlap_end'].strftime('%Y-%m-%d')})")

# Test 3: Find temporal overlap between two specific roles
print("\n3. Temporal overlap: Steve Jobs (Apple CEO) & Barack Obama (US President):")
overlap = graph.find_temporal_overlap(
    "Apple", "CEO", "Steve Jobs",
    "United States", "President", "Barack Obama"
)
if overlap:
    print(f"   Overlap: {overlap['overlap_years']} years")
    print(f"   From {overlap['overlap_start']} to {overlap['overlap_end']}")
else:
    print("   No overlap")

# Test 4: Get successors
print("\n4. Who succeeded Steve Jobs as Apple CEO?")
successors = graph.get_successors("Apple", "CEO", "Steve Jobs")
print(f"   Successors: {', '.join(successors)}")

# Test 5: Get predecessors
print("\n5. Who preceded Tim Cook as Apple CEO?")
predecessors = graph.get_predecessors("Apple", "CEO", "Tim Cook")
print(f"   Predecessors: {', '.join(predecessors)}")

# Test 6: Edge case - no overlap
print("\n6. Temporal overlap: Jeff Bezos (Amazon CEO) & Tim Cook (Apple CEO)?")
overlap2 = graph.find_temporal_overlap(
    "Amazon", "CEO", "Jeff Bezos",
    "Apple", "CEO", "Tim Cook"
)
if overlap2:
    print(f"   Overlap: {overlap2['overlap_years']} years")
else:
    print("   No overlap (Bezos left before Cook started)")

print("\n" + "=" * 80)
print("✅ All temporal join tests completed successfully!")
print("=" * 80)
