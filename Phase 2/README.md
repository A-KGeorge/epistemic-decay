# Phase 2: Query-Side Temporal Intent Analysis

**Temporal Intent Detection + Document Temporal Alignment**

Phase 2 adds query-side temporal intent detection to complement Phase 1's document-side temporal decay. The system detects when queries ask about specific years and applies temporal alignment scoring to prefer documents from the queried era.

---

## Core Principle

**Queries have temporal intent.** When a query asks about a specific year, documents from that year should be preferred over documents from other years, even if they contain similar information.

Example:

- Query: `"Who was the CEO of Apple in 1997?"`
- Phase 1 alone: Prefers recent 2024 document (recency bias)
- **Phase 2**: Detects year [1997], boosts 1997-era docs by 1.30×, penalizes 2024 docs by 0.60×
- Result: Correctly retrieves "Steve Jobs" (1997) instead of "Tim Cook" (2024)

---

## Architecture: Phase 1 vs Phase 2

| Aspect               | Phase 1                          | Phase 2                               |
| -------------------- | -------------------------------- | ------------------------------------- |
| **Scope**            | Document-side                    | Query-side                            |
| **Mechanism**        | Temporal decay (recency penalty) | Temporal alignment (year-match bonus) |
| **Activation**       | All queries                      | Only specific_date queries            |
| **Multiplier range** | 0.85-1.0× (decay)                | 0.60-1.30× (alignment)                |
| **Temporal signals** | Document acquisition date        | Query year constraints                |
| **Purpose**          | Prevent recency bias             | Enable historical precision           |

**Together**: Phase 1 prevents overfitting to recent data, Phase 2 enables historical queries.

---

## What Phase 2 Implements

### 1. Query Intent Detection

**Module: `query_intent.py`**

**Function: `classify_temporal_intent(query)`**

Detects temporal intent from queries:

```python
# Year extraction
"Who was CEO in 1997?" → years=[1997]

# Tense detection (spaCy)
"Who became President" → tense=past (even if verb form is present)
"Who is the current CEO" → tense=present

# Temporal preference classification
past tense + years → specific_date (activate alignment)
present tense → current (neutral 1.0×)
past tense, no years → historical (neutral 1.0×)
no markers → agnostic (neutral 1.0×)
```

**Output:**

```python
{
  "tense": "past",
  "years": [1997],
  "preference": "specific_date",
  "markers": []
}
```

---

### 2. Temporal Alignment Scoring

**Module: `query_intent.py`**

**Function: `compute_temporal_alignment(query_intent, doc_acquisition_date, doc_text)`**

Year-distance scaled multipliers:

```python
if doc_year in query_years:
    multiplier = 1.30  # Perfect match
elif min_gap == 1:
    multiplier = 1.20  # 1 year off
elif min_gap <= 3:
    multiplier = 1.10  # 2-3 years off
elif min_gap <= 5:
    multiplier = 1.05  # 4-5 years off
elif min_gap <= 10:
    # Linear decay from 1.0 to 0.90
    multiplier = 1.0 - (min_gap - 6) * 0.025
else:
    # Exponential penalty for distant years
    # 20 years = 0.70×, 27 years = 0.63×
    multiplier = max(0.60, 0.90 * (0.95 ** (min_gap - 10)))
```

**Application:**

- `specific_date` queries: Apply multiplier
- All other queries: 1.0× (neutral, no modification)

---

### 3. Integration with Phase 1

**Module: `decay_functions.py`**

Phase 2 **extends** Phase 1 by:

1. **Query encoding**: `encode_query_with_intent(query)` returns query vector + intent metadata
2. **Scoring**: `score_with_temporal_alignment()` applies both document decay AND temporal alignment
3. **Backward compatibility**: Phase 1 logic unchanged (used for non-specific-date queries)

**Pipeline:**

```
Query → Intent Detection → Query Vector (384d + confidence)
                              ↓
Document → Temporal Decay → Document Vector (384d + confidence)
                              ↓
Similarity Score → Temporal Alignment Multiplier → Final Score
```

---

## Results

### Programmatic Verified Benchmark (153 cases) ⭐

**Publication-ready**: Generated from 58 verified leadership tenures

| System      | Accuracy           | vs Phase 1    |
| ----------- | ------------------ | ------------- |
| Standard    | 74.5% (114/153)    | -             |
| Phase 1     | 74.5% (114/153)    | -             |
| **Phase 2** | **100% (153/153)** | **+25.5 pts** |

**Coverage:**

- 18 entities (12 tech companies + 6 countries)
- 5 decades (1970s-2020s)
- 42.5% hard cases (2-5 year gaps)

