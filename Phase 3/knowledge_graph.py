"""
Phase 3: Temporal Knowledge Graph

NetworkX-based graph structure for storing and querying temporal entity-role relationships.
Solves continuity and small-gap failures where semantic similarity is insufficient.

Key concepts:
- Entities: People, organizations
- Roles: Positions held by entities (with temporal validity intervals)
- Succession: Temporal ordering of role holders

Example:
    graph = TemporalKnowledgeGraph()
    graph.add_role_fact("Andy Jassy", "CEO", "Amazon", "2021-07-05", None)
    holder = graph.get_role_holder("Amazon", "CEO", 2021)  # Returns "Andy Jassy"
"""

import networkx as nx
from datetime import datetime
from typing import Optional, List, Dict, Tuple
import json


class TemporalKnowledgeGraph:
    """
    Temporal knowledge graph for entity-role-organization relationships.
    
    Graph structure:
    - Entity nodes: (name, type=PERSON/ORG)
    - Role nodes: (entity, role, org, start_date, end_date)
    - Edges: HOLDS_ROLE, SUCCEEDED_BY, FOUNDED_BY
    
    Temporal reasoning:
    - All roles have validity intervals [start_date, end_date]
    - end_date=None means current (still valid)
    - Query: "Who held role R at org O in year Y?" → find role where Y ∈ [start, end]
    """
    
    def __init__(self):
        """Initialize empty directed graph."""
        self.graph = nx.DiGraph()
        
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse date string to datetime object.
        
        Args:
            date_str: ISO format date string (YYYY-MM-DD) or None
            
        Returns:
            datetime object or None if date_str is None
        """
        if date_str is None or date_str == "None" or date_str == "null":
            return None
        
        if isinstance(date_str, datetime):
            return date_str
            
        # Handle ISO format with time (YYYY-MM-DDTHH:MM:SSZ)
        if 'T' in date_str:
            date_str = date_str.split('T')[0]
            
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            # Try year-only format
            try:
                return datetime.strptime(date_str, "%Y")
            except ValueError:
                raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD or YYYY")
    
    def _date_to_str(self, date: Optional[datetime]) -> Optional[str]:
        """Convert datetime to ISO string or None."""
        if date is None:
            return None
        return date.strftime("%Y-%m-%d")
    
    def add_entity(self, name: str, entity_type: str = "PERSON"):
        """
        Add entity node to graph.
        
        Args:
            name: Entity name (e.g., "Andy Jassy")
            entity_type: PERSON or ORG
        """
        if not self.graph.has_node(name):
            self.graph.add_node(name, type=entity_type)
    
    def add_role_fact(self, entity: str, role: str, org: str, 
                     start_date: str, end_date: Optional[str] = None):
        """
        Add role fact: entity held role at org from start_date to end_date.
        
        Args:
            entity: Person name (e.g., "Andy Jassy")
            role: Position title (e.g., "CEO")
            org: Organization name (e.g., "Amazon")
            start_date: When role began (YYYY-MM-DD)
            end_date: When role ended (YYYY-MM-DD) or None if current
            
        Example:
            graph.add_role_fact("Andy Jassy", "CEO", "Amazon", "2021-07-05", None)
        """
        # Parse dates
        start = self._parse_date(start_date)
        end = self._parse_date(end_date)
        
        # Validate temporal consistency
        if start and end and end < start:
            raise ValueError(f"End date {end_date} is before start date {start_date}")
        
        # Add entity and org nodes if they don't exist
        self.add_entity(entity, "PERSON")
        self.add_entity(org, "ORG")
        
        # Create role node ID: "entity/role/org"
        role_id = f"{entity}/{role}/{org}"
        
        # Add role node with temporal metadata
        self.graph.add_node(role_id, 
                          type="ROLE",
                          entity=entity,
                          role=role,
                          org=org,
                          start_date=start,
                          end_date=end)
        
        # Add edges
        self.graph.add_edge(entity, role_id, type="HOLDS_ROLE")
        self.graph.add_edge(org, role_id, type="HAS_ROLE_HOLDER")
    
    def add_succession(self, predecessor_entity: str, successor_entity: str,
                      role: str, org: str, transition_date: str):
        """
        Add succession edge: predecessor → successor for same role.
        
        Args:
            predecessor_entity: Previous role holder (e.g., "Jeff Bezos")
            successor_entity: New role holder (e.g., "Andy Jassy")  
            role: Position (e.g., "CEO")
            org: Organization (e.g., "Amazon")
            transition_date: When succession occurred (YYYY-MM-DD)
            
        Example:
            graph.add_succession("Jeff Bezos", "Andy Jassy", "CEO", "Amazon", "2021-07-05")
        """
        pred_role_id = f"{predecessor_entity}/{role}/{org}"
        succ_role_id = f"{successor_entity}/{role}/{org}"
        
        if not self.graph.has_node(pred_role_id):
            raise ValueError(f"Predecessor role not found: {pred_role_id}")
        if not self.graph.has_node(succ_role_id):
            raise ValueError(f"Successor role not found: {succ_role_id}")
        
        # Add succession edge
        transition = self._parse_date(transition_date)
        self.graph.add_edge(pred_role_id, succ_role_id, 
                           type="SUCCEEDED_BY",
                           date=transition)
    
    def get_role_holder(self, org: str, role: str, year: int) -> Optional[str]:
        """
        Find who held a specific role at an organization in a given year.
        
        Args:
            org: Organization name (e.g., "Amazon")
            role: Position title (e.g., "CEO")
            year: Query year (e.g., 2021)
            
        Returns:
            Entity name if found, None otherwise
            
        Note:
            Uses end of year (Dec 31) as query point to handle mid-year transitions.
            E.g., "Who was CEO in 2021?" when transition was July 2021 returns 
            the person who held role at end of 2021.
            
        Example:
            holder = graph.get_role_holder("Amazon", "CEO", 2021)
            # Returns "Andy Jassy" (even though Bezos held it Jan-July)
        """
        # Use end of year as query point (Dec 31) to handle mid-year transitions
        query_date = datetime(year, 12, 31)
        
        # Find all role nodes for this org
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            
            if node_data.get("type") != "ROLE":
                continue
            
            if node_data.get("org") != org or node_data.get("role") != role:
                continue
            
            # Check if query_date is within validity interval
            start = node_data.get("start_date")
            end = node_data.get("end_date")
            
            if start is None:
                continue
            
            # Check if year falls in [start, end]
            if start <= query_date:
                if end is None or query_date <= end:
                    return node_data.get("entity")
        
        return None
    
    def get_all_role_holders(self, org: str, role: str) -> List[Dict]:
        """
        Get all entities who have held a role at an organization (ordered by date).
        
        Args:
            org: Organization name
            role: Position title
            
        Returns:
            List of dicts with {entity, start_date, end_date} sorted by start_date
        """
        holders = []
        
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            
            if node_data.get("type") != "ROLE":
                continue
                
            if node_data.get("org") == org and node_data.get("role") == role:
                holders.append({
                    "entity": node_data.get("entity"),
                    "start_date": node_data.get("start_date"),
                    "end_date": node_data.get("end_date"),
                    "role_id": node_id
                })
        
        # Sort by start_date
        holders.sort(key=lambda x: x["start_date"] if x["start_date"] else datetime.min)
        return holders
    
    def get_succession_chain(self, org: str, role: str) -> List[str]:
        """
        Get ordered succession chain for a role at an organization.
        
        Args:
            org: Organization name
            role: Position title
            
        Returns:
            List of entity names in chronological order
            
        Example:
            chain = graph.get_succession_chain("Amazon", "CEO")
            # Returns ["Jeff Bezos", "Andy Jassy"]
        """
        holders = self.get_all_role_holders(org, role)
        return [h["entity"] for h in holders]
    
    def validate_temporal_consistency(self) -> List[str]:
        """
        Check for temporal inconsistencies in the graph.
        
        Returns:
            List of error messages (empty if consistent)
            
        Checks:
        - No overlapping role intervals (same person can't hold same role twice)
        - Start dates before end dates
        - Succession edges match role intervals
        """
        errors = []
        
        # Check each role node
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            
            if node_data.get("type") != "ROLE":
                continue
            
            start = node_data.get("start_date")
            end = node_data.get("end_date")
            
            # Check start < end
            if start and end and end < start:
                errors.append(f"Role {node_id} has end_date before start_date")
        
        # Check for overlapping intervals within same org/role
        role_groups = {}
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            
            if node_data.get("type") != "ROLE":
                continue
            
            key = (node_data.get("org"), node_data.get("role"))
            if key not in role_groups:
                role_groups[key] = []
            
            role_groups[key].append({
                "id": node_id,
                "entity": node_data.get("entity"),
                "start": node_data.get("start_date"),
                "end": node_data.get("end_date")
            })
        
        # Check for overlaps within each group
        for (org, role), roles in role_groups.items():
            for i, r1 in enumerate(roles):
                for r2 in roles[i+1:]:
                    # Check if intervals overlap
                    if self._intervals_overlap(r1["start"], r1["end"], r2["start"], r2["end"]):
                        errors.append(
                            f"Overlapping roles at {org}/{role}: "
                            f"{r1['entity']} and {r2['entity']}"
                        )
        
        return errors
    
    def _intervals_overlap(self, start1, end1, start2, end2) -> bool:
        """
        Check if two date intervals overlap.
        
        Intervals [start1, end1) and [start2, end2) overlap if they share any common time.
        Uses half-open intervals: start is inclusive, end is exclusive.
        This allows valid succession: Role A ends 2010-01-01, Role B starts 2010-01-01.
        """
        if start1 is None or start2 is None:
            return False
        
        # end=None means current (still ongoing)
        # For overlap check, treat None as far future
        end1_check = end1 if end1 else datetime(9999, 12, 31)
        end2_check = end2 if end2 else datetime(9999, 12, 31)
        
        # Intervals overlap if: start1 < end2 AND start2 < end1 (strict inequality)
        # This allows exact boundary matching (succession without overlap)
        return start1 < end2_check and start2 < end1_check
    
    def to_dict(self) -> Dict:
        """
        Export graph to dictionary format for JSON serialization.
        
        Returns:
            Dict with nodes and edges
        """
        nodes = []
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id].copy()
            node_data["id"] = node_id
            
            # Convert datetime objects to strings
            if "start_date" in node_data:
                node_data["start_date"] = self._date_to_str(node_data["start_date"])
            if "end_date" in node_data:
                node_data["end_date"] = self._date_to_str(node_data["end_date"])
            
            nodes.append(node_data)
        
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edge_data = data.copy()
            edge_data["source"] = u
            edge_data["target"] = v
            
            # Convert datetime objects to strings
            if "date" in edge_data:
                edge_data["date"] = self._date_to_str(edge_data["date"])
            
            edges.append(edge_data)
        
        return {"nodes": nodes, "edges": edges}
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TemporalKnowledgeGraph':
        """
        Load graph from dictionary format.
        
        Args:
            data: Dict with nodes and edges
            
        Returns:
            TemporalKnowledgeGraph instance
        """
        graph = cls()
        
        # Add nodes
        for node_data in data["nodes"]:
            node_id = node_data["id"]
            attrs = {k: v for k, v in node_data.items() if k != "id"}
            
            # Convert date strings back to datetime
            if "start_date" in attrs and attrs["start_date"]:
                attrs["start_date"] = graph._parse_date(attrs["start_date"])
            if "end_date" in attrs and attrs["end_date"]:
                attrs["end_date"] = graph._parse_date(attrs["end_date"])
            
            graph.graph.add_node(node_id, **attrs)
        
        # Add edges
        for edge_data in data["edges"]:
            source = edge_data["source"]
            target = edge_data["target"]
            attrs = {k: v for k, v in edge_data.items() 
                    if k not in ["source", "target"]}
            
            # Convert date strings back to datetime
            if "date" in attrs and attrs["date"]:
                attrs["date"] = graph._parse_date(attrs["date"])
            
            graph.graph.add_edge(source, target, **attrs)
        
        return graph
    
    # ===== TEMPORAL JOIN METHODS (Deepseek recommendation) =====
    
    def get_role_interval(self, org: str, role: str, entity: str) -> Optional[Tuple[datetime, Optional[datetime]]]:
        """
        Get the time interval when a specific entity held a role at an organization.
        
        Args:
            org: Organization name (e.g., "Apple")
            role: Position title (e.g., "CEO")
            entity: Person name (e.g., "Steve Jobs")
            
        Returns:
            Tuple of (start_date, end_date) or None if not found
            end_date is None if role is current
            
        Example:
            interval = graph.get_role_interval("Apple", "CEO", "Steve Jobs")
            # Returns (datetime(1997, 7, 9), datetime(2011, 8, 24))
        """
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            
            if node_data.get("type") != "ROLE":
                continue
            
            if (node_data.get("org") == org and 
                node_data.get("role") == role and 
                node_data.get("entity") == entity):
                return (node_data.get("start_date"), node_data.get("end_date"))
        
        return None
    
    def get_role_holders_in_interval(self, org: str, role: str, 
                                     interval: Tuple[datetime, datetime]) -> List[Dict]:
        """
        Find all entities who held a role during a specified time interval.
        
        This enables temporal joins: e.g., "Who was US President while Steve Jobs was CEO?"
        
        Args:
            org: Organization name (e.g., "United States")
            role: Position title (e.g., "President")
            interval: Tuple of (start_date, end_date) to query
            
        Returns:
            List of dicts with {entity, start_date, end_date, overlap_years}
            sorted by overlap duration (longest first)
            
        Example:
            jobs_interval = graph.get_role_interval("Apple", "CEO", "Steve Jobs")
            presidents = graph.get_role_holders_in_interval("United States", "President", jobs_interval)
            # Returns: [
            #   {"entity": "George W. Bush", "start": 2001-01-20, "end": 2009-01-20, "overlap_years": 8},
            #   {"entity": "Bill Clinton", "start": 1993-01-20, "end": 2001-01-20, "overlap_years": 4},
            #   {"entity": "Barack Obama", "start": 2009-01-20, "end": 2017-01-20, "overlap_years": 2}
            # ]
        """
        query_start, query_end = interval
        
        if query_start is None:
            return []
        
        # Treat None as far future for query end
        query_end_check = query_end if query_end else datetime(9999, 12, 31)
        
        holders = []
        
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            
            if node_data.get("type") != "ROLE":
                continue
                
            if node_data.get("org") != org or node_data.get("role") != role:
                continue
            
            role_start = node_data.get("start_date")
            role_end = node_data.get("end_date")
            
            if role_start is None:
                continue
            
            # Treat None as far future for role end
            role_end_check = role_end if role_end else datetime(9999, 12, 31)
            
            # Check for overlap: role starts before query ends AND role ends after query starts
            if role_start < query_end_check and role_end_check > query_start:
                # Calculate overlap duration
                overlap_start = max(role_start, query_start)
                overlap_end = min(role_end_check, query_end_check)
                overlap_days = (overlap_end - overlap_start).days
                overlap_years = overlap_days / 365.25
                
                holders.append({
                    "entity": node_data.get("entity"),
                    "start_date": role_start,
                    "end_date": role_end,
                    "overlap_start": overlap_start,
                    "overlap_end": overlap_end,
                    "overlap_years": round(overlap_years, 2),
                    "overlap_days": overlap_days
                })
        
        # Sort by overlap duration (longest first)
        holders.sort(key=lambda x: x["overlap_days"], reverse=True)
        return holders
    
    def find_temporal_overlap(self, role1_org: str, role1_name: str, role1_entity: str,
                             role2_org: str, role2_name: str, role2_entity: str) -> Optional[Dict]:
        """
        Find the temporal overlap between two specific roles.
        
        Args:
            role1_org: Organization for first role
            role1_name: Position title for first role
            role1_entity: Person holding first role
            role2_org: Organization for second role
            role2_name: Position title for second role
            role2_entity: Person holding second role
            
        Returns:
            Dict with overlap info or None if no overlap
            
        Example:
            overlap = graph.find_temporal_overlap(
                "Apple", "CEO", "Steve Jobs",
                "United States", "President", "Barack Obama"
            )
            # Returns: {
            #   "overlap_start": datetime(2009, 1, 20),
            #   "overlap_end": datetime(2011, 8, 24),
            #   "overlap_years": 2.6,
            #   "role1_interval": (datetime(1997, 7, 9), datetime(2011, 8, 24)),
            #   "role2_interval": (datetime(2009, 1, 20), datetime(2017, 1, 20))
            # }
        """
        interval1 = self.get_role_interval(role1_org, role1_name, role1_entity)
        interval2 = self.get_role_interval(role2_org, role2_name, role2_entity)
        
        if not interval1 or not interval2:
            return None
        
        start1, end1 = interval1
        start2, end2 = interval2
        
        if start1 is None or start2 is None:
            return None
        
        # Treat None as far future
        end1_check = end1 if end1 else datetime(9999, 12, 31)
        end2_check = end2 if end2 else datetime(9999, 12, 31)
        
        # Check for overlap
        if start1 >= end2_check or start2 >= end1_check:
            return None  # No overlap
        
        # Calculate overlap
        overlap_start = max(start1, start2)
        overlap_end = min(end1_check, end2_check)
        overlap_days = (overlap_end - overlap_start).days
        overlap_years = overlap_days / 365.25
        
        return {
            "overlap_start": overlap_start,
            "overlap_end": overlap_end if overlap_end != datetime(9999, 12, 31) else None,
            "overlap_years": round(overlap_years, 2),
            "overlap_days": overlap_days,
            "role1_interval": interval1,
            "role2_interval": interval2
        }
    
    def get_successors(self, org: str, role: str, entity: str) -> List[str]:
        """
        Get all successors of an entity in a specific role.
        
        Args:
            org: Organization name
            role: Position title
            entity: Person name
            
        Returns:
            List of entity names who succeeded this person (chronological order)
            
        Example:
            successors = graph.get_successors("Apple", "CEO", "Steve Jobs")
            # Returns: ["Tim Cook"]
        """
        chain = self.get_succession_chain(org, role)
        
        try:
            idx = chain.index(entity)
            return chain[idx + 1:]  # All successors after this person
        except (ValueError, IndexError):
            return []
    
    def get_predecessors(self, org: str, role: str, entity: str) -> List[str]:
        """
        Get all predecessors of an entity in a specific role.
        
        Args:
            org: Organization name
            role: Position title
            entity: Person name
            
        Returns:
            List of entity names who preceded this person (chronological order)
            
        Example:
            predecessors = graph.get_predecessors("Apple", "CEO", "Tim Cook")
            # Returns: ["Steve Jobs"]
        """
        chain = self.get_succession_chain(org, role)
        
        try:
            idx = chain.index(entity)
            return chain[:idx]  # All predecessors before this person
        except ValueError:
            return []
    
    # ===== END TEMPORAL JOIN METHODS =====
    
    def save_to_file(self, filepath: str):
        """Save graph to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'TemporalKnowledgeGraph':
        """Load graph from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def __repr__(self):
        """String representation of graph."""
        num_entities = sum(1 for n in self.graph.nodes() 
                          if self.graph.nodes[n].get("type") in ["PERSON", "ORG"])
        num_roles = sum(1 for n in self.graph.nodes() 
                       if self.graph.nodes[n].get("type") == "ROLE")
        return f"TemporalKnowledgeGraph(entities={num_entities}, roles={num_roles})"
