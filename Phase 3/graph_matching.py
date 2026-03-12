"""
Phase 3: Graph Matching & Structural Alignment Scoring

Computes how well a document's structural facts match a query's constraints.
Returns alignment scores [0.0, 1.0] based on temporal precision of the match.

Match types:
- EXACT (1.0): Perfect structural match (entity, role, org, year all align)
- NEAR_MATCH (0.8): Entity/role/org match, year off by 1-2 years
- PARTIAL (0.3): Role/org match but entity or year mismatch
- NO_MATCH (0.0): No structural overlap

Example:
    Query: "Who was Amazon CEO in 2021?"
    Doc facts: [(Andy Jassy, CEO, Amazon, 2021-07-05, present)]
    Score: 1.0 (EXACT - query year 2021 ∈ [2021-07-05, present])
"""

from typing import Dict, Optional
from datetime import datetime
import sys
sys.path.append('Phase 3')

from knowledge_graph import TemporalKnowledgeGraph
from query_graph import extract_query_constraints


def compute_graph_alignment(query: str, knowledge_graph: TemporalKnowledgeGraph,
                            doc_acquired_date: Optional[datetime] = None,
                            doc_text: Optional[str] = None) -> Dict:
    """
    Compute structural alignment between query and knowledge graph.
    
    Args:
        query: Natural language query
        knowledge_graph: Graph containing document facts
        doc_acquired_date: When document was acquired (for era matching)
        doc_text: Document text (for entity matching in temporal overlap queries)
        
    Returns:
        Dict with:
        - score: Alignment score [0.0, 1.0]
        - match_type: EXACT | NEAR_MATCH | PARTIAL | NO_MATCH
        - matched_entity: Entity that matched (or None)
        - explanation: Human-readable match explanation
        - all_matches: List of all matching entities (for temporal overlap queries)
        
    Examples:
        >>> graph = TemporalKnowledgeGraph()
        >>> graph.add_role_fact("Andy Jassy", "CEO", "Amazon", "2021-07-05", None)
        >>> result = compute_graph_alignment("Who was CEO of Amazon in 2021?", graph)
        >>> result["score"]
        1.0
        >>> result["match_type"]
        'EXACT'
    """
    # Extract query constraints
    constraints = extract_query_constraints(query)
    
    org = constraints["org"]
    role = constraints["role"]
    year = constraints["year"]
    query_type = constraints["query_type"]
    
    # Normalize organization names (do this BEFORE query handlers)
    if org:
        org_lower = org.lower()
        if org_lower in ["us", "usa", "u.s.", "u.s.a.", "united states", "america"]:
            org = "United States"
            constraints["org"] = org
        elif org_lower in ["uk", "u.k.", "united kingdom", "britain", "great britain"]:
            org = "United Kingdom"
            constraints["org"] = org
        elif org_lower in ["france", "french republic"]:
            org = "France"
            constraints["org"] = org
    
    result = {
        "score": 0.0,
        "match_type": "NO_MATCH",
        "matched_entity": None,
        "explanation": "No structural match found",
        "constraints": constraints,
        "all_matches": []  # For temporal overlap queries with multiple valid answers
    }
    
    # Handle specific_role_year queries
    if query_type == "specific_role_year":
        if org and role and year:
            holder = knowledge_graph.get_role_holder(org, role, year)
            
            if holder:
                result["score"] = 1.0
                result["match_type"] = "EXACT"
                result["matched_entity"] = holder
                result["explanation"] = f"{holder} held {role} at {org} in {year}"
            else:
                # Check if role exists at org (but wrong year)
                all_holders = knowledge_graph.get_all_role_holders(org, role)
                
                if all_holders:
                    # Find closest year match
                    closest_gap = float('inf')
                    closest_holder = None
                    
                    for holder_data in all_holders:
                        start = holder_data["start_date"]
                        end = holder_data["end_date"]
                        
                        if start:
                            gap_start = abs(start.year - year)
                            if gap_start < closest_gap:
                                closest_gap = gap_start
                                closest_holder = holder_data["entity"]
                        
                        if end:
                            gap_end = abs(end.year - year)
                            if gap_end < closest_gap:
                                closest_gap = gap_end
                                closest_holder = holder_data["entity"]
                    
                    if closest_gap <= 2:
                        result["score"] = 0.8
                        result["match_type"] = "NEAR_MATCH"
                        result["matched_entity"] = closest_holder
                        result["explanation"] = f"{closest_holder} held {role} at {org}, off by {closest_gap} years"
                    elif closest_gap <= 5:
                        result["score"] = 0.3
                        result["match_type"] = "PARTIAL"  
                        result["matched_entity"] = closest_holder
                        result["explanation"] = f"{closest_holder} held {role} at {org}, off by {closest_gap} years"
    
    # Handle succession queries (before/after)
    elif query_type == "succession":
        directional = constraints.get("directional")
        entity = constraints.get("entity")
        
        if org and role and directional and entity:
            chain = knowledge_graph.get_succession_chain(org, role)
            
            # Find entity in chain (handle partial name matches like "Bezos" → "Jeff Bezos")
            matched_idx = -1
            for i, name in enumerate(chain):
                if entity.lower() in name.lower() or name.lower() in entity.lower():
                    matched_idx = i
                    break
            
            if matched_idx >= 0:
                if directional == "after" and matched_idx + 1 < len(chain):
                    successor = chain[matched_idx + 1]
                    result["score"] = 1.0
                    result["match_type"] = "EXACT"
                    result["matched_entity"] = successor
                    result["explanation"] = f"{successor} succeeded {chain[matched_idx]} as {role} of {org}"
                
                elif directional == "before" and matched_idx > 0:
                    predecessor = chain[matched_idx - 1]
                    result["score"] = 1.0
                    result["match_type"] = "EXACT"
                    result["matched_entity"] = predecessor
                    result["explanation"] = f"{predecessor} held {role} of {org} before {chain[matched_idx]}"
    
    # Handle founder queries
    elif query_type == "founder":
        if org:
            role_to_check = constraints.get("role", "CEO")  # Default to CEO if founder not found
            all_holders = knowledge_graph.get_all_role_holders(org, role_to_check)
            
            if all_holders:
                # Founder is earliest holder
                founder = all_holders[0]["entity"]
                result["score"] = 1.0
                result["match_type"] = "EXACT"
                result["matched_entity"] = founder
                result["explanation"] = f"{founder} was founder / earliest {role_to_check} of {org}"
    
    # Handle temporal overlap queries ("while" queries)
    elif query_type == "temporal_overlap":
        # Example: "Who was President while Steve Jobs was CEO of Apple?"
        # Strategy: Parse "while X was Y of Z" to extract entity1, role1, org1
        # Then find role_query holders at org_query during that interval
        
        entity1 = constraints.get("entity")  # e.g., "Steve Job" (NER may drop 's')
        role_query = constraints.get("role")  # e.g., "President" (what we're asking about)
        org_query = constraints.get("org")    # e.g., "United States" (already normalized)
        
        if entity1 and role_query:
            # Parse the "while" clause to extract entity1's role and org
            # Pattern: "while [entity] was [role] of [org]"
            import re
            query_lower = query.lower()
            
            # Extract role and org from "while" clause
            # Simplified: Look for common patterns
            entity1_role = None
            entity1_org = None
            
            # Try to find role mentions in "while" clause
            while_match = re.search(r'while\s+.*?\s+(?:was|is)\s+(?:the\s+)?(\w+)\s+(?:of|at)\s+(\w+)', query_lower, re.IGNORECASE)
            if while_match:
                entity1_role = while_match.group(1).upper()
                entity1_org = while_match.group(2).capitalize()
                
                # Standardize role names
                if entity1_role == "CEO":
                    entity1_role = "CEO"
                elif entity1_role in ["PRESIDENT", "PRES"]:
                    entity1_role = "President"
                elif entity1_role in ["PM", "PRIME"]:
                    entity1_role = "Prime Minister"
            
            # If parsing failed, try common defaults based on entity
            if not entity1_role or not entity1_org:
                # Try to guess from context
                entity1_lower = entity1.lower()
                if "job" in entity1_lower or "cook" in entity1_lower:  # Jobs or Cook
                    entity1_role = "CEO"
                    entity1_org = "Apple"
                elif "bezos" in entity1_lower or "jassy" in entity1_lower:
                    entity1_role = "CEO"
                    entity1_org = "Amazon"
                elif "zuckerberg" in entity1_lower:
                    entity1_role = "CEO"
                    entity1_org = "Meta"
            
            if entity1_role and entity1_org:
                # Try to find entity1 with fuzzy matching (handle "Steve Job" vs "Steve Jobs")
                # Get all role holders for this org/role
                all_holders = knowledge_graph.get_all_role_holders(entity1_org, entity1_role)
                
                matched_entity = None
                entity1_interval = None
                
                # Fuzzy match entity name
                for holder_data in all_holders:
                    holder_name = holder_data["entity"]
                    # Case-insensitive substring matching (handles dropped 's', etc.)
                    if (entity1.lower() in holder_name.lower() or 
                        holder_name.lower() in entity1.lower() or
                        entity1.replace("'s", "").lower() == holder_name.replace("'s", "").lower()):
                        matched_entity = holder_name
                        entity1_interval = (holder_data["start_date"], holder_data["end_date"])
                        break
                
                if entity1_interval and entity1_interval[0]:
                    # Find all holders of role_query at org_query during entity1's interval
                    holders = knowledge_graph.get_role_holders_in_interval(
                        org_query, role_query, entity1_interval
                    )
                    
                    if holders:
                        # Store all matching entities (valid answers)
                        result["all_matches"] = [h["entity"] for h in holders]
                        
                        # If doc_text provided, check which entity is mentioned
                        best_holder = None
                        doc_entity_in_matches = False
                        
                        if doc_text:
                            for holder in holders:
                                entity_name = holder["entity"]
                                # Check if entity mentioned in document (fuzzy match)
                                # Handle "Clinton" matching "Bill Clinton", etc.
                                name_parts = entity_name.split()
                                if any(part.lower() in doc_text.lower() for part in name_parts if len(part) > 3):
                                    best_holder = holder
                                    doc_entity_in_matches = True
                                    break
                            
                            # Check if document mentions an entity NOT in matches (wrong answer)
                            # This would be someone who held the role but NOT during the overlap period
                            if not doc_entity_in_matches:
                                # Check if doc mentions any entity that's NOT in the valid matches
                                all_role_holders = knowledge_graph.get_all_role_holders(org_query, role_query)
                                for holder_data in all_role_holders:
                                    entity_name = holder_data["entity"]
                                    if entity_name not in result["all_matches"]:
                                        # This entity held the role but NOT during overlap period
                                        name_parts = entity_name.split()
                                        if any(part.lower() in doc_text.lower() for part in name_parts if len(part) > 3):
                                            # Document mentions wrong entity - score should be 0
                                            result["score"] = 0.0
                                            result["match_type"] = "NO_MATCH"
                                            result["matched_entity"] = None
                                            result["explanation"] = (
                                                f"{entity_name} held {role_query} of {org_query} but NOT during "
                                                f"{matched_entity}'s tenure as {entity1_role} of {entity1_org}"
                                            )
                                            return result
                        
                        # If no doc_text match or no doc provided, use highest overlap
                        if not best_holder:
                            best_holder = holders[0]  # Already sorted by overlap_years descending
                        
                        result["score"] = 1.0
                        result["match_type"] = "EXACT"
                        result["matched_entity"] = best_holder["entity"]
                        overlap_years = best_holder.get("overlap_years", 0)
                        result["explanation"] = (
                            f"{best_holder['entity']} held {role_query} of {org_query} "
                            f"during {matched_entity}'s tenure as {entity1_role} of {entity1_org} "
                            f"({overlap_years:.1f} years overlap)"
                        )
                    else:
                        result["explanation"] = f"No {role_query} of {org_query} found during {matched_entity}'s tenure"
                else:
                    result["explanation"] = f"{entity1} not found as {entity1_role} of {entity1_org} in graph"
            else:
                result["explanation"] = "Could not extract entity1's role/org from 'while' clause"
    
    return result


