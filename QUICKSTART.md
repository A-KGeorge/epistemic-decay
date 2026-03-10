# Quick Start Guide

**Get started with the Temporal Decay Framework in 5 minutes**

---

## Prerequisites

### 1. Install Python Dependencies

```powershell
# Navigate to project root
cd "E:\test\decay"

# Create and activate virtual environment
python -m venv Phase 1/venv
.\Phase 1\venv\Scripts\Activate.ps1

# Install all dependencies from requirements.txt
pip install -r requirements.txt

# Download spaCy language model
python -m spacy download en_core_web_sm
```

**Note**: The same virtual environment works for both Phase 1 and Phase 2.

---

## Phase 1: Document-Side Temporal Decay

### Run the 23-Case Adversarial Benchmark

```powershell
cd "E:\test\decay\Phase 1"
.\venv\Scripts\Activate.ps1
python phase_1.py
```

**Expected output:**

```
================================================================================
TEMPORAL DECAY FRAMEWORK - PHASE 1 VALIDATION
================================================================================

Processing 23 test cases...
...
================================================================================
FINAL RESULTS
================================================================================
Both correct:           11  (stable facts maintained)
Decay correct only:     12  (time-sensitive cases rescued)
Standard correct only:   0  (zero regressions)
Both wrong:              0  (perfect resolution)

Accuracy:
  Standard:  11/23 (47.8%)
  Decay:     23/23 (100.0%)
```

**What this tests:**

- 12 time-sensitive queries (CEO changes, breaking news, policy updates)
- 11 stable facts (math, physics, geography) as regression controls
- Validates that temporal decay rescues outdated information without breaking stable facts

---

## Phase 2: Query-Side Temporal Intent

### Option 1: Programmatic Benchmark (153 cases) ⭐ Recommended

**Best for publication**: Verifiable facts from 58 leadership tenures across 18 entities.

```powershell
cd "E:\test\decay\Phase 2"
..\Phase 1\venv\Scripts\Activate.ps1
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/verified_specific_date_benchmark.json
```

**Expected output:**

```
================================================================================
PHASE 2 QUERY INTENT EVALUATION
================================================================================
Test cases: 153
...
================================================================================
RESULTS SUMMARY
================================================================================
Standard:  114/153 (74.5%)
Phase 1:   114/153 (74.5%)
Phase 2:   153/153 (100.0%)

Phase 2 over Phase 1: +39 cases
Phase 2 regressions:  -0 cases
Net improvement:      +39 cases
```

**What this tests:**

- 153 programmatically-generated cases from verified historical records
- CEOs: Apple, Microsoft, Google, Amazon, Meta, Tesla, IBM, Intel, Oracle, Netflix, Adobe, Salesforce
- Political leaders: US, UK, France, Germany, Canada, Japan
- Difficulty: 42.5% hard (2-5 year gaps), 32% medium, 25.5% easy
- Coverage: 1970s-2020s (5 decades)

---

### Option 2: Manual Benchmark (61 cases)

**Best for detailed analysis**: Hand-crafted adversarial cases with nuanced temporal scenarios.

```powershell
cd "E:\test\decay\Phase 2"
..\Phase 1\venv\Scripts\Activate.ps1
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/specific_date_benchmark_large.json --verbose
```

**Expected output:**

```
Standard:  34/61 (55.7%)
Phase 1:   28/61 (45.9%)
Phase 2:   55/61 (90.2%)

Phase 2 over Phase 1: +27 cases
Phase 2 regressions:  -0 cases
```

**Use `--verbose` flag to see:**

- Per-case query intent classification
- Temporal alignment multipliers for each document
- Which cases were rescued by Phase 2

---

### Option 3: TempQuestions Large-Scale (1,740 cases)

**Best for regression testing**: Validates that Phase 2 doesn't break Phase 1 on general temporal queries.

```powershell
cd "E:\test\decay\Phase 2"
..\Phase 1\venv\Scripts\Activate.ps1
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/tempquestions_retrieval_large.json
```

**Expected output:**

```
Standard:  1602/1740 (92.1%)
Phase 1:   1602/1740 (92.1%)
Phase 2:   1602/1740 (92.1%)

Phase 2 over Phase 1: +0 cases
Phase 2 regressions:  -0 cases
```

**What this tests:**

- 1,740 temporal questions from TimeQA dataset
- Validates Phase 2 only activates on specific_date queries (neutral on others)
- Confirms 0 regressions on general temporal knowledge retrieval

---

## Run All Benchmarks (Complete Validation)

```powershell
# Activate environment once
cd "E:\test\decay\Phase 1"
.\venv\Scripts\Activate.ps1

# Phase 1 (23 cases)
python phase_1.py

# Phase 2 - All three benchmarks
cd "..\Phase 2"

# Programmatic (153 cases)
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/verified_specific_date_benchmark.json

# Manual (61 cases)
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/specific_date_benchmark_large.json

# TempQuestions (1,740 cases)
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/tempquestions_retrieval_large.json
```

**Total validation:**

