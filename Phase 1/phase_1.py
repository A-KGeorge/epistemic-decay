import spacy
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer

nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer('all-MiniLM-L6-v2')

HISTORICAL_SEAL = 0.0
CONFIDENCE_FLOOR = 0.05  # minimum confidence for any non-sealed fact

DECAY_RATES = {
    "MATHEMATICAL_TRUTH":     0.0,
    "HISTORICAL_SEAL":        0.0,
    "PHYSICAL_LAW":           0.0001,
    "GEOGRAPHIC_FACT":        0.0002,
    "INSTITUTIONAL_LEADERSHIP": 0.002,
    "POLITICAL_POSITION":     0.01,
    "CURRENT_EVENT":          0.05,
    "BREAKING_NEWS":          0.9,
    "DEFAULT":                0.001
}

TEMPORAL_MARKERS = {
    "currently", "current", "now", "today",
    "latest", "recently", "ongoing", "active", "live"
}

CURRENT_EVENT_KEYWORDS = {
    "market", "stock", "economy", "election", "vote",
    "crisis", "war", "attack", "protest", "outbreak",
    "hurricane", "earthquake", "inflation", "rate"
}

BREAKING_NEWS_KEYWORDS = {
    "breaking", "developing", "urgent", "alert"
}

PHYSICS_MATH_KEYWORDS = {
    "equation", "theorem", "law", "constant",
    "formula", "proof", "axiom"
}

INSTITUTIONAL_ROLE_KEYWORDS = {
    "president", "pope", "prime", "minister", "chancellor",
    "ceo", "chief", "director", "secretary", "governor",
    "mayor", "king", "queen", "emperor", "leader"
}

MATH_KEYWORDS = {
    "equals", "equal", "sum", "product", "square",
    "root", "prime", "integer", "factorial", "derivative",
    "integral", "matrix", "vector", "polynomial"
}

def is_main_clause_past(doc):
    for token in doc:
        if token.dep_ == "ROOT" and token.morph.get("Tense") == ["Past"]:
            # Check if this is passive voice
            # Passive: auxpass child exists, or nsubjpass dependency
            is_passive = any(
                child.dep_ in {"auxpass", "nsubjpass"} 
                for child in token.children
            )
            if is_passive:
                return False  # "was elected" — don't seal
            return True
    return False

def get_category(lemmas, tokens_lower, labels):
    checks = [
        # (condition,                                    category)
        # Order = priority — first match wins
        (bool(tokens_lower & BREAKING_NEWS_KEYWORDS),  "BREAKING_NEWS"),
        (bool(lemmas & MATH_KEYWORDS),                 "MATHEMATICAL_TRUTH"),
        (bool(lemmas & PHYSICS_MATH_KEYWORDS),         "PHYSICAL_LAW"),
        (bool(lemmas & INSTITUTIONAL_ROLE_KEYWORDS),   "INSTITUTIONAL_LEADERSHIP"),
        (bool(lemmas & CURRENT_EVENT_KEYWORDS),        "CURRENT_EVENT"),
        ("PERSON" in labels or "ORG" in labels,        "INSTITUTIONAL_LEADERSHIP"),
        ("GPE" in labels or "LOC" in labels,           "GEOGRAPHIC_FACT"),
    ]
    
    for condition, category in checks:
        if condition:
            return DECAY_RATES[category]
    
    return DECAY_RATES["DEFAULT"]

def classify_decay_rate(text):
    doc = nlp(text)
    lemmas = {token.lemma_.lower() for token in doc}
    tokens_lower = {token.text.lower() for token in doc}
    labels = {ent.label_ for ent in doc.ents}

    # 1. Tense sealing
    is_past_tense = is_main_clause_past(doc)

    PRESENT_DATE_WORDS = {"today", "now", "currently", "this year", "this month"}

    has_historical_anchor = any(
        ent.label_ == "DATE"
        and ent.text.lower() not in PRESENT_DATE_WORDS
        and not any(marker in ent.text.lower() for marker in PRESENT_DATE_WORDS)
        for ent in doc.ents
    )

    has_temporal_present = bool(tokens_lower & TEMPORAL_MARKERS)

    if (is_past_tense or has_historical_anchor) and not has_temporal_present:
        return HISTORICAL_SEAL

    # 2. Classify and apply multiplier
    multiplier = 2.1 if has_temporal_present else 1.0
    base_rate = get_category(lemmas, tokens_lower, labels)

    return base_rate * multiplier

