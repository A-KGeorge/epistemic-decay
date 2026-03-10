"""
TempQuestions to Decay Retrieval Benchmark Converter

TempQuestions dataset contains temporal QA pairs like:
  Q: "Who was the US President in 1998?"
  A: "Bill Clinton"
  
This script converts them to retrieval ranking tests:
  Query: "Who is the US President?"
  Documents:
    - Stale (1998): "Bill Clinton serves as 42nd President..."
    - Current (2025): "Donald Trump is President."
  Test: Does decay rank current higher?
"""

import json
from datetime import datetime
from typing import List, Dict, Tuple


class TempQuestionsConverter:
    """
    Converts TempQuestions temporal QA to retrieval ranking benchmarks.
    
    Strategy:
    1. Extract temporal constraint from question ("in 1998")
    2. Generate current version of the same question
    3. Create stale document (answer from past) vs current document
    4. Test if decay correctly prefers current
    """
    
    def __init__(self):
        self.temporal_patterns = [
            ("in {year}", r"in (\d{4})"),
            ("during {year}", r"during (\d{4})"),
            ("as of {year}", r"as of (\d{4})"),
            ("back in {year}", r"back in (\d{4})"),
        ]
    
    def parse_tempquestion(self, question: str, answer: str, year: int = None) -> Dict:
        """
        Parse a TempQuestions entry.
        
        Args:
            question: Temporal question (e.g., "Who was President in 1998?")
            answer: Expected answer (e.g., "Bill Clinton")
            year: Year of the temporal constraint (if not in question text)
        
        Returns:
            Parsed structure with temporal info
        """
        import re
        
        # Extract year from question if not provided
        if year is None:
            for pattern_desc, pattern_regex in self.temporal_patterns:
                match = re.search(pattern_regex, question)
                if match:
                    year = int(match.group(1))
                    break
        
        # Convert to present-tense query by removing temporal constraint
        present_query = question
        if year:
            present_query = re.sub(r'\s+(in|during|as of|back in)\s+\d{4}', '', question)
            present_query = re.sub(r'\s+was\s+', ' is ', present_query)
            present_query = re.sub(r'\s+were\s+', ' are ', present_query)
            present_query = re.sub(r'\s+had\s+', ' has ', present_query)
        
        return {
            "original_question": question,
            "present_query": present_query,
            "historical_answer": answer,
            "historical_year": year,
            "temporal_type": self._classify_temporal_type(question, answer)
        }
    
    def _classify_temporal_type(self, question: str, answer: str) -> str:
        """Classify the type of temporal knowledge being tested."""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["president", "prime minister", "chancellor", "leader"]):
            return "POLITICAL_POSITION"
        elif any(word in question_lower for word in ["ceo", "director", "executive", "founder"]):
            return "INSTITUTIONAL_LEADERSHIP"
        elif any(word in question_lower for word in ["population", "number of", "how many"]):
            return "STATISTICAL_FACT"
        elif any(word in question_lower for word in ["capital", "name of", "located"]):
            return "GEOGRAPHIC_FACT"
        else:
            return "GENERAL_TEMPORAL"
    
    def create_retrieval_test(self, 
                            present_query: str,
                            historical_answer: str,
                            historical_year: int,
                            current_answer: str,
                            current_year: int = 2026,
                            add_semantic_richness: bool = True) -> Dict:
        """
        Create a retrieval ranking test case.
        
        Args:
            present_query: Present-tense query ("Who is the President?")
            historical_answer: Past answer ("Bill Clinton")
            historical_year: Year of past answer
            current_answer: Current answer ("Donald Trump")
            current_year: Year of current answer
            add_semantic_richness: Add extra context to stale doc (adversarial)
        
        Returns:
            Test case with query, documents, and expected ranking
        """
        # Create stale document (semantically rich if adversarial)
        if add_semantic_richness:
            stale_doc = {
                "text": f"{historical_answer} served in this role and was instrumental in shaping policy, leading major initiatives, and representing the position with distinction across multiple terms.",
                "acquired": datetime(historical_year, 1, 1),
                "is_current": False
            }
        else:
            stale_doc = {
                "text": f"{historical_answer} held this position.",
                "acquired": datetime(historical_year, 1, 1),
                "is_current": False
            }
        
        # Create current document (concise, natural language - no explicit "current" marker)
        current_doc = {
            "text": f"{current_answer} holds this role.",
            "acquired": datetime(current_year, 1, 1),
            "last_verified": datetime(current_year, 3, 1),
            "is_current": True
        }
        
        return {
            "query": present_query,
            "documents": {
                "stale": stale_doc,
                "current": current_doc
            },
            "expected_winner": "current",
            "semantic_bias": "stale" if add_semantic_richness else "neutral",
            "temporal_type": self._classify_temporal_type(present_query, historical_answer)
        }
    
    def convert_dataset(self, tempquestions_data: List[Dict]) -> List[Dict]:
        """
        Convert full TempQuestions dataset to retrieval benchmarks.
        
        Args:
            tempquestions_data: List of TempQuestions entries with format:
                [
                    {
                        "question": "Who was US President in 1998?",
                        "answer": "Bill Clinton",
                        "year": 1998,
                        "current_answer": "Donald Trump"  # YOU must provide this
                    },
                    ...
                ]
        
        Returns:
            List of retrieval test cases
        """
        retrieval_tests = []
        
        for entry in tempquestions_data:
            parsed = self.parse_tempquestion(
                entry["question"],
                entry["answer"],
                entry.get("year")
            )
            
            # Only convert if we have current answer
            if "current_answer" in entry:
                test = self.create_retrieval_test(
                    present_query=parsed["present_query"],
                    historical_answer=parsed["historical_answer"],
                    historical_year=parsed["historical_year"],
                    current_answer=entry["current_answer"],
                    add_semantic_richness=entry.get("add_richness", True)
                )
                
                retrieval_tests.append({
                    **test,
                    "original_question": parsed["original_question"],
                    "metadata": {
                        "source": "TempQuestions",
                        "historical_year": parsed["historical_year"]
                    }
                })
        
        return retrieval_tests


