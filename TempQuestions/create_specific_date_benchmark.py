"""
Create a dedicated benchmark for testing Phase 2 query temporal intent.

Unlike TempQuestions (which has stale=WRONG, current=RIGHT), this benchmark has:
- Documents from multiple eras, each with era-appropriate CORRECT information
- Queries with explicit years
- Tests Phase 2's ability to match query year to document content year
"""

import json
from datetime import datetime
import random

# Temporal facts: entity -> [(year, fact, person/value), ...]
TEMPORAL_FACTS = {
    "Apple CEO": [
        (1997, "Steve Jobs returned as CEO", "Steve Jobs"),
        (2011, "Tim Cook became CEO after Steve Jobs", "Tim Cook"),
        (2024, "Tim Cook continues as CEO", "Tim Cook"),
    ],
    "Microsoft CEO": [
        (1975, "Bill Gates co-founded Microsoft and served as CEO", "Bill Gates"),
        (2000, "Steve Ballmer became CEO", "Steve Ballmer"),
        (2014, "Satya Nadella became CEO", "Satya Nadella"),
        (2024, "Satya Nadella continues as CEO", "Satya Nadella"),
    ],
    "Amazon CEO": [
        (1994, "Jeff Bezos founded Amazon and served as CEO", "Jeff Bezos"),
        (2021, "Andy Jassy became CEO after Jeff Bezos stepped down", "Andy Jassy"),
        (2024, "Andy Jassy continues as CEO", "Andy Jassy"),
    ],
    "Google CEO": [
        (1998, "Larry Page co-founded Google and served as CEO", "Larry Page"),
        (2001, "Eric Schmidt became CEO", "Eric Schmidt"),
        (2011, "Larry Page returned as CEO", "Larry Page"),
        (2015, "Sundar Pichai became CEO", "Sundar Pichai"),
        (2024, "Sundar Pichai continues as CEO", "Sundar Pichai"),
    ],
    "Facebook/Meta CEO": [
        (2004, "Mark Zuckerberg founded Facebook and has remained CEO", "Mark Zuckerberg"),
        (2024, "Mark Zuckerberg continues as CEO of Meta", "Mark Zuckerberg"),
    ],
    "Tesla CEO": [
        (2008, "Elon Musk became CEO of Tesla", "Elon Musk"),
        (2024, "Elon Musk continues as CEO", "Elon Musk"),
    ],
    "UK Prime Minister": [
        (1997, "Tony Blair served as Prime Minister", "Tony Blair"),
        (2007, "Gordon Brown became Prime Minister", "Gordon Brown"),
        (2010, "David Cameron became Prime Minister", "David Cameron"),
        (2016, "Theresa May became Prime Minister", "Theresa May"),
        (2019, "Boris Johnson became Prime Minister", "Boris Johnson"),
        (2022, "Liz Truss briefly served as Prime Minister", "Liz Truss"),
        (2024, "Rishi Sunak serves as Prime Minister", "Rishi Sunak"),
    ],
    "US President": [
        (1993, "Bill Clinton served as President", "Bill Clinton"),
        (2001, "George W. Bush became President", "George W. Bush"),
        (2009, "Barack Obama became President", "Barack Obama"),
        (2017, "Donald Trump became President", "Donald Trump"),
        (2021, "Joe Biden became President", "Joe Biden"),
        (2024, "Joe Biden continues as President", "Joe Biden"),
    ],
    "France President": [
        (1995, "Jacques Chirac served as President", "Jacques Chirac"),
        (2007, "Nicolas Sarkozy became President", "Nicolas Sarkozy"),
        (2012, "François Hollande became President", "François Hollande"),
        (2017, "Emmanuel Macron became President", "Emmanuel Macron"),
        (2024, "Emmanuel Macron continues as President", "Emmanuel Macron"),
    ],
}


