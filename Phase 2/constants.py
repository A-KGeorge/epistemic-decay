"""
Constants and configuration for the Dynamic Epistemic Decay Framework
"""

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
