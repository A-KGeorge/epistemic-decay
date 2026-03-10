"""
Full-Scale TempQuestions (1000+) Evaluation Pipeline

Runs complete pipeline:
1. Generate/download 1000 TempQuestions
2. Augment with Wikidata (rate-limited, takes ~20 minutes)  
3. Convert to retrieval benchmarks
4. Evaluate with decay framework
"""

from tempquestions_batch import TempQuestionsBatchProcessor
import subprocess
import sys


def run_custom_scale_pipeline(count: int):
    """Run custom-count pipeline with Wikidata integration."""
    
    print("=" * 80)
    print(f"TEMPQUESTIONS PIPELINE ({count} ENTRIES)")
    print("=" * 80)
    print()
    estimated_time = (count * 0.88) / 60  # 88% success rate, 1 sec per call
    print(f"Estimated time: ~{estimated_time:.1f} minutes (Wikidata rate limiting)")
    print(f"   (1 second between API calls x ~{int(count * 0.88)} successful lookups)")
    print()
    
    response = input("Continue? (yes/no): ")
    if response.lower() not in ["yes", "y"]:
        print("Aborted.")
        return
    
    # Step 1-3: Batch processing with Wikidata
    processor = TempQuestionsBatchProcessor()
    processor.process_full_pipeline(max_entries=None, total_count=count)  # Process all
    
    # Step 4: Evaluate
    print("\n" + "=" * 80)
    print("STEP 4: Evaluate with Decay Framework")
    print("=" * 80)
    
    benchmark_file = "cache/benchmarks/tempquestions_retrieval_large.json"
    
    result = subprocess.run([
        sys.executable,
        "evaluate_phase1.py",
        "--benchmark", benchmark_file,
        "--large"
    ])
    
    if result.returncode == 0:
        print("\nOK: Full pipeline complete!")
        print(f"  Results saved to: {benchmark_file}")
    else:
        print(f"\nERROR: Evaluation failed with exit code {result.returncode}")


def run_demo_scale():
    """Run 100-entry demo (faster)."""
    print("=" * 80)
    print("DEMO-SCALE TEMPQUESTIONS PIPELINE (100 ENTRIES)")
    print("=" * 80)
    print()
    print("This will take ~2 minutes with Wikidata rate limiting.")
    print()
    
    # Batch process 100 entries
    processor = TempQuestionsBatchProcessor()
    processor.process_full_pipeline(max_entries=100, total_count=100)
    
    # Evaluate
    print("\n" + "=" * 80)
    print("STEP 4: Evaluate with Decay Framework")
    print("=" * 80)
    
    benchmark_file = "cache/benchmarks/tempquestions_retrieval_large.json"
    
    result = subprocess.run([
        sys.executable,
        "evaluate_phase1.py",
        "--benchmark", benchmark_file,
        "--large"
    ])
    
    if result.returncode == 0:
        print("\nOK: Demo complete!")
        print(f"  Benchmark: {benchmark_file}")
        print(f"\nTo run full 1000-entry scale:")
        print(f"  python tempquestions_full_scale.py --full")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run TempQuestions at scale",
        epilog="Examples:\n  python tempquestions_full_scale.py --demo\n  python tempquestions_full_scale.py --count 1500\n  python tempquestions_full_scale.py --count 2000",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--count", type=int, metavar="N",
                       help="Generate N questions (recommended: 500-2000)")
    parser.add_argument("--full", action="store_true",
                       help="Run full 1000-entry pipeline (same as --count 1000)")
    parser.add_argument("--demo", action="store_true",
                       help="Run 100-entry demo (faster)")
    
    args = parser.parse_args()
    
    if args.count:
        if args.count < 500:
            print("WARNING: Counts below 500 may not provide robust validation.")
            print("  Consider using --demo for quick tests (100 entries).")
        elif args.count > 2000:
            print("WARNING: Large counts (>2000) will take significant time.")
            print(f"  Estimated time: ~{(args.count * 0.88) / 60:.1f} minutes")
        run_custom_scale_pipeline(args.count)
    elif args.demo:
        run_demo_scale()
    elif args.full:
        run_custom_scale_pipeline(1000)
    else:
        print("Usage: python tempquestions_full_scale.py [--demo|--full|--count N]")
        print("")
        print("Options:")
        print("  --demo         Run 100-entry demo (~2 minutes)")
        print("  --full         Run 1000-entry pipeline (~15 minutes)")
        print("  --count N      Generate N questions (recommended: 500-2000)")
        print("")
        print("Examples:")
        print("  python tempquestions_full_scale.py --demo")
        print("  python tempquestions_full_scale.py --count 1500")
        print("  python tempquestions_full_scale.py --count 2000")
