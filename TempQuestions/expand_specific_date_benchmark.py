"""
Expand specific_date benchmark by combining:
1. Manual high-quality cases (from create_specific_date_benchmark.py)
2. Generated cases from TempQuestions with modified acquisition dates

This creates a larger benchmark (~200+ cases) for statistical validation.
"""

import json
from datetime import datetime
import random
import re

def extract_year_from_question(question: str):
    """Extract 4-digit year from question."""
    match = re.search(r'\b(19\d{2}|20\d{2})\b', question)
    return int(match.group(1)) if match else None


def generate_from_tempquestions(tempq_path: str, max_cases: int = 200):
    """Generate specific_date cases from TempQuestions."""
    with open(tempq_path) as f:
        tempq = json.load(f)
    
    generated_cases = []
    
    for case in tempq['test_cases'][:max_cases]:
        original_q = case.get('original_question')
        if not original_q:
            continue
            
        query_year = extract_year_from_question(original_q)
        if not query_year:
            continue
        
        # Create era-appropriate documents by modifying TempQuestions structure
        # The "current" doc has the right answer, "stale" has wrong answer
        # But we'll frame it as: docs from different eras
        
        current_doc = case['documents']['current']
        stale_doc = case['documents']['stale']
        
        # For specific_date benchmark: 
        # - Document from query_year should have correct answer (current doc content)
        # - Document from 2026 should also have correct answer (current doc content)
        # - Query asks about query_year, so query_year doc is "expected"
        # BUT: This doesn't work because stale doc has wrong content!
        
        # Skip generation from TempQuestions - it has wrong structure
        # (stale docs have placeholder text, not era-appropriate answers)
        continue
    
    return generated_cases


def load_manual_benchmark(manual_path: str):
    """Load manually created high-quality cases."""
    with open(manual_path) as f:
        data = json.load(f)
    return data['test_cases']


def create_additional_synthetic_cases():
    """Create more synthetic cases with different entities."""
    
    # Additional temporal facts beyond the original benchmark
    additional_facts = {
        "Twitter/X CEO": [
            (2006, "Jack Dorsey co-founded Twitter and served as CEO", "Jack Dorsey"),
            (2008, "Evan Williams became CEO", "Evan Williams"),
            (2010, "Dick Costolo became CEO", "Dick Costolo"),
            (2015, "Jack Dorsey returned as CEO", "Jack Dorsey"),
            (2021, "Parag Agrawal became CEO", "Parag Agrawal"),
            (2022, "Elon Musk acquired Twitter and became CEO", "Elon Musk"),
        ],
        "Netflix CEO": [
            (1997, "Reed Hastings co-founded Netflix and served as CEO", "Reed Hastings"),
            (2020, "Ted Sarandos became co-CEO alongside Reed Hastings", "Ted Sarandos"),
            (2023, "Ted Sarandos continues as co-CEO with Greg Peters", "Ted Sarandos"),
        ],
        "IBM CEO": [
            (1993, "Louis Gerstner became CEO", "Louis Gerstner"),
            (2002, "Sam Palmisano became CEO", "Sam Palmisano"),
            (2012, "Ginni Rometty became CEO", "Ginni Rometty"),
            (2020, "Arvind Krishna became CEO", "Arvind Krishna"),
        ],
        "Yahoo CEO": [
            (1995, "Jerry Yang co-founded Yahoo", "Jerry Yang"),
            (2001, "Terry Semel became CEO", "Terry Semel"),
            (2007, "Jerry Yang returned as CEO", "Jerry Yang"),
            (2009, "Carol Bartz became CEO", "Carol Bartz"),
            (2012, "Marissa Mayer became CEO", "Marissa Mayer"),
            (2017, "Yahoo was sold to Verizon", "Marissa Mayer"),
        ],
        "Disney CEO": [
            (1984, "Michael Eisner became CEO", "Michael Eisner"),
            (2005, "Bob Iger became CEO", "Bob Iger"),
            (2020, "Bob Chapek became CEO", "Bob Chapek"),
            (2022, "Bob Iger returned as CEO", "Bob Iger"),
        ],
        "Germany Chancellor": [
            (1998, "Gerhard Schröder became Chancellor", "Gerhard Schröder"),
            (2005, "Angela Merkel became Chancellor", "Angela Merkel"),
            (2021, "Olaf Scholz became Chancellor", "Olaf Scholz"),
        ],
        "Japan PM": [
            (2006, "Shinzo Abe became Prime Minister", "Shinzo Abe"),
            (2007, "Yasuo Fukuda became Prime Minister", "Yasuo Fukuda"),
            (2008, "Taro Aso became Prime Minister", "Taro Aso"),
            (2009, "Yukio Hatoyama became Prime Minister", "Yukio Hatoyama"),
            (2012, "Shinzo Abe returned as Prime Minister", "Shinzo Abe"),
            (2020, "Yoshihide Suga became Prime Minister", "Yoshihide Suga"),
            (2021, "Fumio Kishida became Prime Minister", "Fumio Kishida"),
        ],
    }
    
    test_cases = []
    
    for entity, facts in additional_facts.items():
        for i, (query_year, fact_text, person) in enumerate(facts):
            if query_year >= 2024:
                continue
            
            # Generate query
            if "CEO" in entity:
                company = entity.replace(" CEO", "").replace("/", " or ")
                query = f"Who was the CEO of {company} in {query_year}?"
            elif "Chancellor" in entity:
                country = entity.replace(" Chancellor", "")
                query = f"Who was the Chancellor of {country} in {query_year}?"
            elif "PM" in entity:
                country = entity.replace(" PM", "")
                query = f"Who was the Prime Minister of {country} in {query_year}?"
            else:
                query = f"Who held the position of {entity} in {query_year}?"
            
            # Create documents from different eras
            documents = {}
            documents[f"from_{query_year}"] = {
                "text": f"{person} holds this position. {fact_text}.",
                "acquired": f"{query_year}-06-15T00:00:00Z",
                "is_correct": True,
                "era": query_year
            }
            
            # Add 1-2 documents from other eras
            for j, (other_year, other_fact, other_person) in enumerate(facts):
                if other_year == query_year:
                    continue
                if abs(other_year - query_year) <= 10 or j == len(facts) - 1:
                    documents[f"from_{other_year}"] = {
                        "text": f"{other_person} holds this position. {other_fact}.",
                        "acquired": f"{other_year}-06-15T00:00:00Z",
                        "is_correct": False,
                        "era": other_year
                    }
            
            # Ensure at least 2 documents - if only 1, add one more from different era
            if len(documents) < 2:
                # Add the closest other year
                for other_year, other_fact, other_person in facts:
                    if other_year != query_year:
                        documents[f"from_{other_year}"] = {
                            "text": f"{other_person} holds this position. {other_fact}.",
                            "acquired": f"{other_year}-06-15T00:00:00Z",
                            "is_correct": False,
                            "era": other_year
                        }
                        break
            
            test_cases.append({
                "query": query,
                "entity": entity,
                "query_year": query_year,
                "documents": documents,
                "expected_winner": f"from_{query_year}",
                "reasoning": f"Query asks about {query_year}, should prefer document from {query_year}"
            })
    
    return test_cases


