"""
Phase 3: Query Graph Extraction

Extracts structural constraints from natural language queries.
Converts queries into (entity, role, org, year) tuples for graph matching.

Examples:
    "Who was CEO of Amazon in 2021?" → {org: "Amazon", role: "CEO", year: 2021}
    "Who became PM after Thatcher?" → {org: "UK", role: "PM", directional: "after", entity: "Thatcher"}
    "Who is the founder of Apple?" → {org: "Apple", role: "founder"}
"""

import spacy
import re
from typing import Dict, Optional, List
from datetime import datetime


# Load spaCy model (reuse from Phase 2)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spaCy model...")
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")


# Role keywords (from Phase 2 constants)
ROLE_KEYWORDS = {
    "CEO", "Chief Executive Officer",
    "President", "Prime Minister", "PM",
    "founder", "co-founder",
    "Chairman", "CTO", "CFO",
    "leader", "head"
}

# Directional operators
DIRECTIONAL_KEYWORDS = {
    "before", "after", "since", "during", "until", "while"
}


def extract_query_constraints(query: str) -> Dict:
    """
    Extract structured constraints from query text.
    
    Args:
        query: Natural language query
        
    Returns:
        Dict with fields:
        - org: Organization name (or None)
        - role: Role/position (or None)
        - year: Explicit year (or None)
        - entity: Explicit entity mentioned (or None)
        - directional: before/after/since/during/until/while (or None)
        - query_type: specific_role_year | succession | founder | temporal_overlap | general
        
    Examples:
        >>> extract_query_constraints("Who was CEO of Amazon in 2021?")
        {
            "org": "Amazon",
            "role": "CEO",
            "year": 2021,
            "entity": None,
            "directional": None,
            "query_type": "specific_role_year"
        }
        
        >>> extract_query_constraints("Who became PM after Thatcher?")
        {
            "org": "UK",  # Inferred from context
            "role": "PM",
            "year": None,
            "entity": "Thatcher",
            "directional": "after",
            "query_type": "succession"
        }
    """
    doc = nlp(query)  # Keep original case for NER
    query_lower = query.lower()  # Use lowercase for keyword matching
    
    constraints = {
        "org": None,
        "role": None,
        "year": None,
        "entity": None,
        "directional": None,
        "query_type": "general"
    }
    
    # Extract year
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', query)
    if year_match:
        constraints["year"] = int(year_match.group(1))
    
    # Check for directional operators first (affects role extraction)
    for keyword in DIRECTIONAL_KEYWORDS:
        if keyword in query_lower:
            constraints["directional"] = keyword
            break
    
    # For "while" queries, extract role from MAIN question, not "while" clause
    if constraints["directional"] == "while":
        # Split query at "while" to separate main question from condition
        parts = query_lower.split("while")
        if len(parts) == 2:
            main_question = parts[0]  # "Who was the US President"
            while_clause = parts[1]   # "Steve Jobs was the CEO of Apple"
            
            # Extract role from main question only
            for role in ROLE_KEYWORDS:
                if role.lower() in main_question:
                    constraints["role"] = role
                    break
        else:
            # Fallback to normal extraction
            for role in ROLE_KEYWORDS:
                if role.lower() in query_lower:
                    constraints["role"] = role
                    break
    else:
        # Normal role extraction for non-while queries
        for role in ROLE_KEYWORDS:
            if role.lower() in query_lower:
                constraints["role"] = role
                break
    
    # Extract organizations and people using NER (use original doc with capitalization)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    
    # Organizations can be ORG or GPE (geo-political entities like countries)
    orgs = [text for text, label in entities if label in ["ORG", "GPE"]]
    if orgs:
        constraints["org"] = orgs[0]  # Take first org
    
    people = [text for text, label in entities if label == "PERSON"]
    if people:
        # Strip possessive markers like "'s"
        entity_text = people[0].rstrip("'s")
        constraints["entity"] = entity_text
    
    # Special case: If we found a "person" but it appears with a corporate role (CEO, etc.),
    # it's probably a company name misclassified by NER (e.g., "Twitter")
    # Pattern: "CEO of Twitter" → Twitter is org, not person
    if not constraints["org"] and constraints["entity"]:
        # Check if query contains corporate role keywords
        corporate_roles = ["ceo", "cto", "cfo", "chairman", "chief executive"]
        has_corporate_role = any(role in query_lower for role in corporate_roles)
        
        # If there's a corporate role and no real organization found, the "person" is likely the org
        if has_corporate_role:
            constraints["org"] = constraints["entity"]
            constraints["entity"] = None
    
    # Check for directional operators
    for keyword in DIRECTIONAL_KEYWORDS:
        if keyword in query_lower:
            constraints["directional"] = keyword
            break
    
    # Infer org from context if not found
    if not constraints["org"] and constraints["role"]:
        inferred_org = extract_org_from_context(query, constraints["role"])
        if inferred_org:
            constraints["org"] = inferred_org
    
    # Infer query type (do this after org inference)
    if constraints["year"] and constraints["role"] and constraints["org"]:
        constraints["query_type"] = "specific_role_year"
    elif constraints["directional"] == "while" and constraints["entity"]:
        constraints["query_type"] = "temporal_overlap"
    elif constraints["directional"] and constraints["entity"]:
        constraints["query_type"] = "succession"
    elif "founder" in query_lower or "founded" in query_lower:
        constraints["query_type"] = "founder"
        if not constraints["role"]:
            constraints["role"] = "founder"
    
    return constraints