---

### Manual Specific Date Benchmark (61 cases)

**Hand-crafted adversarial cases**

| System      | Accuracy          | vs Phase 1    |
| ----------- | ----------------- | ------------- |
| Standard    | 55.7% (34/61)     | -             |
| Phase 1     | 45.9% (28/61)     | -9.8 pts      |
| **Phase 2** | **90.2% (55/61)** | **+44.3 pts** |

**Failures:** 6/61 cases due to continuity (same person) or small gaps (2-5 years)

---

### TempQuestions Large-Scale (1,740 cases)

**Regression testing**

| System      | Accuracy                | vs Phase 1             |
| ----------- | ----------------------- | ---------------------- |
| Standard    | 92.1% (1,602/1,740)     | -                      |
| Phase 1     | 92.1% (1,602/1,740)     | -                      |
| **Phase 2** | **92.1% (1,602/1,740)** | **0 pts (no regress)** |

**Key:** Phase 2 only activates on specific_date queries (0 in TempQuestions)

---

## File Structure

```
Phase 2/
├── evaluate_query_intent.py       # Main evaluation script ⭐
├── query_intent.py                 # Temporal intent detection
├── decay_functions.py              # Phase 1 + Phase 2 integration
├── compositional_logic.py          # Compositional decay (Phase 1 feature)
├── analyze_failures.py             # Failure pattern analysis
├── constants.py                    # Shared configuration
├── PHASE2_RESULTS_SUMMARY.md       # Comprehensive results ⭐
└── README.md                       # This file
```

---

## Quick Start

### Prerequisites

```powershell
# Use Phase 1's virtual environment
cd "..\Phase 1"
.\venv\Scripts\Activate.ps1

# Install dependencies (if not already done)
pip install -r ..\requirements.txt
python -m spacy download en_core_web_sm
```

---

### Run Programmatic Benchmark (153 cases) ⭐ Recommended

```powershell
cd "..\Phase 2"
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/verified_specific_date_benchmark.json
```

**Expected output:**

```
Standard:  114/153 (74.5%)
Phase 1:   114/153 (74.5%)
Phase 2:   153/153 (100.0%)

Phase 2 over Phase 1: +39 cases
Phase 2 regressions:  -0 cases
Net improvement:      +39 cases
```

---

### Run Manual Benchmark (61 cases) with Verbose Output

```powershell
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/specific_date_benchmark_large.json --verbose
```

**Verbose output shows:**

- Query intent classification (tense, years, preference)
- Temporal alignment multipliers for each document
- Which cases were rescued by Phase 2

---

### Run TempQuestions (1,740 cases) - Regression Test

```powershell
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/tempquestions_retrieval_large.json
```

**Validates:** Phase 2 maintains Phase 1 performance (0 regressions)

---

### Analyze Failures (6 cases on manual benchmark)

```powershell
python analyze_failures.py
```

**Output:**

- Failure Pattern 1: CONTINUITY (2 cases) - same person across years
- Failure Pattern 2: SMALL GAPS (4 cases) - 2-5 year distances
- Root cause: Scalar multipliers insufficient for near-identical embeddings
- Proposed solution: Phase 3 dependency graphs

---

## Limitations and Phase 3 Direction

### Identified Limitations (6 manual benchmark failures)

**1. Continuity Problem:**

- Same person across multiple years (Andy Jassy 2021 vs 2024)
- Embeddings nearly identical
- Temporal alignment boost 1.18-1.24× (need ~1.5-2.0×)

**2. Small-Gap Problem:**

- 2-5 year gaps with similar contexts (Twitter 2008 vs 2006)
- Multipliers 1.05-1.10× too weak

**Root Cause:** Scalar multipliers on embedding similarity insufficient when content semantically identical.

### Phase 3 Solution: Dependency Graphs

**Proposed:**

- Extract date-constrained facts: "Andy Jassy became CEO in 2021"
- Build temporal dependency graphs: `tenure(Andy_Jassy, CEO, 2021, 2024)`
- Match query year to fact validity windows
- Structural knowledge instead of surface similarity

---

## Technical Details

### Year Extraction

```python
import re
years = re.findall(r'\b(19\d{2}|20\d{2})\b', query)
# "Who was CEO in 1997?" → [1997]
# "Changes from 2001 to 2011" → [2001, 2011]
```

### Tense Detection

```python
import spacy
nlp = spacy.load("en_core_web_sm")

past_oriented_verbs = {"become", "became", "elected", "appointed", "started"}

# "Who became CEO" → past tense (even if verb form is present)
# "Who is the CEO" → present tense
```

