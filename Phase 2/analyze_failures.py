"""
Analyze Phase 2 failures on specific_date benchmark to understand limitations.
"""

import json
import sys

def analyze_failures():
    # Load results manually from verbose output
    failures = [
        {
            "query": "Who was Amazon's CEO in 2021?",
            "query_year": 2021,
            "expected": "from_2021",
            "phase2_picked": "from_2024",
            "alignment_correct": 1.30,
            "alignment_wrong": 1.10,
            "year_distance": 3,
            "reasoning": "Amazon CEO 2021 (Andy Jassy) vs 2024 (Andy Jassy continues). Same person, minimal semantic difference. 1.30/1.10 = 1.18x boost insufficient."
        },
        {
            "query": "Who was Google's CEO in 2001?",
            "query_year": 2001,
            "expected": "from_2001",
            "phase2_picked": "from_1998",
            "alignment_correct": 1.30,
            "alignment_wrong": 1.10,
            "year_distance": 3,
            "reasoning": "Google CEO 2001 (Eric Schmidt) vs 1998 (Larry Page). Different people but similar founder/leadership context. Semantic similarity gap."
        },
        {
            "query": "Who was the President of France in 2007?",
            "query_year": 2007,
            "expected": "from_2007",
            "phase2_picked": "from_2012",
            "alignment_correct": 1.30,
            "alignment_wrong": 1.05,
            "year_distance": 5,
            "reasoning": "France 2007 (Sarkozy) vs 2012 (Hollande). Different people, 5-year gap = 1.05x multiplier. 1.30/1.05 = 1.24x insufficient."
        },
        {
            "query": "Who was the CEO of Twitter or X in 2008?",
            "query_year": 2008,
            "expected": "from_2008",
            "phase2_picked": "from_2006",
            "alignment_correct": 1.30,
            "alignment_wrong": 1.10,
            "year_distance": 2,
            "reasoning": "Twitter 2008 (Evan Williams) vs 2006 (Jack Dorsey). Different people but both founders. 2-year gap = 1.10x, ratio 1.18x insufficient."
        },
        {
            "query": "Who was the CEO of Twitter or X in 2010?",
            "query_year": 2010,
            "expected": "from_2010",
            "phase2_picked": "from_2006",
            "alignment_correct": 1.30,
            "alignment_wrong": 1.05,
            "year_distance": 4,
            "reasoning": "Twitter 2010 (Dick Costolo) vs 2006 (Jack Dorsey). Semantic similarity to founder era stronger than correct answer."
        },
        {
            "query": "Who was the CEO of Netflix in 2020?",
            "query_year": 2020,
            "expected": "from_2020",
            "phase2_picked": "from_2023",
            "alignment_correct": 1.30,
            "alignment_wrong": 1.10,
            "year_distance": 3,
            "reasoning": "Netflix 2020 (Ted Sarandos co-CEO) vs 2023 (Ted Sarandos continues). Same person, minimal semantic difference."
        }
    ]
    
    print("="*80)
    print("PHASE 2 FAILURE ANALYSIS (6/61 cases)")
    print("="*80)
    print()
    
    for i, failure in enumerate(failures, 1):
        print(f"{i}. {failure['query']}")
        print(f"   Query year: {failure['query_year']}")
        print(f"   Expected: {failure['expected']}")
        print(f"   Phase 2 picked: {failure['phase2_picked']}")
        print(f"   Alignment: correct={failure['alignment_correct']}x, wrong={failure['alignment_wrong']}x")
        print(f"   Boost ratio: {failure['alignment_correct'] / failure['alignment_wrong']:.2f}x")
        print(f"   Year distance: {failure['year_distance']} years")
        print(f"   → {failure['reasoning']}")
        print()
    
    print("="*80)
    print("COMMON PATTERNS IN FAILURES")
    print("="*80)
    print()
    print("1. CONTINUITY CASES (2/6): Same person across years")
    print("   - Amazon 2021 vs 2024 (Andy Jassy)")
    print("   - Netflix 2020 vs 2023 (Ted Sarandos)")
    print("   → Semantic embeddings nearly identical, alignment multiplier insufficient")
    print()
    print("2. SMALL YEAR GAPS (4/6): 2-5 years apart")
    print("   - Google 2001 vs 1998 (3 years)")
    print("   - France 2007 vs 2012 (5 years)")
    print("   - Twitter 2008 vs 2006 (2 years)")
    print("   - Twitter 2010 vs 2006 (4 years)")
    print("   → Alignment multipliers 1.05-1.10x create only 1.18-1.24x boost ratio")
    print("   → Insufficient to overcome semantic similarity gaps")
    print()
    print("="*80)
    print("FUNDAMENTAL LIMITATION")
    print("="*80)
    print()
    print("Phase 2 temporal alignment applies SCALAR MULTIPLIERS to similarity scores.")
    print("This works when semantic similarity is close (e.g., 1997 vs 2024 = 27 years → strong penalty).")
    print()
    print("But when:")
    print("  - Same person across years (continuity): semantics ~identical")
    print("  - Small year gaps: multipliers 1.05-1.10x too weak")
    print()
    print("Then alignment multipliers can't overcome the semantic gap.")
    print()
    print("SOLUTION → Phase 3: Dependency graphs")
    print("  - Structural knowledge: 'Andy Jassy became CEO in 2021'")
    print("  - Date constraints: 2021 query → match tenure start/end")
    print("  - Not semantic similarity, but STRUCTURAL FACT MATCHING")
    print()
    print("Surface similarity (Phase 2) fails where structural knowledge (Phase 3) excels.")
    print()


if __name__ == "__main__":
    analyze_failures()