def main():
    # Load manual high-quality cases
    manual_cases = load_manual_benchmark("cache/benchmarks/specific_date_benchmark.json")
    print(f"Loaded {len(manual_cases)} manual cases")
    
    # Generate additional synthetic cases
    synthetic_cases = create_additional_synthetic_cases()
    print(f"Generated {len(synthetic_cases)} additional synthetic cases")
    
    # Combine
    all_cases = manual_cases + synthetic_cases
    
    # Remove duplicates based on query
    seen_queries = set()
    unique_cases = []
    for case in all_cases:
        if case['query'] not in seen_queries:
            seen_queries.add(case['query'])
            unique_cases.append(case)
    
    print(f"Total unique cases: {len(unique_cases)}")
    
    # Create expanded benchmark
    benchmark = {
        "source": "Specific_Date_Benchmark_Expanded",
        "version": "2.0",
        "creation_date": datetime.now().isoformat(),
        "total_cases": len(unique_cases),
        "description": "Expanded benchmark for testing query temporal intent with explicit years. "
                      "Includes manual high-quality cases plus additional synthetic cases. "
                      "All documents contain era-appropriate correct information.",
        "test_cases": unique_cases
    }
    
    output_path = "cache/benchmarks/specific_date_benchmark_large.json"
    with open(output_path, 'w') as f:
        json.dump(benchmark, f, indent=2)
    
    print(f"\nSaved to: {output_path}")
    print(f"Total test cases: {len(unique_cases)}")
    
    # Show distribution
    year_counts = {}
    for case in unique_cases:
        year = case['query_year']
        decade = (year // 10) * 10
        year_counts[decade] = year_counts.get(decade, 0) + 1
    
    print("\nDistribution by decade:")
    for decade in sorted(year_counts.keys()):
        print(f"  {decade}s: {year_counts[decade]} cases")


if __name__ == "__main__":
    main()
