import re

test_queries = [
    "Who was the CEO of Apple before Tim Cook?",
    "Who became the Prime Minister after Margaret Thatcher?",
    "Who leads the company since Tim Cook's departure?",
]

for query in test_queries:
    text_lower = query.lower()
    before_match = re.search(r'before\s+([\w\']+(?:\s+[\w\']+)*)', text_lower)
    after_match = re.search(r'(?:after|since)\s+([\w\']+(?:\s+[\w\']+)*)', text_lower)
    
    print(f"\nQuery: {query}")
    print(f"  Before match: {before_match.group(0) if before_match else None}")
    print(f"  Before entity: {before_match.group(1) if before_match else None}")
    print(f"  After match: {after_match.group(0) if after_match else None}")
    print(f"  After entity: {after_match.group(1) if after_match else None}")
