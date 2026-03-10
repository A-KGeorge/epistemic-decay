# TempQuestions: Benchmark Generation & External Validation

**Temporal Knowledge Retrieval Benchmarks**

This folder contains tools for generating temporal knowledge retrieval benchmarks from verified historical data and the TempQuestions dataset. These benchmarks validate the temporal decay framework against external data sources.

---

## Overview

Three types of benchmarks:

1. **Verified Specific Date (153 cases)** ⭐ Publication-ready
   - Programmatically generated from 58 verified leadership tenures
   - All facts verifiable from public sources (Wikipedia, government records)
   - 18 entities across 5 decades (1970s-2020s)

2. **Manual Specific Date (61 cases)**
   - Hand-crafted adversarial cases with nuanced temporal scenarios
   - Entities: Apple, Microsoft, Amazon, Google, Meta, Tesla, IBM, etc.

3. **TempQuestions Large-Scale (1,740 cases)**
   - Converted from TimeQA temporal QA dataset
   - Regression testing (ensures Phase 2 doesn't break Phase 1)

---

## File Structure

```
TempQuestions/
├── README.md                              # This file
│
├── generate_wikidata_benchmark.py         # Generate 153-case programmatic benchmark ⭐
├── create_specific_date_benchmark.py      # Generate 28-case manual benchmark
├── expand_specific_date_benchmark.py      # Expand to 61-case manual benchmark
│
├── tempquestions_converter.py             # Convert TempQuestions QA to retrieval
├── tempquestions_batch.py                 # Batch processor for large-scale
├── tempquestions_full_scale.py            # End-to-end pipeline ⭐
├── wikidata_lookup.py                     # Wikidata SPARQL queries
├── tempquestions_autolookup.py            # Manual KB lookups
│
└── cache/
    ├── tempquestions_raw_2000.json        # Raw TempQuestions data
    ├── tempquestions_augmented_2000.json  # With current answers
    └── benchmarks/
        ├── verified_specific_date_benchmark.json      # 153 programmatic ⭐
        ├── specific_date_benchmark_large.json         # 61 manual
        └── tempquestions_retrieval_large.json         # 1,740 TempQuestions
```

---

## Quick Start

### 1. Generate Verified Programmatic Benchmark (153 cases) ⭐ Recommended

**Best for publication**: Uses curated verified data, no network dependencies.

```powershell
cd "E:\test\decay\TempQuestions"
..\Phase 1\venv\Scripts\Activate.ps1
python generate_wikidata_benchmark.py
```

**Output**: `cache/benchmarks/verified_specific_date_benchmark.json`

**What it generates:**

- 153 test cases from 58 leadership tenures
- Entities:
  - **Tech CEOs**: Apple, Microsoft, Google, Amazon, Meta, Tesla, IBM, Intel, Oracle, Netflix, Adobe, Salesforce
  - **Political leaders**: US, UK, France, Germany, Canada, Japan
- Coverage: 1970s-2020s (5 decades)
- Difficulty: 42.5% hard (2-5 year gaps), 32% medium, 25.5% easy

**Example test case:**

```json
{
  "query": "Who was the CEO of Microsoft in 2005?",
  "entity": "Microsoft",
  "query_year": 2005,
  "documents": {
    "from_2005": {
      "text": "Steve Ballmer served as CEO of Microsoft. Their tenure lasted from 2000 to 2014...",
      "acquired": "2005-06-15T00:00:00Z",
      "is_correct": true,
      "era": 2005,
      "person": "Steve Ballmer"
    },
    "from_2018": {
      "text": "Satya Nadella served as CEO of Microsoft. Their tenure lasted from 2014 to 2024...",
      "acquired": "2018-06-15T00:00:00Z",
      "is_correct": false,
      "era": 2018,
      "person": "Satya Nadella"
    }
  },
  "expected_winner": "from_2005",
  "difficulty": "medium"
}
```

**Runtime**: ~2 seconds (no network calls)

---

### 2. Generate TempQuestions Benchmark (1,740 cases)

**Best for large-scale validation**: Uses external TimeQA dataset with Wikidata current answers.

```powershell
cd "E:\test\decay\TempQuestions"
..\Phase 1\venv\Scripts\Activate.ps1

# Generate 2000 questions (filters to ~1740 valid cases)
python tempquestions_full_scale.py --count 2000
```

**Output**: `cache/benchmarks/tempquestions_retrieval_large.json`

**What it does:**

1. Fetches TempQuestions from source (~5 min)
2. Looks up current answers via Wikidata SPARQL (~20 min with rate limiting)
3. Converts QA format to retrieval benchmark (~2 min)
4. Filters for quality (removes ambiguous cases)

**Example test case:**

```json
{
  "query": "Who is the President of the United States?",
  "documents": {
    "stale": {
      "text": "[Historical answer for United States President] served as president...",
      "acquired": "1998-05-15T10:00:00Z"
    },
    "current": {
      "text": "Joe Biden is the current President of the United States...",
      "acquired": "2024-01-15T10:00:00Z",
      "last_verified": "2024-01-15T10:00:00Z"
    }
  },
  "expected_winner": "current"
}
```

**Runtime**: ~30 minutes for 2000 questions (Wikidata API rate-limited)

**Options:**

```powershell
# Demo mode (100 questions, ~2 min)
python tempquestions_full_scale.py --demo

# Full mode (1000 questions, ~15 min)
python tempquestions_full_scale.py --full

# Custom count (recommended: 1500-2000)
python tempquestions_full_scale.py --count 1500
```

---

### 3. Generate Manual Benchmark (28 → 61 cases)

**For detailed analysis**: Hand-crafted cases with specific adversarial scenarios.

```powershell
# Generate initial 28 cases
python create_specific_date_benchmark.py

# Expand to 61 cases
python expand_specific_date_benchmark.py
```

**Output**:

- `cache/benchmarks/specific_date_benchmark.json` (28 cases)
- `cache/benchmarks/specific_date_benchmark_large.json` (61 cases)

**Note**: These are already generated and version-controlled. Re-running will recreate from hardcoded data.

---

## Benchmark Comparison

| Benchmark                 | Cases | Generation Time | Network Required | Purpose                        |
| ------------------------- | ----- | --------------- | ---------------- | ------------------------------ |
| **Verified programmatic** | 153   | ~2s             | No               | Publication (verifiable facts) |
| **Manual specific_date**  | 61    | ~1s             | No               | Adversarial testing            |
| **TempQuestions**         | 1,740 | ~30min          | Yes (Wikidata)   | Large-scale regression         |

---

## Evaluation

All benchmarks are evaluated with the same script:

```powershell
cd "..\Phase 2"
..\Phase 1\venv\Scripts\Activate.ps1

# Programmatic (153 cases)
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/verified_specific_date_benchmark.json

# Manual (61 cases) with verbose output
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/specific_date_benchmark_large.json --verbose

# TempQuestions (1,740 cases)
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/tempquestions_retrieval_large.json
```

---

## Results Summary

### Verified Programmatic (153 cases) ⭐

| System      | Accuracy           |
| ----------- | ------------------ |
| Standard    | 74.5% (114/153)    |
| Phase 1     | 74.5% (114/153)    |
| **Phase 2** | **100% (153/153)** |

**Improvement**: +39 cases over Phase 1, 0 regressions

---

### Manual Specific Date (61 cases)

| System      | Accuracy          |
| ----------- | ----------------- |
| Standard    | 55.7% (34/61)     |
| Phase 1     | 45.9% (28/61)     |
| **Phase 2** | **90.2% (55/61)** |

**Improvement**: +27 cases over Phase 1, 0 regressions  
**Failures**: 6 cases (continuity or small-gap scenarios)

---

### TempQuestions (1,740 cases)

| System      | Accuracy                |
| ----------- | ----------------------- |
| Standard    | 92.1% (1,602/1,740)     |
| Phase 1     | 92.1% (1,602/1,740)     |
| **Phase 2** | **92.1% (1,602/1,740)** |

**Improvement**: 0 cases (Phase 2 neutral on non-specific-date queries)  
**Validation**: 0 regressions ✓

---

## Technical Details

### Verified Benchmark Generation

**Data source**: Curated verified leadership tenures in `generate_wikidata_benchmark.py`

```python
VERIFIED_LEADERSHIP_DATA = {
    "Apple": [
        ("Steve Jobs", 1997, 2011, "CEO"),
        ("Tim Cook", 2011, 2024, "CEO"),
    ],
    "Microsoft": [
        ("Bill Gates", 1975, 2000, "CEO"),
        ("Steve Ballmer", 2000, 2014, "CEO"),
        ("Satya Nadella", 2014, 2024, "CEO"),
    ],
    # ... 18 entities total
}
```

**Test case generation:**

1. For each tenure, sample 1-3 years (start, middle, end)
2. Create documents from that year + predecessor/successor tenures
3. Add temporal distractors (especially close years for hard cases)
4. Ensure ≥2 documents per case

---

### TempQuestions Pipeline

**Step 1**: Fetch TempQuestions

```powershell
python tempquestions_batch.py --count 2000
```

Output: `cache/tempquestions_raw_2000.json`

**Step 2**: Augment with current answers

```powershell
python wikidata_lookup.py
```

Output: `cache/tempquestions_augmented_2000.json`

**Step 3**: Convert to retrieval format

```powershell
python tempquestions_converter.py
```

Output: `cache/benchmarks/tempquestions_retrieval_large.json`

**Or run all at once:**

```powershell
python tempquestions_full_scale.py --count 2000
```

---

## Wikidata SPARQL Queries

**Module**: `wikidata_lookup.py`

Example query for current President:

```sparql
SELECT ?person ?personLabel WHERE {
  wd:Q30 p:P35 ?statement.           # United States has head of state
  ?statement ps:P35 ?person.         # Person is head of state
  ?statement pq:P580 ?start.         # Start date
  FILTER NOT EXISTS { ?statement pq:P582 ?end. }  # No end date (current)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

**Rate limiting**: 1 request per second (Wikidata User-Agent policy)

---

## Troubleshooting

### Network timeout during TempQuestions generation

**Solution**: Use smaller count or retry

```powershell
python tempquestions_full_scale.py --count 1000  # Smaller batch
```

### Wikidata returns no results

**Solution**: Check entity exists and has position data

```powershell
# Test single query
python wikidata_lookup.py --entity "Q95"  # Google
```

### Missing benchmark files

**Solution**: Regenerate benchmarks

```powershell
# Verified (fast, no network)
python generate_wikidata_benchmark.py

# TempQuestions (slow, requires network)
python tempquestions_full_scale.py --count 2000
```

---

## See Also

- **Main README**: [../README.md](../README.md)
- **Quick Start**: [../QUICKSTART.md](../QUICKSTART.md)
- **Phase 2 Results**: [../Phase 2/PHASE2_RESULTS_SUMMARY.md](../Phase%202/PHASE2_RESULTS_SUMMARY.md)
- **Phase 2 README**: [../Phase 2/README.md](../Phase%202/README.md)
  python evaluate_phase2.py --large

````

**What Phase 2 tests:**

- Temporal marker detection: "CURRENT President" vs "President in 1998"
- Contamination penalties: Stale facts with "current" should decay faster
- Epistemic qualifiers: "is the President" vs "was the President"

### 4. Evaluate Combined (Phase 1 + Phase 2)

Compares all three approaches side-by-side:

```powershell
python evaluate_combined.py
````

**Output comparison:**

- Standard: No decay (baseline)
- Phase 1: Temporal decay only
- Phase 2: Temporal decay + contamination detection

Shows improvement metrics and rescue rates.

## Key Metrics

Each evaluator reports:

- **Accuracy**: Percentage of test cases where current document ranked higher
- **Rescued cases**: Standard failed, decay succeeded
- **Regressions**: Decay failed, standard succeeded
- **Margin analysis**: Average confidence difference (current - stale)
- **Contamination stats** (Phase 2): Detection rates and effectiveness

## Expected Results (88-case benchmark)

| Method   | Accuracy | Rescued | Notes                   |
| -------- | -------- | ------- | ----------------------- |
| Standard | 22.7%    | -       | Baseline retrieval      |
| Phase 1  | 92.0%    | 61      | +69.3% improvement      |
| Phase 2  | 92.0%+   | 61+     | +contamination handling |

## Category Breakdown

TempQuestions covers three entity types:

1. **Political** (60%): Presidents, Prime Ministers, Governors
2. **Institutional** (25%): CEOs, Chancellors, Directors
3. **Statistical** (15%): Population counts, economic figures

Phase 1 typically achieves:

- Political: 85% accuracy
- Institutional: 100% accuracy
- Statistical: 95.2% accuracy

## Dependencies

**Required:**

- `sentence-transformers` (all-MiniLM-L6-v2)
- `numpy`
- `requests` (Wikidata SPARQL)

**From main project:**

- `Phase 1/decay_functions.py` (for evaluate_phase1.py)
- `Phase 2/decay_functions.py` (for evaluate_phase2.py)
- `Phase 2/compositional_logic.py` (for contamination detection)

## Quick Start: Complete Workflow

**Step 1: Generate questions (choose one):**

```powershell
# Recommended for robust validation (1500 questions, ~22 minutes)
python tempquestions_full_scale.py --count 1500

# Or for extensive validation (2000 questions, ~30 minutes)
python tempquestions_full_scale.py --count 2000
```

**Step 2: Run evaluations:**

```powershell
# Evaluate Phase 1 (temporal decay)
python evaluate_phase1.py

# Evaluate Phase 2 (contamination detection)
python evaluate_phase2.py

# Compare all three approaches
python evaluate_combined.py
```

That's it! The script will:

- Generate synthetic TempQuestions
- Fetch current answers from Wikidata (~1 sec per question)
- Create retrieval benchmarks automatically
- Save results to `cache/benchmarks/tempquestions_retrieval_large.json`

## Limitations

1. **Wikidata coverage**: ~88% success rate on entity lookups
2. **Entity ambiguity**: "President" assumes US unless specified
3. **Language**: English-only queries and documents
4. **Temporal scope**: Focuses on leadership/position changes, not all temporal facts

## Future Extensions

- [ ] Multi-language TempQuestions variants
- [ ] Additional entity types (sports teams, company acquisitions)
- [ ] Temporal reasoning benchmarks (before/after relationships)
- [ ] Combine with other temporal datasets (TimeQA, SituatedQA)

## References

- **TempQuestions**: Original temporal QA benchmark
- **Wikidata**: Knowledge graph for current fact lookup
- **Phase 1**: Temporal decay implementation
- **Phase 2**: Contamination detection implementation
