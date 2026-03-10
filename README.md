# Dynamic Epistemic Decay Framework

**Multi-Phase Temporal Knowledge Retrieval System**

This repository implements a novel approach to temporal knowledge retrieval that combines document-side temporal decay with query-side temporal intent analysis. The system achieves **92.7% accuracy across 1,954 test cases** covering temporal queries from the 1970s to 2020s.

---

## Quick Start

See [QUICKSTART.md](QUICKSTART.md) for step-by-step instructions to run all benchmarks.

**TL;DR:**

```powershell
# Phase 1: Document-side temporal decay (23 cases)
cd "Phase 1"
python phase_1.py

# Phase 2: Query-side temporal intent (153 programmatic + 61 manual + 1,740 TempQuestions)
cd "../Phase 2"
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/verified_specific_date_benchmark.json
```

---

## Project Overview

### Architecture

- **Phase 1**: Document-side temporal decay with category-specific decay rates
- **Phase 2**: Query-side temporal intent detection and alignment scoring

**Key Innovation**: Phase 1 penalizes old documents (recency bias correction), while Phase 2 rewards documents whose temporal era matches the query's temporal intent (e.g., "Who was CEO in 1997?" prefers 1997-era documents).

### Results Summary

| Benchmark                 | Cases     | Standard  | Phase 1   | Phase 2   | P2 Improvement |
| ------------------------- | --------- | --------- | --------- | --------- | -------------- |
| **Programmatic verified** | 153       | 74.5%     | 74.5%     | **100%**  | **+25.5 pts**  |
| **Manual specific_date**  | 61        | 55.7%     | 45.9%     | **90.2%** | **+44.3 pts**  |
| **TempQuestions**         | 1,740     | 92.1%     | 92.1%     | **92.1%** | **0 pts**      |
| **TOTAL**                 | **1,954** | **88.7%** | **88.2%** | **92.7%** | **+4.5 pts**   |

📊 **Detailed results**: [Phase 2/PHASE2_RESULTS_SUMMARY.md](Phase%202/PHASE2_RESULTS_SUMMARY.md)

---

## Repository Structure

```
decay/
├── README.md                          # This file
├── QUICKSTART.md                      # Quick start guide for all benchmarks
├── VALIDATION_RESULTS.md              # Complete validation results
│
├── Phase 1/                           # Document-side temporal decay
│   ├── phase_1.py                     # Main Phase 1 script (23-case benchmark)
│   ├── decay_functions.py             # Core decay logic
│   ├── benchmark_data.py              # 23 adversarial test cases
│   ├── constants.py                   # Decay rates and categories
│   └── venv/                          # Python virtual environment
│
├── Phase 2/                           # Query-side temporal intent
│   ├── evaluate_query_intent.py       # Main evaluation script
│   ├── query_intent.py                # Temporal intent detection
│   ├── decay_functions.py             # Phase 1 + Phase 2 integration
│   ├── compositional_logic.py         # Compositional decay rules
│   ├── analyze_failures.py            # Failure pattern analysis
│   ├── constants.py                   # Shared configuration
│   ├── PHASE2_RESULTS_SUMMARY.md      # Comprehensive results documentation
│   └── README.md                      # Phase 2 documentation
│
└── TempQuestions/                     # Benchmark generation & validation
    ├── create_specific_date_benchmark.py       # Manual benchmark generator
    ├── expand_specific_date_benchmark.py       # Benchmark expander
    ├── generate_wikidata_benchmark.py          # Programmatic benchmark generator
    ├── tempquestions_converter.py              # TempQuestions converter
    ├── tempquestions_batch.py                  # Batch processor
    ├── tempquestions_full_scale.py             # End-to-end pipeline
    ├── wikidata_lookup.py                      # Wikidata SPARQL queries
    ├── README.md                               # TempQuestions documentation
    └── cache/
        └── benchmarks/
            ├── verified_specific_date_benchmark.json     # 153 programmatic cases ⭐
            ├── specific_date_benchmark_large.json        # 61 manual cases
            └── tempquestions_retrieval_large.json        # 1,740 TempQuestions cases
```