def embed_with_decay(text, acquired_date, category=None, last_verified=None):
    """
    Embed text with temporal decay confidence.
    
    Args:
        text: The text to embed
        acquired_date: When the fact was first acquired
        category: Optional explicit category (otherwise auto-classified)
        last_verified: When the fact was last confirmed current (defaults to acquired_date)
    """
    reference_date = last_verified if last_verified else acquired_date
    days_elapsed = (datetime.now() - reference_date).days
    decay_rate = DECAY_RATES[category] if category else classify_decay_rate(text)
    
    if decay_rate == 0.0:
        confidence = 1.0  # historically sealed — always full confidence
    else:
        raw_confidence = np.exp(-decay_rate * days_elapsed)
        confidence = max(raw_confidence, CONFIDENCE_FLOOR)
    
    semantic = model.encode(text)
    return np.append(semantic, confidence)

# Tests

# Adversarial Benchmark: Semantically richer STALE vs. sparse CURRENT
# The challenge: can decay flip rankings when stale docs are semantically stronger?

benchmark = [
    # CASE 1: Catholic Church leadership
    {
        "query": "Who leads the Catholic Church?",
        "entries": [
            {
                "text": "Pope Francis is the head of the Catholic Church and leads the Vatican.",
                "acquired": datetime(2023, 1, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2025, 5, 7)
            },
            {
                "text": "Pope Leo XIV succeeded Francis in May 2025.",
                "acquired": datetime(2025, 5, 8),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 2: US President
    {
        "query": "Who is the President of the United States?",
        "entries": [
            {
                "text": "Joe Biden serves as the 46th President of the United States and Commander in Chief.",
                "acquired": datetime(2021, 1, 20),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2025, 1, 19)
            },
            {
                "text": "Donald Trump became President in January 2025.",
                "acquired": datetime(2025, 1, 20),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 3: UK Prime Minister
    {
        "query": "Who is the UK Prime Minister?",
        "entries": [
            {
                "text": "Rishi Sunak serves as Prime Minister of the United Kingdom and head of government.",
                "acquired": datetime(2022, 10, 25),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2024, 7, 4)
            },
            {
                "text": "Keir Starmer is PM after July 2024 election.",
                "acquired": datetime(2024, 7, 5),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 4: Twitter/X ownership
    {
        "query": "Who runs Twitter?",
        "entries": [
            {
                "text": "Jack Dorsey is the CEO of Twitter and leads the social media platform.",
                "acquired": datetime(2020, 1, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2022, 10, 26)
            },
            {
                "text": "Elon Musk owns X, formerly Twitter.",
                "acquired": datetime(2022, 10, 27),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 5: Solar system planets
    {
        "query": "How many planets are in the solar system?",
        "entries": [
            {
                "text": "The solar system contains nine planets including Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune, and Pluto.",
                "acquired": datetime(2000, 1, 1),
                "category": "GEOGRAPHIC_FACT",
                "valid_until": datetime(2006, 8, 23)
            },
            {
                "text": "Eight planets. Pluto reclassified in 2006.",
                "acquired": datetime(2006, 8, 24),
                "category": "GEOGRAPHIC_FACT",
                "valid_until": None
            },
        ]
    },
    
    # CASE 6: Apple CEO
    {
        "query": "Who is the CEO of Apple?",
        "entries": [
            {
                "text": "Steve Jobs is the CEO of Apple Inc. and leads the technology company.",
                "acquired": datetime(2010, 1, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2011, 8, 23)
            },
            {
                "text": "Tim Cook leads Apple since 2011.",
                "acquired": datetime(2011, 8, 24),
                "last_verified": datetime(2026, 3, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 7: German Chancellor
    {
        "query": "Who is the German Chancellor?",
        "entries": [
            {
                "text": "Angela Merkel serves as Chancellor of Germany and leads the government coalition.",
                "acquired": datetime(2020, 1, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2021, 12, 7)
            },
            {
                "text": "Olaf Scholz is Chancellor since December 2021.",
                "acquired": datetime(2021, 12, 8),
                "last_verified": datetime(2026, 3, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 8: French President
    {
        "query": "Who is the President of France?",
        "entries": [
            {
                "text": "François Hollande serves as President of the French Republic and leads the nation.",
                "acquired": datetime(2015, 1, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2017, 5, 13)
            },
            {
                "text": "Emmanuel Macron is French President since 2017.",
                "acquired": datetime(2017, 5, 14),
                "last_verified": datetime(2026, 3, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 9: Amazon CEO
    {
        "query": "Who runs Amazon?",
        "entries": [
            {
                "text": "Jeff Bezos is the CEO of Amazon and founder of the e-commerce giant.",
                "acquired": datetime(2020, 1, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2021, 7, 4)
            },
            {
                "text": "Andy Jassy became Amazon CEO in 2021.",
                "acquired": datetime(2021, 7, 5),
                "last_verified": datetime(2026, 3, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 10: Microsoft CEO
    {
        "query": "Who is Microsoft's chief executive?",
        "entries": [
            {
                "text": "Steve Ballmer is CEO of Microsoft Corporation and leads the software company.",
                "acquired": datetime(2012, 1, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2014, 2, 3)
            },
            {
                "text": "Satya Nadella runs Microsoft since 2014.",
                "acquired": datetime(2014, 2, 4),
                "last_verified": datetime(2026, 3, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 11: Twitter verification
    {
        "query": "How does Twitter verification work?",
        "entries": [
            {
                "text": "Twitter blue checkmarks verify notable public figures, journalists, and organizations for free.",
                "acquired": datetime(2021, 1, 1),                
                "category": "CURRENT_EVENT",
                "valid_until": datetime(2023, 3, 31)
            },
            {
                "text": "X verification now works as a paid subscription called X Blue. "
                        "Free legacy checkmarks were removed.",
                "acquired": datetime(2023, 4, 1),
                "last_verified": datetime(2026, 3, 1),   
                "category": "CURRENT_EVENT",
                "valid_until": None
            },
        ]
    },
    
    # CASE 12: COVID status
    {
        "query": "What is the status of COVID-19?",
        "entries": [
            {
                "text": "COVID-19 is a global pandemic with widespread lockdowns and emergency measures worldwide.",
                "acquired": datetime(2020, 6, 1),
                "category": "CURRENT_EVENT",
                "valid_until": datetime(2023, 5, 10)
            },
            {
                "text": "COVID-19 pandemic emergency status ended in May 2023. "
                        "The WHO and US government declared the public health emergency over.",
                "acquired": datetime(2023, 5, 11),
                "last_verified": datetime(2026, 3, 1),   
                "category": "CURRENT_EVENT",
                "valid_until": None
            },
        ]
    },
    
    # STABLE FACTS - decay should NOT hurt these
    
    # CASE 13: Speed of light
    {
        "query": "What is the speed of light?",
        "entries": [
            {
                "text": "Light travels at approximately 299,792,458 meters per second in vacuum.",
                "acquired": datetime(2018, 1, 1),
                "category": "PHYSICAL_LAW",
                "valid_until": None
            },
        ]
    },
    
    # CASE 14: Capital of France
    {
        "query": "What is the capital of France?",
        "entries": [
            {
                "text": "Paris is the capital city of France and seat of government.",
                "acquired": datetime(2019, 1, 1),
                "category": "GEOGRAPHIC_FACT",
                "valid_until": None
            },
        ]
    },
    
    # CASE 15: Shakespeare
    {
        "query": "Who wrote Hamlet?",
        "entries": [
            {
                "text": "William Shakespeare wrote the tragedy Hamlet in the early 17th century.",
                "acquired": datetime(2017, 1, 1),
                "category": "HISTORICAL_SEAL",
                "valid_until": None
            },
        ]
    },
    
    # CASE 16: Pythagorean theorem
    {
        "query": "What is the Pythagorean theorem?",
        "entries": [
            {
                "text": "In a right triangle, the square of the hypotenuse equals the sum of squares of the other sides.",
                "acquired": datetime(2016, 1, 1),
                "category": "MATHEMATICAL_TRUTH",
                "valid_until": None
            },
        ]
    },
    
    # CASE 17: Water boiling point
    {
        "query": "At what temperature does water boil?",
        "entries": [
            {
                "text": "Water boils at 100 degrees Celsius or 212 degrees Fahrenheit at sea level.",
                "acquired": datetime(2015, 1, 1),
                "category": "PHYSICAL_LAW",
                "valid_until": None
            },
        ]
    },
    
    # CASE 18: Mount Everest
    {
        "query": "What is the tallest mountain?",
        "entries": [
            {
                "text": "Mount Everest is the tallest mountain on Earth at 8,849 meters above sea level.",
                "acquired": datetime(2020, 1, 1),
                "category": "GEOGRAPHIC_FACT",
                "valid_until": None
            },
        ]
    },
    
    # CASE 19: Earth's moon
    {
        "query": "How many moons does Earth have?",
        "entries": [
            {
                "text": "Earth has one natural satellite called the Moon.",
                "acquired": datetime(2018, 1, 1),
                "category": "GEOGRAPHIC_FACT",
                "valid_until": None
            },
        ]
    },
    
    # CASE 20: Pi value
    {
        "query": "What is the value of pi?",
        "entries": [
            {
                "text": "Pi equals approximately 3.14159, the ratio of circumference to diameter.",
                "acquired": datetime(2019, 1, 1),
                "category": "MATHEMATICAL_TRUTH",
                "valid_until": None
            },
        ]
    },
    
    # CASE 21: Capital of Germany
    {
        "query": "What is the capital of Germany?",
        "entries": [
            {
                "text": "The capital of Germany is Berlin.",
                "acquired": datetime(2020, 1, 1),
                "category": "GEOGRAPHIC_FACT",
                "valid_until": None
            },
        ]
    },
    
    # CASE 22: Amazon rainforest location
    {
        "query": "Where is the Amazon rainforest?",
        "entries": [
            {
                "text": "The Amazon rainforest is in South America.",
                "acquired": datetime(2018, 6, 1),
                "category": "GEOGRAPHIC_FACT",
                "valid_until": None
            },
        ]
    },
    
    # CASE 23: DNA structure
    {
        "query": "What is the structure of DNA?",
        "entries": [
            {
                "text": "DNA is double-stranded.",
                "acquired": datetime(2017, 3, 15),
                "category": "PHYSICAL_LAW",
                "valid_until": None
            },
        ]
    },
]

# Run benchmark
from numpy.linalg import norm

def cosine_similarity(a, b):
    return np.dot(a, b) / (norm(a) * norm(b))

def run_benchmark_case(query, kb_entries):
    """
    Returns: (standard_is_correct, decay_is_correct, diagnostics)
    """
    query_vec = model.encode(query)
    current_date = datetime.now()
    
    standard_scores = []
    decay_scores = []
    
    for entry in kb_entries:
        last_verified = entry.get("last_verified")
        category = entry.get("category")
        vec = embed_with_decay(entry["text"], entry["acquired"], category, last_verified)
        semantic_sim = cosine_similarity(query_vec, vec[:-1])  # First 384 dims
        confidence = vec[-1]  # Last dim
        decay_score = semantic_sim * confidence
        
        standard_scores.append((semantic_sim, entry, confidence))
        decay_scores.append((decay_score, entry, confidence))
    
    standard_scores_sorted = sorted(standard_scores, key=lambda x: x[0], reverse=True)
    decay_scores_sorted = sorted(decay_scores, key=lambda x: x[0], reverse=True)
    
    standard_top = standard_scores_sorted[0]
    decay_top = decay_scores_sorted[0]
    
    # Infer correctness from valid_until dates
    standard_is_correct = (standard_top[1]["valid_until"] is None or 
                          standard_top[1]["valid_until"] >= current_date)
    decay_is_correct = (decay_top[1]["valid_until"] is None or 
                       decay_top[1]["valid_until"] >= current_date)
    
    # Diagnostics
    diagnostics = {
        "standard_top_score": standard_top[0],
        "decay_top_score": decay_top[0],
        "standard_top_confidence": standard_top[2],
        "decay_top_confidence": decay_top[2],
        "standard_top_text": standard_top[1]["text"],
        "decay_top_text": decay_top[1]["text"],
        "all_confidences": [(entry["text"][:60], conf) for _, entry, conf in standard_scores]
    }
    
    return standard_is_correct, decay_is_correct, diagnostics

# Run all 23 cases
results = {
    "both_correct": 0,
    "decay_correct_only": 0,
    "standard_correct_only": 0,
    "both_wrong": 0
}

rescued_cases = []
stable_cases = []

print("=" * 80)
print("ADVERSARIAL BENCHMARK: Standard vs. Decay Retrieval")
print("=" * 80)
print()

for i, case in enumerate(benchmark, 1):
    standard_correct, decay_correct, diagnostics = run_benchmark_case(case["query"], case["entries"])
    
    if standard_correct and decay_correct:
        outcome = "both_correct"
        symbol = "[=]"
        stable_cases.append((case["query"], diagnostics))
    elif decay_correct and not standard_correct:
        outcome = "decay_correct_only"
        symbol = "[+]"
        rescued_cases.append((case["query"], diagnostics))
    elif standard_correct and not decay_correct:
        outcome = "standard_correct_only"
        symbol = "[-]"
    else:
        outcome = "both_wrong"
        symbol = "[X]"
    
    results[outcome] += 1
    
    print(f"{symbol} Case {i:2d}: {case['query']}")
    print(f"         Standard: {'+' if standard_correct else '-'}  |  Decay: {'+' if decay_correct else '-'}  |  [{outcome}]")
    print()

print("=" * 80)
print("RESULTS SUMMARY")
print("=" * 80)
print(f"Both correct:           {results['both_correct']:2d}  (decay adds no value but doesn't hurt)")
print(f"Decay correct only:     {results['decay_correct_only']:2d}  (decay rescued a case standard got wrong) [+]")
print(f"Standard correct only:  {results['standard_correct_only']:2d}  (decay hurt a case - failure mode) [-]")
print(f"Both wrong:             {results['both_wrong']:2d}  (neither works)")
print()

if results['decay_correct_only'] > 0 and results['standard_correct_only'] <= 1:
    print("[SUCCESS] DECAY RETRIEVAL ADDS VALUE")
    print(f"  Rescued {results['decay_correct_only']} cases where standard retrieval failed")
    print(f"  Only {results['standard_correct_only']} regression(s)")
elif results['decay_correct_only'] == 0:
    print("[FAIL] DECAY RETRIEVAL ADDS NO VALUE")
    print("  No cases where decay outperformed standard retrieval")
else:
    print("[MIXED] RESULTS")
    print(f"  Decay rescued {results['decay_correct_only']} cases")
    print(f"  But caused {results['standard_correct_only']} regressions")

# VERIFICATION 1: Check confidence values on stable facts
print("\n" + "=" * 80)
print("VERIFICATION 1: Confidence Values on Stable Facts")
print("=" * 80)
print("Stable facts should maintain high confidence despite age")
print("Mathematical truths (decay=0.0) should have conf=1.0")
print("Physical laws (decay=0.0001) and geographic facts (decay=0.0002) should have conf>0.5")
print()

for query, diag in stable_cases:
    print(f"Query: {query}")
    for text, conf in diag["all_confidences"]:
        status = ""
        if conf >= 0.99:
            status = "[PERFECT]"
        elif conf >= 0.5:
            status = "[GOOD]"
        elif conf >= 0.3:
            status = "[OK]"
        else:
            status = "[LOW]"
        print(f"  confidence: {conf:.4f} {status} | {text}")
    print()

# VERIFICATION 2: Score margins on rescued cases
print("=" * 80)
print("VERIFICATION 2: Decay Correctly Flips Rankings")
print("=" * 80)
print("For each rescued case:")
print("- Standard picks stale (high semantic, low confidence)")
print("- Decay picks current (lower semantic, higher confidence)")
print("- Margin shows how strongly decay prefers current")
print()

for query, diag in rescued_cases:
    print(f"Query: {query}")
    
    # The standard top is the stale doc, decay top is the current doc
    print(f"  Standard picked (STALE):")
    print(f"    Semantic similarity: {diag['standard_top_score']:.4f}")
    print(f"    Confidence: {diag['standard_top_confidence']:.4f}")
    print(f"    Weighted score (if using decay): {diag['standard_top_score'] * diag['standard_top_confidence']:.4f}")
    print(f"    Text: {diag['standard_top_text'][:65]}")
    
    print(f"  Decay picked (CURRENT):")
    print(f"    Weighted score: {diag['decay_top_score']:.4f}")
    print(f"    Confidence: {diag['decay_top_confidence']:.4f}")
    print(f"    Text: {diag['decay_top_text'][:65]}")
    
    # Calculate margin - how much better current is than stale under decay weighting
    stale_under_decay = diag['standard_top_score'] * diag['standard_top_confidence']
    current_under_decay = diag['decay_top_score']
    margin = current_under_decay - stale_under_decay
    
    status = "[STRONG]" if margin > 0.1 else "[ROBUST]" if margin > 0.01 else "[WEAK]" if margin > 0 else "[FAIL]"
    print(f"  Decay margin: {margin:+.4f} {status}")
    print()
    