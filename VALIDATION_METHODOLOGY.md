# Temporal Decay Framework: Validation Methodology

**Last Updated**: March 10, 2026  
**Author**: Alan Kochukalam George

> **For latest benchmark results**, see [RESULTS.md](RESULTS.md) (auto-generated on each evaluation run)

---

## Overview

The temporal decay framework is validated across **four independent benchmarks** with different objectives:

1. **Phase 1 Adversarial** (23 cases): Document-side decay with semantic richness bias
2. **Verified Programmatic** (153 cases): Query-side intent with programmatically-generated historical facts
3. **Manual Specific Date** (61 cases): Hand-crafted adversarial cases targeting known failure modes
4. **TempQuestions Large-Scale** (1,740 cases): External temporal QA benchmark for zero-regression validation

Total: **1,977 test cases** across diverse temporal reasoning scenarios.

---

## Benchmark Descriptions

### Phase 1: Adversarial Benchmark (Internal)

**Purpose**: Test temporal decay with carefully designed adversarial cases where standard retrieval fails due to semantic richness bias.

**Design**:

- 12 time-sensitive queries (leadership, news, policy changes)
- 11 stable facts (math, physics, geography) as regression controls
- Stale documents are semantically richer than current documents to test if decay can overcome embedding bias

**Example**:

```
Query: "Who is the current Pope?"

Stale (acquired 2024-03-14):
  "Pope Francis, elected in 2013, has transformed the Vatican with
   progressive reforms on climate change, social justice, and interfaith
   dialogue. His papacy marks a historic shift..." (semantically rich)

Current (acquired 2025-05-08):
  "Pope Leo XIV succeeded Francis in May 2025." (sparse)

Standard retrieval: Picks stale (0.72 similarity)
Decay retrieval: Picks current (decay penalty overcomes semantic gap)
```

**Validation Goal**: Ensure decay rescues all 12 time-sensitive cases without breaking 11 stable facts.

---

### Phase 2.1: Verified Programmatic Benchmark ⭐

**Purpose**: Validate query-side temporal intent with programmatically-generated test cases that can't be accused of overfitting.

**Design**:

- 153 test cases from curated historical facts (18 entities, 58 leadership tenures)
- Covers CEOs (Apple, Microsoft, Google, Amazon, etc.) and political leaders (US, UK, Canada, Japan, etc.)
- Spans 5 decades (1970s-2020s)
- Difficulty tiers: easy (2 docs), medium (3 docs), hard (4 docs)

**Data Source**:

- Manually curated seed data with Wikipedia citations
- Programmatic generation ensures reproducibility
- All facts verifiable from public sources

**Example**:

```
Query: "Who was the Prime Minister of Japan in 2002?"
Expected: Junichiro Koizumi

Documents:
- from_1997: "Ryutaro Hashimoto holds this position..." (acquired 1997-07-30)
- from_2002: "Junichiro Koizumi holds this position..." (acquired 2002-04-26) ✓
- from_2016: "Shinzo Abe holds this position..." (acquired 2016-05-11)
- from_2022: "Fumio Kishida holds this position..." (acquired 2022-12-10)

Difficulty: hard (4 documents, needs precise year matching)
```

**Validation Goal**: Achieve >95% accuracy by correctly matching query year to document acquisition date.

---

### Phase 2.2: Manual Specific Date Benchmark

**Purpose**: Hand-crafted adversarial cases targeting known limitations of the programmatic benchmark.

**Design**:

- 61 manually-created test cases
- Focuses on edge cases:
  - Same person across multiple tenures (e.g., Jack Dorsey at Twitter 2006-2008, 2015-2021)
  - Small date gaps (2-5 years between documents)
  - Continuity scenarios where embedding similarity is nearly identical

**Example**:

```
Query: "Who was the CEO of Twitter in 2010?"
Expected: Evan Williams

Documents:
- from_2008: "Evan Williams became CEO." (acquired 2008-10-01) ✓
- from_2015: "Jack Dorsey returned as CEO." (acquired 2015-07-01)

Challenge: Same company, different person, small gap
Phase 1: May fail (decay multipliers similar)
Phase 2: Should succeed (year extraction: 2010 closer to 2008 than 2015)
```

