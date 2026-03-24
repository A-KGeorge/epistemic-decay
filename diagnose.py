import json
from collections import Counter

with open("TempQuestions/cache/benchmarks/complex_bench.json", "r") as f:
    data = json.load(f)

entities_in_failures = []
for test in data["test_cases"]:
    query = test.get("original_question", test["query"])
    words = query.split()
    for word in words:
        if len(word) > 1 and word[0].isupper() and word not in ["In", "What", "Who", "When", "Where", "Is", "Are", "Did", "Does", "How", "Which", "Why"]:
            entities_in_failures.append(word.strip("?,.:;\"'"))

common_entities = Counter(entities_in_failures).most_common(50)
print("Top Entities:")
for ent, count in common_entities:
    print(f" - {ent}: {count}")
