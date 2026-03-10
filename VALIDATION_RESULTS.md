# Temporal Decay Framework: Validation Results

**Date**: March 10, 2026  
**Author**: Alan Kochukalam George

> 📊 **Latest benchmark runs**: See [RESULTS.md](RESULTS.md) (auto-generated)  
> 📋 **Methodology details**: See [VALIDATION_METHODOLOGY.md](VALIDATION_METHODOLOGY.md)

---

## Quick Summary

The temporal decay framework has been validated across **four independent benchmarks** totaling **1,977 test cases**:

| Benchmark                 | Test Cases | Purpose                                          |
| ------------------------- | ---------- | ------------------------------------------------ |
| **Phase 1 Adversarial**   | 23         | Document-side decay with semantic richness bias  |
| **Verified Programmatic** | 153        | Query-side intent with verified historical facts |
| **Manual Specific Date**  | 61         | Hand-crafted adversarial cases                   |
| **TempQuestions**         | 1,740      | Large-scale external validation                  |
| **TOTAL**                 | **1,977**  | Comprehensive temporal reasoning coverage        |

### Latest Performance

**See [RESULTS.md](RESULTS.md) for current numbers** (updated automatically on each benchmark run)

Expected performance based on latest validations:

- **Phase 1 Adversarial**: 100% (23/23) - All time-sensitive cases rescued, zero regressions on stable facts
- **Verified Programmatic**: 100% (153/153) - Perfect year matching on programmatic benchmark
- **Manual Specific Date**: 90.2% (55/61) - High accuracy on adversarial cases
- **TempQuestions**: 92.1% (1,602/1,740) - Zero regressions on general temporal queries

---

## Key Publications Claims

✅ **1,977 test cases** validated with **zero regressions** across all benchmarks  
✅ **100% accuracy** on programmatic verified benchmark (153 cases)  
✅ **Programmatic generation** prevents overfitting criticism  
✅ **External validation** on TempQuestions dataset (1,740 cases)  
✅ **Multi-decade coverage** (1970s-2020s) across tech and political domains

---

## Documentation

- **[RESULTS.md](RESULTS.md)**: Auto-generated benchmark results (updated on each run)
- **[VALIDATION_METHODOLOGY.md](VALIDATION_METHODOLOGY.md)**: Complete methodology, architecture, and failure analysis
- **[QUICKSTART.md](QUICKSTART.md)**: Step-by-step commands to reproduce all benchmarks
- **[README.md](README.md)**: Project overview and Phase 3 roadmap

---

## How to Reproduce

```powershell
# Activate virtual environment
.\Phase 1\venv\Scripts\Activate.ps1

# Run Phase 1 adversarial (23 cases)
cd "Phase 1"
python phase_1.py

# Run Phase 2 verified programmatic (153 cases)
cd ..\Phase 2
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/verified_specific_date_benchmark.json

# Run Phase 2 manual adversarial (61 cases)
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/specific_date_benchmark_large.json

# Run Phase 2 TempQuestions (1,740 cases)
python evaluate_query_intent.py --benchmark ../TempQuestions/cache/benchmarks/tempquestions_retrieval_large.json
```

After each run, [RESULTS.md](RESULTS.md) is automatically updated with timestamped results.

---

## Citation

```bibtex
@misc{george2026temporal_decay,
  author = {George, Alan Kochukalam},
  title = {Dynamic Epistemic Decay Framework: Temporal Knowledge Representation for RAG Systems},
  year = {2026},
  howpublished = {Computer Engineering, Memorial University of Newfoundland},
  note = {Validated on 1,977 test cases across 4 benchmarks with zero regressions}
}
```

---

**Status**: Publication-ready validation complete

- ✅ Zero regressions across all 1,977 test cases
- ✅ Programmatic benchmarks prevent overfitting criticism
- ✅ Results automatically tracked in [RESULTS.md](RESULTS.md)
- ✅ Comprehensive methodology documented in [VALIDATION_METHODOLOGY.md](VALIDATION_METHODOLOGY.md)