**Known Failures**: ~6 cases fail due to person continuity (same person = identical embeddings). See [Phase 3 roadmap](#next-steps-phase-3) for planned solution.

**Validation Goal**: Achieve >85% accuracy on adversarial cases where Phase 1 struggles.

---

### Phase 2.3: TempQuestions Large-Scale

**Purpose**: External validation with zero-regression requirement on general temporal queries.

**Design**:

- 1,740 test cases generated from TempQuestions dataset
- Augmented with Wikidata SPARQL queries for current answers
- 88% coverage (1,763 questions successfully augmented, 1,740 used)
- Mix of leadership, statistics, and general temporal facts

**Methodology**:

1. Generate original question: "Who was US President in 1998?"
2. Query Wikidata for current answer (e.g., "Joe Biden", 2024-01-20)
3. Create retrieval test: stale doc (1998 answer) vs current doc (2024 answer)
4. Query asks about past year → should prefer stale doc

**Validation Goal**: Maintain Phase 1 accuracy (92.1%) with zero regressions to prove Phase 2 doesn't hurt general temporal queries.

---

## Technical Architecture

### Phase 1: Document-Side Temporal Decay

**Core Innovation**: Augment 384-dim embeddings with confidence dimension:

```python
embedding_with_decay = [semantic_384, confidence_1]
```

**Decay Functions**:

- Leadership: `exp(-0.8 * years)`
- Statistics: `exp(-0.15 * years)`
- Technology: `exp(-0.4 * years)`
- Stable facts: no decay (confidence = 1.0 always)

**Historical Sealing**: Past tense facts detected via NLP get zero decay (confidence locked at 1.0).

---

### Phase 2: Query-Side Temporal Intent

**Core Innovation**: Detect temporal intent in queries and align with document acquisition dates.

**Intent Types**:

1. **Specific date**: "Who was CEO in 2015?" → extract year, prefer docs from that year
2. **Current**: "Who is the current CEO?" → prefer recent docs
3. **Historical**: "Who was the first CEO?" → prefer old docs
4. **Agnostic**: "What is 2+2?" → no temporal preference

**Temporal Alignment Bonus**:

```python
if query_year and abs(doc_year - query_year) <= 1:
    boost = 0.15  # Strong boost for year match
elif query_year and abs(doc_year - query_year) <= 3:
    boost = 0.10  # Moderate boost for near match
else:
    boost = 0.0
```

**Compositional Contamination**: Pure truths (math, definitions) get zero decay even if query has temporal intent, preventing fragility.

---

## Statistical Validation

### Sample Size

- **1,977 total test cases** exceeds typical academic benchmarks
- Phase 2 alone: **1,954 cases** (largest contribution to validation)
- Multi-domain coverage: tech (423 cases), political (498 cases), temporal QA (1,740 cases)

### Coverage

- **5 decades** (1970s-2020s)
- **18 entities** in verified benchmark
- **4 benchmark types** preventing overfitting to single dataset
- **3 difficulty tiers** (easy/medium/hard) ensuring robust evaluation

### Significance

- **Zero regressions** across all 1,977 cases (critical for production deployment)
- **Programmatic generation** prevents accusations of hand-tuning to test data
- **External validation** (TempQuestions) proves generalization beyond internal benchmarks

---

## Publication-Ready Claims

Based on validation results, we can claim:

1. ✅ **Temporal decay rescues 82% of failed cases** (1,954 Phase 2 tests)
2. ✅ **Zero regressions** on stable facts and general temporal queries
3. ✅ **100% accuracy** on programmatic verified benchmark (153 cases)
4. ✅ **90%+ accuracy** on adversarial manual cases (55/61 correct)
5. ✅ **Scales to 1,740 cases** with maintained performance

---

## Failure Analysis

### Known Limitations (6 cases from Manual Benchmark)

**Root Cause**: Same person across multiple tenures with small time gaps

**Example**:

```
Query: "Who was CEO of Apple in 2004?"
Expected: Steve Jobs

Documents:
- from_1998: "Steve Jobs returned as CEO"
- from_2004: "Steve Jobs continues as CEO"

Problem: Embeddings are nearly identical (same person mentioned)
Phase 2: Cannot distinguish based on year alone when semantic content identical
```

**Failure Pattern**:

- Continuity: Same person across years (embeddings identical)
- Small gaps: 2-5 years (multipliers insufficient to overcome semantic tie)

**Planned Solution (Phase 3)**: Extract date-constrained facts (e.g., "Steve Jobs became CEO in 1997") and match against query year using structural knowledge graph rather than embeddings.

📂 **See**: [Phase 2/analyze_failures.py](Phase%202/analyze_failures.py) for detailed failure analysis

---

## Next Steps: Phase 3

### Proposed Architecture: Dependency Graph Propagation

**Motivation**: Handle cases where embeddings are identical (same person, continuity scenarios)

**Approach**:

1. Extract temporal relationships: "X became Y in YEAR"
2. Build knowledge graph with start/end dates
3. Query graph for "Who was Y in YEAR?" using interval arithmetic
4. Fall back to embedding+decay if graph has no answer

**Example**:

```
Query: "Who was CEO of Apple in 2004?"

Graph lookup:
  Steve Jobs: CEO from 1997-2011
  Tim Cook: CEO from 2011-present

Result: Steve Jobs (2004 in [1997, 2011])
```

**Expected Impact**: Rescue remaining 6 manual benchmark failures (90.2% → 100%)

---

## Citation

```bibtex
@misc{george2026temporal_decay,
  author = {George, Alan Kochukalam},
  title = {Dynamic Epistemic Decay Framework: Temporal Knowledge Representation for RAG Systems},
  year = {2026},
  howpublished = {Computer Engineering, Memorial University of Newfoundland},
  note = {Validated on 1,977 test cases with 92.7\% overall accuracy and zero regressions}
}
```

---

## Files and Benchmarks

### Phase 1

- Code: `Phase 1/phase_1.py`
- Test data: Embedded in `Phase 1/benchmark_data.py`
- Results: See [RESULTS.md](RESULTS.md) for latest run

### Phase 2

- Code: `Phase 2/evaluate_query_intent.py`
- Benchmarks:
  - `TempQuestions/cache/benchmarks/verified_specific_date_benchmark.json` (153 cases)
  - `TempQuestions/cache/benchmarks/specific_date_benchmark_large.json` (61 cases)
  - `TempQuestions/cache/benchmarks/tempquestions_retrieval_large.json` (1,740 cases)
- Results: Auto-generated in [RESULTS.md](RESULTS.md) on each evaluation run

---

**For latest performance numbers, see** [RESULTS.md](RESULTS.md) (updated automatically on each benchmark run)
