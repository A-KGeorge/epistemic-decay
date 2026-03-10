"""
Wikidata SPARQL Integration for Current Answer Lookup

Queries Wikidata to find current values for temporal facts:
- Political positions (presidents, prime ministers)
- Institutional leadership (CEOs, directors)
- Statistical facts (population, counts)
- Geographic facts (capitals, locations)
"""

import requests
import json
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import time


class WikidataLookup:
    """
    Query Wikidata for current fact values using SPARQL.
    """
    
    def __init__(self, user_agent: str = "TemporalDecayFramework/1.0"):
        self.endpoint = "https://query.wikidata.org/sparql"
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "application/sparql-results+json"
        }
        self.rate_limit_delay = 1.0  # seconds between requests
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Enforce rate limiting to be respectful to Wikidata."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def _query(self, sparql: str) -> Optional[Dict]:
        """
        Execute SPARQL query against Wikidata.
        
        Args:
            sparql: SPARQL query string
        
        Returns:
            Query results as dict, or None on error
        """
        self._rate_limit()
        
        try:
            response = requests.get(
                self.endpoint,
                params={"query": sparql},
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Wikidata query error: {e}")
            return None
    
    def get_current_head_of_state(self, country_qid: str) -> Optional[Tuple[str, datetime]]:
        """
        Get current head of state/government for a country.
        
        Args:
            country_qid: Wikidata Q-ID (e.g., "Q30" for USA)
        
        Returns:
            (name, start_date) or None
        """
        sparql = f"""
        SELECT ?holderLabel ?start WHERE {{
          wd:{country_qid} p:P35 ?statement .
          ?statement ps:P35 ?holder .
          ?statement pq:P580 ?start .
          FILTER NOT EXISTS {{ ?statement pq:P582 ?end }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
        }}
        ORDER BY DESC(?start)
        LIMIT 1
        """
        
        result = self._query(sparql)
        if result and result.get("results", {}).get("bindings"):
            binding = result["results"]["bindings"][0]
            name = binding["holderLabel"]["value"]
            start_str = binding["start"]["value"]
            start_date = datetime.fromisoformat(start_str.replace("Z", ""))
            return name, start_date
        
        return None
    
    def get_current_head_of_government(self, country_qid: str) -> Optional[Tuple[str, datetime]]:
        """
        Get current head of government (Prime Minister, Chancellor, etc.).
        
        Args:
            country_qid: Wikidata Q-ID
        
        Returns:
            (name, start_date) or None
        """
        sparql = f"""
        SELECT ?holderLabel ?start WHERE {{
          wd:{country_qid} p:P6 ?statement .
          ?statement ps:P6 ?holder .
          ?statement pq:P580 ?start .
          FILTER NOT EXISTS {{ ?statement pq:P582 ?end }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
        }}
        ORDER BY DESC(?start)
        LIMIT 1
        """
        
        result = self._query(sparql)
        if result and result.get("results", {}).get("bindings"):
            binding = result["results"]["bindings"][0]
            name = binding["holderLabel"]["value"]
            start_str = binding["start"]["value"]
            start_date = datetime.fromisoformat(start_str.replace("Z", ""))
            return name, start_date
        
        return None
    
    def get_current_ceo(self, company_qid: str) -> Optional[Tuple[str, datetime]]:
        """
        Get current CEO of a company.
        
        Args:
            company_qid: Wikidata Q-ID (e.g., "Q312" for Apple)
        
        Returns:
            (name, start_date) or None
        """
        sparql = f"""
        SELECT ?holderLabel ?start WHERE {{
          wd:{company_qid} p:P169 ?statement .
          ?statement ps:P169 ?holder .
          OPTIONAL {{ ?statement pq:P580 ?start }}
          FILTER NOT EXISTS {{ ?statement pq:P582 ?end }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
        }}
        ORDER BY DESC(?start)
        LIMIT 1
        """
        
        result = self._query(sparql)
        if result and result.get("results", {}).get("bindings"):
            binding = result["results"]["bindings"][0]
            name = binding["holderLabel"]["value"]
            
            if "start" in binding:
                start_str = binding["start"]["value"]
                start_date = datetime.fromisoformat(start_str.replace("Z", ""))
            else:
                start_date = datetime(2020, 1, 1)  # fallback
            
            return name, start_date
        
        return None
    
    def get_population(self, place_qid: str) -> Optional[Tuple[str, datetime]]:
        """
        Get most recent population figure for a place.
        
        Args:
            place_qid: Wikidata Q-ID
        
        Returns:
            (population_string, date) or None
        """
        sparql = f"""
        SELECT ?population ?time WHERE {{
          wd:{place_qid} p:P1082 ?statement .
          ?statement ps:P1082 ?population .
          ?statement pq:P585 ?time .
        }}
        ORDER BY DESC(?time)
        LIMIT 1
        """
        
        result = self._query(sparql)
        if result and result.get("results", {}).get("bindings"):
            binding = result["results"]["bindings"][0]
            pop_value = int(binding["population"]["value"])
            time_str = binding["time"]["value"]
            pop_date = datetime.fromisoformat(time_str.replace("Z", ""))
            
            # Format population
            if pop_value >= 1_000_000:
                pop_str = f"{pop_value / 1_000_000:.1f} million"
            elif pop_value >= 1_000:
                pop_str = f"{pop_value / 1_000:.0f} thousand"
            else:
                pop_str = str(pop_value)
            
            return pop_str, pop_date
        
        return None
    
    def search_entity(self, name: str, entity_type: str = None) -> Optional[str]:
        """
        Search for entity QID by name.
        
        Args:
            name: Entity name (e.g., "United States", "Apple Inc.")
            entity_type: Optional type hint ("country", "company", "city")
        
        Returns:
            Wikidata QID or None
        """
        # Use Wikidata search API
        search_url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbsearchentities",
            "search": name,
            "language": "en",
            "format": "json",
            "limit": 5
        }
        
        self._rate_limit()
        
        try:
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("search"):
                # Take first result (could be improved with type filtering)
                return data["search"][0]["id"]
        except requests.exceptions.RequestException as e:
            print(f"Entity search error: {e}")
        
        return None


