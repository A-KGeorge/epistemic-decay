import argparse
import json
import sys
import re
from pathlib import Path

# Ensure the script can find the base converter
sys.path.insert(0, str(Path(__file__).parent))
from tempquestions_converter import TempQuestionsConverter

class ComplexTempQATruthConverter(TempQuestionsConverter):
    """
    Advanced Converter that sets the expected_winner based on Query Intent.
    Allows for 'Rescue' testing where Recency/Phase 1 are expected to FAIL.
    """
    
    def convert_dataset_to_truth(self, raw_data, current_fallback="Unknown"):
        retrieval_tests = []
        for entry in raw_data:
            if not isinstance(entry, dict): continue
            question = entry.get("question")
            answer = entry.get("answer")
            if not question or not answer: continue

            # 1. Parse using base class to detect if it's a historical question
            parsed = self.parse_tempquestion(question, answer)
            is_historical = parsed["historical_year"] is not None
            
            # 2. Extract years for the DED framework logic
            metadata = entry.get("metadata", {})
            time_span = metadata.get("time_span", [])
            try:
                if time_span and isinstance(time_span, list):
                    hist_year = int(str(time_span[0]).split("-")[0])
                else:
                    hist_year = parsed["historical_year"] or 2000
            except (ValueError, IndexError, AttributeError):
                hist_year = 2000

            # 3. Create the test case
            test = self.create_retrieval_test(
                present_query=parsed["present_query"], # Keep query clean
                historical_answer=answer,
                historical_year=hist_year,
                current_answer=entry.get("current_answer", current_fallback),
                add_semantic_richness=True
            )
            
            # 4. LOGICAL FLIP: If the question is historical, the 'stale' doc is the TRUTH
            if is_historical:
                test["expected_winner"] = "stale"
            else:
                test["expected_winner"] = "current"

            # 5. Add original_question for --use-original evaluations
            test["original_question"] = question
            
            test["metadata"] = {
                "source": "ComplexTempQA_truth",
                "complexity_type": entry.get("type", "UNKNOWN"),
                "is_historical_intent": is_historical
            }
            retrieval_tests.append(test)
        return retrieval_tests

def stream_json_objects(text):
    decoder = json.JSONDecoder()
    pos = 0
    text = text.strip()
    while pos < len(text):
        try:
            obj, pos = decoder.raw_decode(text, pos)
            yield obj
            while pos < len(text) and text[pos] in " \n\r\t,": pos += 1
        except json.JSONDecodeError:
            next_start = text.find('{', pos + 1)
            if next_start == -1: break
            pos = next_start

def main():
    parser = argparse.ArgumentParser(description="Generate Truth-Aware ComplexTempQA Benchmark")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--current-fallback", default="Latest Verified Fact")
    
    args = parser.parse_args()
    converter = ComplexTempQATruthConverter()
    
    with open(args.input, 'r', encoding='utf-8') as f:
        content = f.read()
            
    raw_data = list(stream_json_objects(content))
    converted_data = converter.convert_dataset_to_truth(raw_data, args.current_fallback)

    output_payload = {"source": "ComplexTempQA_truth", "test_cases": converted_data}
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_payload, f, indent=2, default=str)
    
    print(f"✓ Saved {len(converted_data)} truth-aware cases to {args.output}")

if __name__ == "__main__":
    main()