def example_conversion():
    """Demonstrate conversion on sample TempQuestions-style data."""
    
    converter = TempQuestionsConverter()
    
    # Example TempQuestions entries with current answers added
    sample_data = [
        {
            "question": "Who was the US President in 1998?",
            "answer": "Bill Clinton",
            "year": 1998,
            "current_answer": "Donald Trump"
        },
        {
            "question": "Who was the UK Prime Minister in 2010?",
            "answer": "David Cameron",
            "year": 2010,
            "current_answer": "Keir Starmer"
        },
        {
            "question": "Who was the CEO of Apple in 2005?",
            "answer": "Steve Jobs",
            "year": 2005,
            "current_answer": "Tim Cook"
        },
        {
            "question": "What was the population of Tokyo in 2010?",
            "answer": "13.2 million",
            "year": 2010,
            "current_answer": "14.1 million",
            "add_richness": False  # Population facts are statistical
        }
    ]
    
    retrieval_tests = converter.convert_dataset(sample_data)
    
    print("=" * 80)
    print("TEMPQUESTIONS → RETRIEVAL BENCHMARK CONVERSION")
    print("=" * 80)
    print()
    
    for i, test in enumerate(retrieval_tests, 1):
        print(f"Case {i}: {test['original_question']}")
        print(f"  Present Query: {test['query']}")
        print(f"  Type: {test['temporal_type']}")
        print()
        print(f"  STALE DOC (acquired {test['documents']['stale']['acquired'].year}):")
        print(f"    {test['documents']['stale']['text']}")
        print()
        print(f"  CURRENT DOC (acquired {test['documents']['current']['acquired'].year}):")
        print(f"    {test['documents']['current']['text']}")
        print()
        print(f"  Expected: {test['expected_winner'].upper()} should rank higher")
        print(f"  Semantic bias: {test['semantic_bias']}")
        print()
        print("-" * 80)
        print()
    
    # Export to JSON for testing
    output = {
        "source": "TempQuestions_converted",
        "conversion_date": datetime(2026, 3, 9).isoformat(),
        "test_cases": retrieval_tests
    }
    
    with open("tempquestions_retrieval_benchmark.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"✓ Exported {len(retrieval_tests)} test cases to tempquestions_retrieval_benchmark.json")
    print()
    print("NEXT STEPS:")
    print("1. Load this JSON in Phase 1 or Phase 2")
    print("2. Run each query against both documents")
    print("3. Check if decay correctly ranks current > stale")
    print("4. Measure: rescued cases, regressions, margins")


if __name__ == "__main__":
    example_conversion()