### Temporal Preference Classification

```python
if years and tense == "past":
    preference = "specific_date"  # Activate alignment
elif tense == "present":
    preference = "current"  # Neutral 1.0×
elif tense == "past":
    preference = "historical"  # Neutral 1.0×
else:
    preference = "agnostic"  # Neutral 1.0×
```

---

## Citation

If you use Phase 2, please cite:

```bibtex
@software{phase2_temporal_intent,
  author = {George, Alan Kochukalam},
  title = {Query-Side Temporal Intent Analysis for Temporal Knowledge Retrieval},
  year = {2026},
}
```

---

## See Also

- **Detailed Results**: [PHASE2_RESULTS_SUMMARY.md](PHASE2_RESULTS_SUMMARY.md)
- **Quick Start Guide**: [../QUICKSTART.md](../QUICKSTART.md)
- **Main README**: [../README.md](../README.md)
- **Phase 1**: [../Phase 1/](../Phase%201/)
- **Benchmarks**: [../TempQuestions/README.md](../TempQuestions/README.md)

```

---

## Expected Results

The Phase 2 benchmark tests **9 contamination cases**:

### Pure Zero-Decay (3 cases)

- Mathematical equations with no contaminants
- **Expected**: Confidence = 1.0, Status = PURE_ZERO_DECAY

### Contaminated by Temporal Markers (2 cases)

- Math truths with `currently`, `today`, etc.
- **Expected**: Confidence < 0.3, Status = CONTAMINATED

### Contaminated by Epistemic Qualifiers (2 cases)

- Math truths with `estimate`, `think`, etc.
- **Expected**: Confidence < 0.3, Status = CONTAMINATED

### Contaminated by Mortal Entities (2 cases)

- Math truths attributed to living people
- **Expected**: Confidence < 0.3 (unless past tense → sealed)

---

## Key Findings

### 1. Contamination Detection Works

Pure mathematical statements correctly maintain λ = 0.0:

```

"The Pythagorean theorem states a² + b² = c²"
→ Status: PURE_ZERO_DECAY
→ Confidence: 1.0000

```

### 2. Temporal Contamination

Temporal markers contaminate even mathematical truths:

```

"The current Pope currently knows 2 + 2 = 4"
→ Contaminants: ['current']
→ Decay rate: 0.0088 (base 0.002 × 2.1 amplifier × 2.1 temporal)
→ Confidence: 0.05

```

### 3. Epistemic Contamination

Epistemic qualifiers inject uncertainty:

```

"Scientists estimate pi is 3.14159"
→ Contaminants: ['estimate']
→ Decay rate: 0.001
→ Confidence: 0.05

```

### 4. Past Tense Sealing Overrides Contamination

Historical statements remain sealed:

```

"Einstein proved E = mc²"
→ Status: PURE_ZERO_DECAY (past tense seal)
→ Confidence: 1.0000

```

Even though Einstein is a mortal entity, the past tense "proved" seals the statement historically.

---

## Theoretical Foundation

This implements Section 3.1 (Compositional Stacking) from the framework paper:

**Contamination Rule**:

```

sentence.λ0 = ∀(component.λ0) AND no contamination

```

One impure component eliminates zero-decay status. This is the **fragility principle**: zero-decay is not inherited compositionally—it must be pure to hold.

---

## Comparison: Phase 1 vs Phase 2

| Sentence                           | Phase 1 λ | Phase 2 λ | Reason                                             |
| ---------------------------------- | --------- | --------- | -------------------------------------------------- |
| `"2 + 2 = 4"`                      | 0.0       | 0.0       | Both detect pure math                              |
| `"Scientists estimate pi is 3.14"` | 0.0       | 0.001     | Phase 2 detects "estimate" contaminant             |
| `"The current Pope knows math"`    | 0.0042    | 0.0088    | Phase 2 applies contamination + temporal amplifier |
| `"Einstein proved E=mc²"`          | 0.001     | 0.0       | Phase 2 seals past tense correctly                 |

---

## Next Steps

**Phase 3**: Dependency Graph and Cascade Propagation

- Build knowledge graph with typed edges
- Implement transmission coefficients
- Demonstrate cascade decay through dependencies
- Bridge node and fan-out risk analysis

---

## Citation

If you use Phase 2 contamination logic, please cite:

```

Alan Kochukalam George (2026). Dynamic Epistemic Decay Framework:
Phase 2 - Compositional Contamination and Zero-Decay Fragility.
Computer Engineering, Memorial University of Newfoundland.

```

---

**Current Status**: Phase 2 compositional contamination logic implemented and tested
```
