# Phase 3 Deepseek Improvements - Implementation Summary

**Date**: 2026-03-12  
**Status**: ✅ All improvements implemented and tested

---

## Overview

Implemented Deepseek's three recommendations for Phase 3 (Knowledge Graph) improvements:

1. ✅ **Expand knowledge graph entities** - Cover CEOs and political leaders from manual benchmark failures
2. ✅ **Improve query-to-graph mapping** - Better recognition of graph-answerable queries
3. ✅ **Adaptive confidence threshold** - Flexible threshold based on document scores

**Bottom Line Results:**

- **Edge Cases Benchmark**: 8/15 → **9/15 (60.0%)** (+6.7 pts, +1 rescue)
- **Verified Benchmark**: **153/153 (100%)** (0 regressions)
- **Phase 3 Rescues**: 1/15 (6.7%) - temporal overlap "while" query

---

## Implementation Details

### 1. Knowledge Graph Entity Coverage ✅

**Status**: Already complete  
**Finding**: graph_facts.json already contained all requested entities:

- ✅ Amazon CEOs (Bezos, Jassy)
- ✅ Google CEOs (Page, Schmidt, Pichai)
- ✅ Netflix CEOs (Hastings, Sarandos)
- ✅ Twitter/X CEOs (Dorsey, Williams, Costolo, Musk)
- ✅ France Presidents (Chirac, Sarkozy, Hollande, Macron)
- ✅ US Presidents (Clinton, Bush, Obama, Trump, Biden)
- ✅ UK Prime Ministers (Thatcher, Major, Blair, Brown, Cameron)
- ✅ Apple CEOs (Jobs, Cook) - already tested in temporal joins

**Additional Data**: 62 nodes total in knowledge graph

---

### 2. Query-to-Graph Mapping Improvements ✅

#### A. Added "while" to Directional Keywords

**File**: `Phase 3/query_graph.py`

```python
DIRECTIONAL_KEYWORDS = {
    "before", "after", "since", "during", "until", "while"  # Added "while"
}
```

#### B. New Query Type: temporal_overlap

**File**: `Phase 3/query_graph.py`

```python
# Infer query type
if constraints["year"] and constraints["role"] and constraints["org"]:
    constraints["query_type"] = "specific_role_year"
elif constraints["directional"] == "while" and constraints["entity"]:
    constraints["query_type"] = "temporal_overlap"  # NEW
elif constraints["directional"] and constraints["entity"]:
    constraints["query_type"] = "succession"
```

#### C. Enhanced Role Extraction for "while" Queries

**File**: `Phase 3/query_graph.py`

For queries like "Who was the US President while Steve Jobs was the CEO of Apple?":