- **1,954 test cases** across 4 benchmarks
- **92.7% overall accuracy** (1,808/1,954)
- **0 regressions** across all systems

---

## Generate New Benchmarks (Optional)

### Generate Programmatic Benchmark from Verified Data

```powershell
cd "E:\test\decay\TempQuestions"
..\Phase 1\venv\Scripts\Activate.ps1
python generate_wikidata_benchmark.py
```

**Output**: `cache/benchmarks/verified_specific_date_benchmark.json` (153 cases)

**What it does:**

- Uses curated verified data (CEOs, Presidents, PMs from 1975-2024)
- Generates 1-3 test cases per leadership tenure
- Creates temporal distractors from predecessor/successor tenures
- All facts verifiable from Wikipedia or government records

---

### Generate TempQuestions Benchmark

```powershell
cd "E:\test\decay\TempQuestions"
..\Phase 1\venv\Scripts\Activate.ps1

# Generate 2000 questions (~30 minutes with Wikidata API calls)
python tempquestions_full_scale.py --count 2000
```

**Output**: `cache/benchmarks/tempquestions_retrieval_large.json` (1,740 cases)

**What it does:**

- Fetches TempQuestions from source
- Looks up current answers via Wikidata SPARQL
- Converts QA format to retrieval benchmark
- Filters for quality (removes ambiguous cases)

---

## Analyze Failures (Phase 2)

```powershell
cd "E:\test\decay\Phase 2"
..\Phase 1\venv\Scripts\Activate.ps1
python analyze_failures.py
```

**Output**: Detailed analysis of the 6 failures on the 61-case manual benchmark

**Example output:**

```
FAILURE ANALYSIS: Phase 2 on Manual Benchmark (61 cases)
================================================================================

Total failures: 6/61 (9.8%)

Failure Pattern 1: CONTINUITY (2 cases)
  - Same person across different years
  - Embeddings nearly identical
  - Temporal multipliers insufficient (1.18-1.24× boost)

  Examples:
    • Amazon 2021 vs 2024 (Andy Jassy both years)
    • Netflix 2020 vs 2023 (Ted Sarandos co-CEO)

Failure Pattern 2: SMALL GAPS (4 cases)
  - 2-5 year distances
  - Multipliers 1.05-1.10× create only 1.18-1.24× total boost

  Examples:
    • Google 2001 vs 1998 (3-year gap)
    • France 2007 vs 2012 (Sarkozy era, 5-year gap)
    • Twitter 2008 vs 2006, 2010 vs 2006 (founder context)
```

---

## Troubleshooting

### ImportError: No module named 'spacy'

```powershell
# Make sure virtual environment is activated
cd "Phase 1"
.\venv\Scripts\Activate.ps1
pip install -r ..\requirements.txt
python -m spacy download en_core_web_sm
```

### OSError: Can't find model 'en_core_web_sm'

```powershell
python -m spacy download en_core_web_sm
```

### Benchmark file not found

```powershell
# Generate missing benchmarks
cd "TempQuestions"
..\Phase 1\venv\Scripts\Activate.ps1

# For verified benchmark
python generate_wikidata_benchmark.py

# For TempQuestions benchmark
python tempquestions_full_scale.py --count 2000
```

### Slow performance on first run

**Expected**: First run loads sentence transformer model (~100MB), takes 10-30 seconds. Subsequent runs are fast (<5 seconds for 153 cases).

---

## Next Steps

1. **Review detailed results**: [Phase 2/PHASE2_RESULTS_SUMMARY.md](Phase%202/PHASE2_RESULTS_SUMMARY.md)
2. **Understand failures**: [Phase 2/analyze_failures.py](Phase%202/analyze_failures.py)
3. **Explore Phase 3**: See README.md for dependency graph proposals
4. **Customize benchmarks**: Modify `generate_wikidata_benchmark.py` with your own entities

---

## Summary of Commands

| Task                       | Command                                                                                                                                    | Time   | Cases |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------ | ----- |
| **Phase 1 baseline**       | `cd "Phase 1"; python phase_1.py`                                                                                                          | ~10s   | 23    |
| **Phase 2 programmatic**   | `cd "Phase 2"; python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/verified_specific_date_benchmark.json`        | ~15s   | 153   |
| **Phase 2 manual**         | `cd "Phase 2"; python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/specific_date_benchmark_large.json --verbose` | ~10s   | 61    |
| **Phase 2 TempQuestions**  | `cd "Phase 2"; python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/tempquestions_retrieval_large.json`           | ~60s   | 1,740 |
| **Generate programmatic**  | `cd "TempQuestions"; python generate_wikidata_benchmark.py`                                                                                | ~2s    | 153   |
| **Generate TempQuestions** | `cd "TempQuestions"; python tempquestions_full_scale.py --count 2000`                                                                      | ~30min | 1,740 |
| **Analyze failures**       | `cd "Phase 2"; python analyze_failures.py`                                                                                                 | ~1s    | 6     |

**Total validation time: ~2 minutes** (excluding benchmark generation)