# Entity mapping cache (to reduce API calls)
ENTITY_QID_CACHE = {
    # Countries
    "united states": "Q30",
    "usa": "Q30",
    "us": "Q30",
    "united kingdom": "Q145",
    "uk": "Q145",
    "britain": "Q145",
    "france": "Q142",
    "germany": "Q183",
    "canada": "Q16",
    "japan": "Q17",
    "china": "Q148",
    "india": "Q668",
    "russia": "Q159",
    "brazil": "Q155",
    "australia": "Q408",
    
    # Companies
    "apple": "Q312",
    "apple inc": "Q312",
    "microsoft": "Q2283",
    "google": "Q95",
    "amazon": "Q3884",
    "tesla": "Q478214",
    "facebook": "Q380",
    "meta": "Q380",
    "twitter": "Q918",
    "netflix": "Q907311",
    "intel": "Q248",
    
    # Cities
    "tokyo": "Q1490",
    "new york": "Q60",
    "london": "Q84",
    "paris": "Q90",
    "beijing": "Q956",
    "delhi": "Q987",
    "shanghai": "Q8686",
    "mumbai": "Q1156",
    "moscow": "Q649",
}


def lookup_current_answer(question: str, historical_answer: str) -> Optional[Dict]:
    """
    High-level function to lookup current answer for a temporal question.
    
    Args:
        question: "Who was the US President in 1998?"
        historical_answer: "Bill Clinton"
    
    Returns:
        {
            "current_answer": "Donald Trump",
            "acquired_date": datetime(...),
            "source": "wikidata",
            "qid": "Q30"
        }
    """
    wikidata = WikidataLookup()
    question_lower = question.lower()
    
    # Detect entity and attribute
    entity_name = None
    attribute = None
    qid = None
    
    # Extract entity
    for name, cached_qid in ENTITY_QID_CACHE.items():
        if name in question_lower:
            entity_name = name
            qid = cached_qid
            break
    
    # Extract attribute type
    if "president" in question_lower and "prime minister" not in question_lower:
        attribute = "president"
    elif "prime minister" in question_lower or " pm " in question_lower:
        attribute = "prime_minister"
    elif "chancellor" in question_lower:
        attribute = "chancellor"
    elif "ceo" in question_lower or "chief executive" in question_lower:
        attribute = "ceo"
    elif "population" in question_lower:
        attribute = "population"
    
    # Query Wikidata based on attribute
    if qid and attribute:
        if attribute in ["president", "prime_minister", "chancellor"]:
            # Try head of government first (more common)
            result = wikidata.get_current_head_of_government(qid)
            if not result:
                # Fall back to head of state
                result = wikidata.get_current_head_of_state(qid)
            
            if result:
                name, date = result
                return {
                    "current_answer": name,
                    "acquired_date": date,
                    "source": "wikidata",
                    "qid": qid,
                    "attribute": attribute
                }
        
        elif attribute == "ceo":
            result = wikidata.get_current_ceo(qid)
            if result:
                name, date = result
                return {
                    "current_answer": name,
                    "acquired_date": date,
                    "source": "wikidata",
                    "qid": qid,
                    "attribute": attribute
                }
        
        elif attribute == "population":
            result = wikidata.get_population(qid)
            if result:
                pop_str, date = result
                return {
                    "current_answer": pop_str,
                    "acquired_date": date,
                    "source": "wikidata",
                    "qid": qid,
                    "attribute": attribute
                }
    
    return None


def test_wikidata_lookup():
    """Test Wikidata integration with sample queries."""
    print("=" * 80)
    print("WIKIDATA INTEGRATION TEST")
    print("=" * 80)
    print()
    
    test_cases = [
        ("Who was the US President in 1998?", "Bill Clinton"),
        ("Who was the UK Prime Minister in 2010?", "David Cameron"),
        ("Who was the CEO of Apple in 2005?", "Steve Jobs"),
        ("What was the population of Tokyo in 2010?", "13.2 million"),
        ("Who was the French President in 2000?", "Jacques Chirac"),
    ]
    
    for question, historical in test_cases:
        print(f"Question: {question}")
        print(f"  Historical: {historical}")
        
        result = lookup_current_answer(question, historical)
        
        if result:
            print(f"  Current:    {result['current_answer']}")
            print(f"  Date:       {result['acquired_date'].strftime('%Y-%m-%d')}")
            print(f"  Source:     {result['source']} ({result['qid']})")
            print(f"  ✓ SUCCESS")
        else:
            print(f"  ✗ LOOKUP FAILED")
        
        print()
    
    print("=" * 80)


if __name__ == "__main__":
    test_wikidata_lookup()