def compute_era_adjusted_score(graph_result: Dict, doc_acquired_date: Optional[datetime],
                               query_year: Optional[int]) -> float:
    """
    Adjust graph alignment score by document era matching.
    
    For continuity cases where same person held role across multiple years,
    prefer documents acquired closer to the query year.
    
    Args:
        graph_result: Result from compute_graph_alignment()
        doc_acquired_date: When document was acquired
        query_year: Year from query
        
    Returns:
        Adjusted score [0.0, 1.5]
        
    Example:
        Graph match = 1.0 (both docs match Andy Jassy as CEO in 2021)
        Doc A acquired 2021 → era match → score = 1.0 * 1.3 = 1.3
        Doc B acquired 2024 → era mismatch → score = 1.0 * 0.7 = 0.7
    """
    base_score = graph_result["score"]
    
    if base_score == 0.0:
        return 0.0
    
    # No era adjustment if no query year or doc date
    if not query_year or not doc_acquired_date:
        return base_score
    
    # Compute era gap
    doc_year = doc_acquired_date.year
    era_gap = abs(doc_year - query_year)
    
    # Era matching multiplier
    if era_gap == 0:
        era_mult = 1.3  # Same year as query → boost
    elif era_gap == 1:
        era_mult = 1.1  # 1 year off → slight boost
    elif era_gap <= 3:
        era_mult = 1.0  # 2-3 years → neutral
    elif era_gap <= 5:
        era_mult = 0.9  # 4-5 years → slight penalty
    else:
        era_mult = 0.7  # 5+ years → penalty
    
    adjusted_score = base_score * era_mult
    return adjusted_score