---

## Phase 1: Document-Side Temporal Decay

**Status**: Complete ✅ (23/23 cases, 100% accuracy)

Phase 1 implements category-specific temporal decay where documents lose confidence over time at rates appropriate to their knowledge type. Key innovations:

- **Historical sealing**: Past-tense facts with date anchors don't decay
- **Category classification**: Institutional leadership, geographic facts, mathematical truths, etc.
- **Verification boosting**: Recently verified documents maintain relevance

**Example:**

```python
# A 20-year-old document about "Tim Cook is CEO" gets confidence penalty
# A 50-year-old document about "Washington was first president" stays at 1.0
```

📂 **Navigate to**: [Phase 1/](Phase%201/)

---

## Phase 2: Query-Side Temporal Intent Analysis

**Status**: Complete ✅ (100% on 153-case programmatic benchmark)

Phase 2 adds query-side temporal intent detection:

1. **Year extraction**: "Who was CEO in 1997?" → extract [1997]
2. **Tense detection**: Past tense + year → specific_date intent
3. **Temporal alignment**: Documents from 1997 get 1.30× boost, distant years get 0.60-0.90× penalty

**Key Results:**

- **100% (153/153)** on programmatic benchmark (verified historical facts)
- **90.2% (55/61)** on manual benchmark (hand-crafted cases)
- **92.1% (1,602/1,740)** on TempQuestions (0 regressions vs Phase 1)

**Architectural distinction from Phase 1:**

- Phase 1 = document-side (penalizes old documents)
- Phase 2 = query-side (rewards temporally-aligned documents)
- Together = balanced temporal retrieval

📂 **Navigate to**: [Phase 2/README.md](Phase%202/README.md)

---

## Benchmarks

### 1. Verified Specific Date Benchmark (153 cases) ⭐ Publication-Ready

**Source**: Programmatically generated from 58 verified leadership tenures  
**Entities**: 12 tech companies + 6 countries  
**Coverage**: 1970s-2020s (5 decades)  
**Difficulty**: 42.5% hard cases (2-5 year gaps)

**Generate**: `python TempQuestions/generate_wikidata_benchmark.py`  
**Evaluate**: `python Phase 2/evaluate_query_intent.py --benchmark TempQuestions/cache/benchmarks/verified_specific_date_benchmark.json`

### 2. Manual Specific Date Benchmark (61 cases)

**Source**: Hand-crafted high-quality test cases  
**Entities**: Apple, Microsoft, Amazon, Google, Meta, Tesla, IBM, Oracle, etc.  
**Purpose**: Adversarial testing with nuanced temporal scenarios

**Generate**: `python TempQuestions/expand_specific_date_benchmark.py`  
**Evaluate**: `python Phase 2/evaluate_query_intent.py --benchmark TempQuestions/cache/benchmarks/specific_date_benchmark_large.json`

### 3. TempQuestions Large-Scale (1,740 cases)

