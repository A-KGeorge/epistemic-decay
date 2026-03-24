import re
from collections import Counter

fails = []
current_case = ""
with open("output_verbose.txt", "r", encoding="utf-16") as f:
    for line in f:
        if line.startswith("Case"):
            current_case = line.split(":", 1)[1].strip()
        elif "Phase 2:  FAIL" in line:
            fails.append(current_case)

entities = []
for q in fails:
    words = q.split()
    for w in words:
        w = w.strip("?,.:;\"'")
        if w and w[0].isupper() and w not in ["In", "What", "Who", "When", "Where", "Is", "Are", "Did", "Does", "How", "Which", "Why", "The", "A"]:
            entities.append(w)

print("Number of fails:", len(fails))
print("Top Entities in Failures:")
for ent, count in Counter(entities).most_common(20):
    print(f"{ent}: {count}")