def generate_test_cases():
    """Generate test cases with multiple documents per query, each from different eras."""
    test_cases = []
    
    for entity, facts in TEMPORAL_FACTS.items():
        # For each temporal fact, create a query asking about that specific year
        for i, (query_year, fact_text, person) in enumerate(facts):
            # Skip the most recent era for now (focus on historical queries)
            if query_year >= 2024:
                continue
                
            # Generate query variations
            if "CEO" in entity:
                company = entity.replace(" CEO", "")
                queries = [
                    f"Who was the CEO of {company} in {query_year}?",
                    f"Who was {company}'s CEO in {query_year}?",
                ]
            elif "Prime Minister" in entity:
                country = entity.replace(" Prime Minister", "")
                queries = [
                    f"Who was the Prime Minister of {country} in {query_year}?",
                    f"Who was {country}'s PM in {query_year}?",
                ]
            elif "President" in entity:
                country = entity.replace(" President", "")
                queries = [
                    f"Who was the President of {country} in {query_year}?",
                    f"Who was {country}'s President in {query_year}?",
                ]
            else:
                queries = [f"Who held the position of {entity} in {query_year}?"]
            
            query = random.choice(queries)
            
            # Create documents from different eras
            documents = {}
            
            # Add document from the queried year (CORRECT answer)
            documents[f"from_{query_year}"] = {
                "text": f"{person} holds this position. {fact_text}.",
                "acquired": f"{query_year}-06-15T00:00:00Z",
                "is_correct": True,
                "era": query_year
            }
            
            # Add documents from other eras (also CORRECT for their time, but WRONG for query year)
            for j, (other_year, other_fact, other_person) in enumerate(facts):
                if other_year == query_year:
                    continue
                    
                # Add 1-2 documents from other eras as distractors
                if abs(other_year - query_year) <= 10 or j == len(facts) - 1:
                    documents[f"from_{other_year}"] = {
                        "text": f"{other_person} holds this position. {other_fact}.",
                        "acquired": f"{other_year}-06-15T00:00:00Z",
                        "is_correct": False,
                        "era": other_year
                    }
            
            # Ensure at least 2 documents
            if len(documents) < 2:
                for other_year, other_fact, other_person in facts:
                    if other_year != query_year:
                        documents[f"from_{other_year}"] = {
                            "text": f"{other_person} holds this position. {other_fact}.",
                            "acquired": f"{other_year}-06-15T00:00:00Z",
                            "is_correct": False,
                            "era": other_year
                        }
                        break
            
            # The correct document is from the query year
            expected_winner = f"from_{query_year}"
            
            test_cases.append({
                "query": query,
                "entity": entity,
                "query_year": query_year,
                "documents": documents,
                "expected_winner": expected_winner,
                "reasoning": f"Query asks about {query_year}, should prefer document from {query_year} with era-appropriate information"
            })
    
    return test_cases


def main():
    test_cases = generate_test_cases()
    
    benchmark = {
        "source": "Specific_Date_Benchmark",
        "version": "1.0",
        "creation_date": datetime.now().isoformat(),
        "total_cases": len(test_cases),
        "description": "Benchmark for testing query temporal intent with explicit years. "
                      "Unlike TempQuestions, all documents contain era-appropriate CORRECT information. "
                      "Phase 2 should match query year to document acquisition year.",
        "test_cases": test_cases
    }
    
    output_path = "cache/benchmarks/specific_date_benchmark.json"
    with open(output_path, 'w') as f:
        json.dump(benchmark, f, indent=2)
    
    print("=" * 80)
    print("SPECIFIC DATE BENCHMARK CREATED")
    print("=" * 80)
    print(f"Total test cases: {len(test_cases)}")
    print(f"Output: {output_path}")
    print()
    print("Sample cases:")
    for i, case in enumerate(test_cases[:3]):
        print(f"\n{i+1}. {case['query']}")
        print(f"   Entity: {case['entity']}")
        print(f"   Query year: {case['query_year']}")
        print(f"   Documents: {len(case['documents'])} from different eras")
        print(f"   Expected: {case['expected_winner']}")
    
    print("\n" + "=" * 80)
    print("KEY DIFFERENCE FROM TEMPQUESTIONS:")
    print("=" * 80)
    print("TempQuestions: stale=WRONG (placeholder), current=RIGHT")
    print("This benchmark: all docs=RIGHT for their era, Phase 2 picks matching year")
    print()

if __name__ == "__main__":
    main()