- Main question role: "President" (what we're asking about)
- While clause role: "CEO" (the condition)

**Implementation**: Split query at "while" keyword, extract role from main question only:

```python
if constraints["directional"] == "while":
    parts = query_lower.split("while")
    if len(parts) == 2:
        main_question = parts[0]  # "Who was the US President"
        while_clause = parts[1]   # "Steve Jobs was the CEO of Apple"

        # Extract role from main question only
        for role in ROLE_KEYWORDS:
            if role.lower() in main_question:
                constraints["role"] = role
                break
```

#### D. Temporal Overlap Query Handling

**File**: `Phase 3/graph_matching.py`

**Strategy**:

1. Parse "while X was Y of Z" to extract entity1, role1, org1
2. Use fuzzy name matching (handles "Steve Job" vs "Steve Jobs")
3. Find entity1's role interval using `get_role_interval()`
4. Find all holders of role_query during that interval using `get_role_holders_in_interval()`
5. Return all matching entities in `all_matches` field

**Key Code**:

```python
# Get entity1's interval (e.g., Steve Jobs as Apple CEO)
entity1_interval = get_role_interval(entity1_org, entity1_role, entity1)

# Find all Presidents during Jobs' tenure
holders = knowledge_graph.get_role_holders_in_interval(
    org_query, role_query, entity1_interval
)

result["all_matches"] = [h["entity"] for h in holders]
# Returns: ['George W. Bush', 'Bill Clinton', 'Barack Obama']
```

#### E. Document-Aware Entity Matching

**File**: `Phase 3/graph_matching.py`

**Problem**: Multiple valid answers (Bush, Clinton, Obama), but documents only mention one each

**Solution**: Check document text for entity mentions, prefer entities that appear in the document:

```python
if doc_text:
    for holder in holders:
        entity_name = holder["entity"]
        name_parts = entity_name.split()
        if any(part.lower() in doc_text.lower() for part in name_parts if len(part) > 3):
            best_holder = holder
            doc_entity_in_matches = True
            break
```

#### F. Wrong Entity Detection

**File**: `Phase 3/graph_matching.py`

**Problem**: Trump document mentions "Donald Trump" but Trump was NOT President during Jobs' tenure

**Solution**: Check if document mentions an entity that's NOT in the valid overlap matches:

```python
# Check if doc mentions any entity that's NOT in the valid matches
all_role_holders = knowledge_graph.get_all_role_holders(org_query, role_query)
for holder_data in all_role_holders:
    entity_name = holder_data["entity"]
    if entity_name not in result["all_matches"]:
        # This entity held the role but NOT during overlap period
        if entity_name in doc_text:
            # Document mentions wrong entity - score should be 0
            result["score"] = 0.0
            result["match_type"] = "NO_MATCH"
            return result
```

**Example**:

- Clinton document → score 1.0 (Clinton in overlap)
- Trump document → score 0.0 (Trump NOT in overlap)

#### G. Organization Name Normalization

**File**: `Phase 3/graph_matching.py`

Handle NER variations:

```python
if org_query_lower in ["us", "usa", "u.s.", "u.s.a.", "united states"]:
    org_query = "United States"
elif org_query_lower in ["uk", "u.k.", "united kingdom", "britain"]:
    org_query = "United Kingdom"
```

---

### 3. Adaptive Confidence Threshold ✅

**File**: `Phase 4/evaluate_phase4_on_phase2.py`

**Previous Behavior**: Hardcoded threshold of 0.8 (too strict)

```python
# OLD CODE
if doc1_graph_score >= 0.8 or doc2_graph_score >= 0.8:
    # Apply graph override
```

**New Behavior**: Three-tier adaptive threshold:

```python
high_confidence_threshold = 0.8
medium_confidence_threshold = 0.5

if better_graph_score >= high_confidence_threshold:
    # High confidence (≥0.8): Always use graph (EXACT or strong NEAR_MATCH)
    should_override = True

elif better_graph_score >= medium_confidence_threshold:
    # Medium confidence (0.5-0.8): Use graph ONLY if it beats BOTH document scores
    # This is adaptive - graph wins if more confident than epistemic modulation
    if better_graph_score > doc1_sim_phase4 and better_graph_score > doc2_sim_phase4:
        should_override = True

# Low confidence (<0.5): Ignore graph, use Phase 4 scores
```

**Rationale**:

- High confidence graph matches (≥0.8) always override (structural facts > embeddings)
- Medium confidence (0.5-0.8) only override if graph beats both document scores
- Low confidence (<0.5) ignored entirely (insufficient structural evidence)

**Updated Help Text**:

```
Phase 3: Graph override (role queries with adaptive confidence)
  - High confidence (≥0.8): Always use graph
  - Medium confidence (0.5-0.8): Use if beats both document scores
  - Low confidence (<0.5): Ignore, use Phase 4
```

---

## Files Modified

### New Files Created:

1. `Phase 3/test_while_query.py` - Debug script for temporal overlap queries
2. `Phase 3/test_doc_matching.py` - Test document-aware entity matching
3. `PHASE3_DEEPSEEK_IMPROVEMENTS.md` - This file

### Files Modified:

1. **Phase 3/query_graph.py** (3 changes):
   - Added "while" to DIRECTIONAL_KEYWORDS
   - Added temporal_overlap query type
   - Enhanced role extraction for "while" queries (split at "while", parse main question only)

2. **Phase 3/graph_matching.py** (5 changes):
   - Added doc_text parameter to compute_graph_alignment()
   - Added all_matches field to result dict
   - Implemented temporal overlap query handling (~70 lines)
   - Added document-aware entity matching
   - Added wrong entity detection (score 0.0 for entities not in overlap period)
   - Added organization name normalization (US → United States, etc.)

3. **Phase 4/evaluate_phase4_on_phase2.py** (2 changes):
   - Implemented adaptive confidence threshold (3-tier system)
   - Updated help text to explain adaptive thresholding
   - Pass doc_text to compute_graph_alignment()

---

## Test Results

### Edge Cases Benchmark (15 cases)

**Before Improvements**:

- Phase 2: 7/15 (46.7%)
- Phase 4: 8/15 (53.3%)
- Phase 3: 8/15 (53.3%) - no rescues

**After Improvements**:

- Phase 2: 7/15 (46.7%)
- Phase 4: 8/15 (53.3%)
- **Phase 3: 9/15 (60.0%)** ✅ (+1 rescue)

**Phase 3 Rescued Cases**:

- **unnamed_6**: "Who was the US President while Steve Jobs was the CEO of Apple?"
  - Expected: clinton_1998 (Bill Clinton)
  - Phase 2/4: trump_2018 (WRONG)
  - Phase 3: clinton_1998 (CORRECT) ✅

**Rescue Mechanism**:

1. Query identified as temporal_overlap (has "while" + entity)
2. Extracted: role="President", org="United States", entity="Steve Job" (NER drop 's')
3. Fuzzy matched to "Steve Jobs"
4. Found Jobs' Apple CEO tenure: 1997-09-16 to 2011-08-24
5. Queried US Presidents during that interval: Bush (8.0 yrs), Clinton (3.35 yrs), Obama (2.59 yrs)
6. Clinton doc mentions "Bill Clinton" → matched → score 1.0
7. Trump doc mentions "Donald Trump" → NOT in overlap → score 0.0
8. Graph override: Clinton wins (1.0 > 0.0)

### Verified Specific Date Benchmark (153 cases)

**After Improvements**:

- Phase 2: 153/153 (100.0%)
- Phase 4: 153/153 (100.0%)
- Phase 3: 153/153 (100.0%) ✅ (0 regressions)

**Confirmation**: Phase 3 improvements do not break existing functionality.

---

## Production Recommendations

### Deployment Strategy

1. **Graph Population**: Current 62 nodes sufficient for demo, expand to 500+ for production:
   - Add all S&P 500 CEOs
   - Add all world leaders (G20 countries)
   - Add key historical figures (founders, inventors, scientists)

2. **Query Parser Integration**: Connect temporal join methods to natural language queries:
   - "Who was X while Y was Z?" → temporal_overlap query type
   - "Who was X before/after Y?" → succession query type
   - "Who was X during timeframe T?" → interval query type

3. **Monitoring**:
   - Track graph override activation rate (expected: 5-10% of queries)
   - Monitor temporal_overlap vs succession vs specific_role_year distribution
   - Alert if wrong entity detection rate > 10%

4. **Testing**:
   - Add role succession benchmark with "before", "after", "while" queries
   - Stress test fuzzy name matching (handle nicknames, abbreviations)
   - Test organization name variations (US vs USA vs United States)

### Known Limitations

1. **Document-centric**: Graph override can only select between provided documents, not inject third answers
   - Example: If both docs are wrong, graph can't override with correct answer
   - Workaround: Expand document pool before retrieval

2. **NER Dependency**: Relies on spaCy NER for entity extraction
   - Handles some errors (fuzzy matching for dropped 's')
   - May miss entities if NER classification wrong (e.g., company name tagged as PERSON)

3. **Regex Parsing**: "while" clause parsing uses simple regex
   - Works for standard patterns: "while X was Y of Z"
   - May fail on complex syntax: "while X, who was Y, served as Z"

---

## Future Enhancements

1. **Multi-entity "while" queries**: "Who was President while Jobs was CEO and Gates was at Microsoft?"
   - Requires intersection of multiple temporal intervals
   - Can use existing find_temporal_overlap() method

2. **Fuzzy temporal queries**: "Who was President around the time Jobs returned to Apple?"
   - Parse fuzzy time expressions
   - Map to approximate intervals (±2 years)

3. **Negative queries**: "Who was President but NOT while Jobs was CEO?"
   - Set difference operations on time intervals
   - Requires interval algebra

4. **Temporal aggregation**: "Who spent the most time as President during Jobs' Apple CEO tenure?"
   - Already supported via overlap_years field
   - Just needs query type detection

---

## Conclusion

All three Deepseek recommendations successfully implemented:

✅ **Entities expanded**: Already covered in graph (62 nodes)  
✅ **Query mapping improved**: "while" queries now handled via temporal_overlap query type  
✅ **Adaptive threshold**: 3-tier system (high/medium/low confidence)

**Impact**: +1 rescue on edge cases benchmark (53.3% → 60.0%), 0 regressions on verified benchmark (100% maintained).

**Key Innovation**: Document-aware entity matching enables Phase 3 to correctly score documents based on whether mentioned entities are valid answers for the temporal overlap period.