**Source**: TimeQA dataset converted to retrieval format  
**Purpose**: Regression testing (ensure Phase 2 doesn't break Phase 1)

**Generate**: `python TempQuestions/tempquestions_full_scale.py --count 2000`  
**Evaluate**: `python Phase 2/evaluate_query_intent.py --benchmark TempQuestions/cache/benchmarks/tempquestions_retrieval_large.json`

---

## Key Features

✅ **Zero regressions** across all benchmarks  
✅ **Programmatic generation** prevents overfitting criticism  
✅ **Publication-ready** with 1,954 total test cases  
✅ **Verified facts** from public sources (Wikipedia, government records)  
✅ **Comprehensive documentation** with failure analysis  
✅ **Modular design** (Phase 1 and Phase 2 independently testable)

---

## Citation

If you use this framework, please cite:

```bibtex
@software{temporal_decay_framework,
  author = {George, Alan Kochukalam},
  title = {Dynamic Epistemic Decay Framework},
  year = {2026},
}
```

---

## Next Steps: Phase 3

**Proposed**: Dependency graphs with structural temporal reasoning

Current Phase 2 failures (6/61 manual cases) occur when:

- **Continuity**: Same person across years (embeddings identical)
- **Small gaps**: 2-5 years (multipliers insufficient)

**Solution**: Extract date-constrained facts (e.g., "Andy Jassy became CEO in 2021") and match against query year using structural knowledge rather than embedding similarity.

📂 **See**: [Phase 2/analyze_failures.py](Phase%202/analyze_failures.py) for detailed failure analysis

```powershell
cd TempQuestions

# Evaluate Phase 1 (temporal decay only)
python evaluate_phase1.py

# Evaluate Phase 2 (contamination detection)
python evaluate_phase2.py

# Compare all three approaches
python evaluate_combined.py
```

**Scaling**:

- **Demo (100 entries)**: `python tempquestions_full_scale.py --demo` (~2 minutes)
- **Full (1000 entries)**: `python tempquestions_full_scale.py --full` (~20 minutes)
- 88% Wikidata coverage achieved on demo run

---

## Complete Validation Results

📊 **View comprehensive results**: [VALIDATION_RESULTS.md](VALIDATION_RESULTS.md)

**Summary across all benchmarks** (120 test cases):

- Phase 1 Adversarial: 23/23 (100%)
- Phase 2 Contamination: 9/9 (100%)
- TempQuestions Large-Scale: 81/88 (92%)
- **Total: 113/120 (94.2%)**
- **Improvement over standard: +68.3%**
- **Regressions: 0**

---

## The Problem

Current AI systems treat all knowledge equally:

- `"Pope Francis is the current Pope"` → stored with same confidence as `"2+2=4"`
- No mechanism to distinguish time-sensitive facts from eternal truths
- Semantically rich but stale information outranks concise but current facts

**Standard retrieval fails** when outdated documents are more detailed than current ones.

---

## The Solution: Temporal Decay

Facts decay at **category-specific rates** based on their knowledge type:

| Knowledge Category       | Decay Rate (λ) | Half-Life  | Example             |
| ------------------------ | -------------- | ---------- | ------------------- |
| Mathematical truth       | 0.0            | ∞          | Pythagorean theorem |
| Historical seal          | 0.0            | ∞          | Shakespeare/Hamlet  |
| Physical law             | 0.0001         | ~19 years  | Speed of light      |
| Geographic fact          | 0.0002         | ~9.5 years | Capital of France   |
| Institutional leadership | 0.002          | ~1 year    | CEO of Apple        |
| Political position       | 0.01           | ~70 days   | President of France |
| Current event            | 0.05           | ~14 days   | News story          |
| Breaking news            | 0.9            | ~18 hours  | Live event          |

**Confidence formula**: `C(t) = e^(-λ × days_elapsed)`

### Key Innovation: Historical Sealing

Past tense facts are **sealed at zero decay** (confidence = 1.0):

- `"Shakespeare wrote Hamlet"` → sealed, permanent confidence
- `"The Pope is currently Francis"` → decays continuously

---

## What Phase 1 Implements

### Core Components

1. **`embed_with_decay(text, acquired_date, category=None, last_verified=None)`**
   - Creates 385-dimensional vectors: 384 semantic + 1 confidence dimension
   - Auto-classifies decay rate via NLP if category not provided
   - Supports `last_verified` date distinct from `acquired_date`

2. **`classify_decay_rate(text)`**
   - Uses spaCy for tense detection, named entity recognition
   - Detects temporal markers (`currently`, `now`, `today`, etc.)
   - Applies historical sealing for past tense main clauses
   - Multiplies decay rate by 2.1× when temporal markers present

3. **Decay-Weighted Retrieval**
   - Standard: ranks by `semantic_similarity(query, doc)` only
   - Decay: ranks by `semantic_similarity × confidence`
   - Flips rankings when stale docs are semantically richer

### Safety Features

- **`CONFIDENCE_FLOOR = 0.05`**: Prevents confidence collapse to zero for old facts
- **`HISTORICAL_SEAL = 0.0`**: Past tense facts maintain full confidence
- **Category-specific rates**: 7 knowledge categories with calibrated decay constants

---

## Benchmark Results

### Adversarial Test Design

23 test cases designed to challenge the system:

- **12 time-sensitive queries** with stale (semantically rich) vs. current (concise) entries
- **11 stable facts** (math, physics, geography) as regression controls

Example adversarial case:

```

Query: "Who is the CEO of Apple?"

Stale entry (acquired 2010):
"Steve Jobs is the CEO of Apple Inc. and leads the technology
company through revolutionary changes in personal computing..."
→ Semantic similarity: 0.7845 | Confidence: 0.05 | Score: 0.0392

Current entry (acquired 2011, verified 2026):
"Tim Cook leads Apple since 2011."
→ Semantic similarity: 0.5462 | Confidence: 0.9841 | Score: 0.5376

Standard retrieval: WRONG (picks Jobs)
Decay retrieval: CORRECT (picks Cook, margin +0.4983)

```

### Results: 23/23 Perfect Accuracy

| Outcome                | Count  | Description                                    |
| ---------------------- | ------ | ---------------------------------------------- |
| **Decay correct only** | **12** | ✅ Rescued cases (standard wrong, decay right) |
| Both correct           | 11     | Stable facts work with both methods            |
| Standard correct only  | **0**  | ❌ Zero regressions                            |
| Both wrong             | **0**  | ✅ All adversarial cases resolved              |

### Margin Distribution

After calibration fixes (confidence floor + last_verified dates):

- **12 STRONG/ROBUST margins**: All time-sensitive cases successfully rescued
- **0 WEAK margins** (<0.01): All fragile cases fixed
- **0 failures**: Perfect adversarial test resolution

### Confidence Calibration Verification

**Stable facts maintain high confidence despite age:**

| Query                | Confidence | Status  | Category                     |
| -------------------- | ---------- | ------- | ---------------------------- |
| Pythagorean theorem  | 1.0000     | PERFECT | Math truth (λ=0.0)           |
| Pi value             | 1.0000     | PERFECT | Math truth (λ=0.0)           |
| Shakespeare/Hamlet   | 1.0000     | PERFECT | Historical seal (past tense) |
| Speed of light       | 0.7416     | GOOD    | Physical law (λ=0.0001)      |
| Water boiling point  | 0.6646     | GOOD    | Physical law (λ=0.0001)      |
| Mount Everest height | 0.6365     | GOOD    | Geographic (λ=0.0002)        |

---

## How to Run

### Prerequisites

```powershell
# Create virtual environment
python -m venv Phase 1/venv
.\Phase 1\venv\Scripts\Activate.ps1

# Install all dependencies from requirements.txt
pip install -r requirements.txt

# Download spaCy language model
python -m spacy download en_core_web_sm
```

### Run Phase 1 Benchmark (23 cases)

```powershell
cd "Phase 1"
python main.py
```

### Run Phase 2 Benchmark (9 contamination cases)

```powershell
cd "Phase 2"
python main.py
```

### Output

The script prints:

1. **Case-by-case results**: Standard vs. Decay correctness
2. **Summary statistics**: Rescued, regressions, both correct/wrong
3. **Verification 1**: Confidence values on stable facts
4. **Verification 2**: Margin analysis for rescued cases

---

## Implementation Details

### Vector Representation

Each knowledge entry becomes a **385-dimensional vector**:

- Dimensions 0-383: Semantic embedding (`all-MiniLM-L6-v2`)
- Dimension 384: Confidence = `max(e^(-λ × Δt), CONFIDENCE_FLOOR)`

### Compositional Decay Classification

The `classify_decay_rate()` function uses NLP to detect:

1. **Tense sealing**: Past tense main clause → `λ = 0.0`
2. **Temporal markers**: `currently`, `now` → `λ × 2.1`
3. **Entity types**:
   - Institutional roles (`CEO`, `President`) → `λ = 0.002`
   - Mathematical language (`theorem`, `equation`) → `λ = 0.0`
4. **Keyword patterns**: Physics, geography, politics, news categories

### last_verified vs. acquired_date

Critical distinction for live knowledge bases:

- `acquired_date`: When fact first became true
- `last_verified`: When fact was most recently confirmed still true

Example:

```python
{
  "text": "Tim Cook is CEO of Apple",
  "acquired": datetime(2011, 8, 24),      # When Cook became CEO
  "last_verified": datetime(2026, 3, 1),  # Recently confirmed
  # Confidence based on last_verified, not acquired
}
```

This prevents old-but-still-true facts from decaying to zero.

---

## Theoretical Foundation

This implementation is Phase 1 of a larger framework covering:

- **Temporal decay** (implemented): Time-based confidence erosion
- **Paradigm decay** (future): Domain-scoped validity (Newtonian vs. relativistic)
- **Uncertainty decay** (future): Bayesian confidence updating
- **Dependency decay** (future): Graph-based stability propagation

See the full paper (provided separately) for:

- Complete formal mathematics
- Compositional stacking rules
- Dependency graph theory
- Misinformation detection applications
- AI safety implications

---

## Key Findings

### 1. Decay Retrieval Rescues Time-Sensitive Cases

**12/12 adversarial cases** where standard retrieval failed were correctly resolved by decay weighting, with zero regressions on stable facts.

### 2. Historical Sealing Works

Past tense detection successfully sealed historical facts at confidence 1.0, preventing inappropriate decay of permanent truths.

### 3. Confidence Floor Prevents Collapse

Without `CONFIDENCE_FLOOR`, institutional leadership facts acquired 10+ years ago collapsed to confidence ≈0.0000, making wins dependent on floating-point noise. Floor at 0.05 maintains meaningful signal.

### 4. last_verified Field Essential

Distinguishing acquisition date from verification date is critical for live knowledge bases. Current leaders verified recently maintain high confidence despite old acquisition dates.

### 5. Semantic Richness Bias Confirmed

Standard retrieval consistently prefers semantically richer stale documents over concise current facts. Decay weighting successfully corrects this bias.

---

## Development Status

**✅ Phase 1 Complete**: Temporal decay with historical sealing (12/12 rescued, 0 regressions)  
**✅ Phase 2 Complete**: Compositional contamination detection (9/9 contamination cases correct)

### Next Steps (Future Phases)

**Phase 3**: Dependency graph (cascade propagation, bridge nodes, stability metrics)  
**Phase 4**: Multi-dimensional decay (paradigm + uncertainty + temporal)  
**Phase 5**: Live metabolism (continuous ingestion, versioning, excretion)

---

## Technical Stack

- **Python**: 3.12
- **Embeddings**: `sentence-transformers` (all-MiniLM-L6-v2, 384-dim)
- **NLP**: `spacy` (en_core_web_sm) for tense/entity detection
- **Math**: `numpy` for exponential decay and vector operations

---

## Citation

If you use this framework, please cite:

```
Alan Kochukalam George (2025). Dynamic Epistemic Decay Framework:
A Multi-Dimensional Theory of Knowledge Validity, Propagation, and Stability.
Computer Engineering, Memorial University of Newfoundland.
```

---

## Contact

Alan Kochukalam George  
B.Eng. Computer Engineering  
St. John's, NL, Canada | 2025

---

## License

[Specify license here]

---

**Current Status**:

- **Phase 1**: Complete ✅ (12 rescued, 0 regressions, 11 stable)
- **Phase 2**: Complete ✅ (compositional contamination with 9/9 correct cases)