def extract_org_from_context(query: str, role: str) -> Optional[str]:
    """
    Infer organization from context clues.
    
    Args:
        query: Query text
        role: Role extracted from query
        
    Returns:
        Organization name or None
        
    Examples:
        "Who was Prime Minister in 2007?" → "UK" (inferred)
        "Who was President in 1990?" → "United States" (inferred)
    """
    query_lower = query.lower()
    
    # UK political roles
    if role in ["Prime Minister", "PM"]:
        return "UK"
    
    # US political roles
    if role in ["President"] and "united states" not in query_lower:
        # If not explicitly mentioned, assume US president
        return "United States"
    
    # French political roles
    if "france" in query_lower or "french" in query_lower:
        return "France"
    
    return None


def match_query_to_graph(query: str, knowledge_graph) -> Dict:
    """
    Match query constraints against knowledge graph.
    
    Args:
        query: Natural language query
        knowledge_graph: TemporalKnowledgeGraph instance
        
    Returns:
        Dict with:
        - constraints: Extracted query constraints
        - matches: List of matching entities from graph
        - match_score: Confidence in structural match (0.0-1.0)
    """
    constraints = extract_query_constraints(query)
    
    # If org not found, try to infer from role
    if not constraints["org"] and constraints["role"]:
        inferred_org = extract_org_from_context(query, constraints["role"])
        if inferred_org:
            constraints["org"] = inferred_org
    
    matches = []
    match_score = 0.0
    
    # Query graph for specific role/year
    if constraints["query_type"] == "specific_role_year":
        org = constraints["org"]
        role = constraints["role"]
        year = constraints["year"]
        
        if org and role and year:
            holder = knowledge_graph.get_role_holder(org, role, year)
            if holder:
                matches.append(holder)
                match_score = 1.0  # Exact structural match
    
    # Query graph for succession
    elif constraints["query_type"] == "succession":
        org = constraints["org"]
        role = constraints["role"]
        directional = constraints["directional"]
        entity = constraints["entity"]
        
        if org and role:
            chain = knowledge_graph.get_succession_chain(org, role)
            
            if entity and entity in chain:
                idx = chain.index(entity)
                
                if directional == "after" and idx + 1 < len(chain):
                    matches.append(chain[idx + 1])
                    match_score = 1.0
                elif directional == "before" and idx > 0:
                    matches.append(chain[idx - 1])
                    match_score = 1.0
    
    # Query graph for founder (special case: no year needed)
    elif constraints["query_type"] == "founder":
        org = constraints["org"]
        role = constraints.get("role", "founder")
        
        if org and role:
            # Founders typically don't have end dates in their founding role
            # Or we look for earliest role holder
            all_holders = knowledge_graph.get_all_role_holders(org, role)
            if all_holders:
                # Take earliest by start_date
                matches.append(all_holders[0]["entity"])
                match_score = 1.0
    
    return {
        "constraints": constraints,
        "matches": matches,
        "match_score": match_score
    }


def test_query_extraction():
    """Test query constraint extraction."""
    test_cases = [
        (
            "Who was CEO of Amazon in 2021?",
            {"org": "Amazon", "role": "CEO", "year": 2021, "query_type": "specific_role_year"}
        ),
        (
            "Who became Prime Minister after Thatcher?",
            {"org": "UK", "role": "Prime Minister", "directional": "after", "query_type": "succession"}
        ),
        (
            "Who is the founder of Apple?",
            {"org": "Apple", "role": "founder", "query_type": "founder"}
        ),
        (
            "Who was President in 2007?",
            {"org": "United States", "role": "President", "year": 2007, "query_type": "specific_role_year"}
        ),
    ]
    
    print("=" * 80)
    print("QUERY EXTRACTION TESTS")
    print("=" * 80)
    print()
    
    for query, expected_fields in test_cases:
        result = extract_query_constraints(query)
        
        print(f"Query: {query}")
        print(f"Extracted: {result}")
        
        # Check expected fields
        all_match = True
        for field, expected_value in expected_fields.items():
            if result.get(field) != expected_value:
                print(f"  ✗ FAIL: {field} = {result.get(field)} (expected {expected_value})")
                all_match = False
        
        if all_match:
            print("  ✓ PASS")
        
        print()
    
    print("=" * 80)


if __name__ == "__main__":
    test_query_extraction()