def test_graph_matching():
    """Test graph matching on example cases."""
    print("=" * 80)
    print("GRAPH MATCHING TESTS")
    print("=" * 80)
    print()
    
    # Build test graph
    graph = TemporalKnowledgeGraph()
    graph.add_role_fact("Jeff Bezos", "CEO", "Amazon", "1994-07-05", "2021-07-05")
    graph.add_role_fact("Andy Jassy", "CEO", "Amazon", "2021-07-05", None)
    graph.add_succession("Jeff Bezos", "Andy Jassy", "CEO", "Amazon", "2021-07-05")
    
    graph.add_role_fact("Steve Jobs", "CEO", "Apple", "1997-09-16", "2011-08-24")
    graph.add_role_fact("Tim Cook", "CEO", "Apple", "2011-08-24", None)
    graph.add_succession("Steve Jobs", "Tim Cook", "CEO", "Apple", "2011-08-24")
    
    # Test cases
    test_cases = [
        ("Who was CEO of Amazon in 2021?", "EXACT", "Andy Jassy"),
        ("Who was CEO of Amazon in 2020?", "EXACT", "Jeff Bezos"),
        ("Who was CEO of Amazon in 2024?", "EXACT", "Andy Jassy"),
        ("Who was CEO of Apple before Tim Cook?", "EXACT", "Steve Jobs"),
        ("Who became CEO of Amazon after Bezos?", "EXACT", "Andy Jassy"),
    ]
    
    for query, expected_match_type, expected_entity in test_cases:
        result = compute_graph_alignment(query, graph)
        
        print(f"Query: {query}")
        print(f"Result: {result['match_type']} (score={result['score']:.2f})")
        print(f"Entity: {result['matched_entity']}")
        print(f"Explanation: {result['explanation']}")
        
        # Validate
        match_ok = result["match_type"] == expected_match_type
        entity_ok = result["matched_entity"] == expected_entity
        
        if match_ok and entity_ok:
            print("✓ PASS")
        else:
            print(f"✗ FAIL: Expected {expected_match_type}/{expected_entity}")
        
        print()
    
    # Test era adjustment
    print("=" * 80)
    print("ERA ADJUSTMENT TEST (Jassy Continuity Case)")
    print("=" * 80)
    print()
    
    query = "Who was CEO of Amazon in 2021?"
    result = compute_graph_alignment(query, graph)
    
    print(f"Query: {query}")
    print(f"Graph match: {result['score']:.2f} ({result['matched_entity']})")
    print()
    
    # Doc A: acquired 2021 (era match)
    doc_a_date = datetime(2021, 7, 15)
    score_a = compute_era_adjusted_score(result, doc_a_date, 2021)
    print(f"Doc A (acquired 2021-07-15): score = {score_a:.2f} (era match → boost)")
    
    # Doc B: acquired 2024 (era mismatch)
    doc_b_date = datetime(2024, 1, 15)
    score_b = compute_era_adjusted_score(result, doc_b_date, 2021)
    print(f"Doc B (acquired 2024-01-15): score = {score_b:.2f} (era mismatch → penalty)")
    print()
    
    if score_a > score_b:
        print("✓ PASS: Doc A (correct) scores higher than Doc B (incorrect)")
    else:
        print("✗ FAIL: Doc B scored higher")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    test_graph_matching()
