"""
SIGMA-Crypto-ASCEND Confluence Detector
Port of B2BConfluence.mqh
"""

from typing import List, Optional
from ..models.structures import B2BZoneInfo, TF_RANK

def get_zone_range(zone: B2BZoneInfo) -> tuple[float, float]:
    """Returns (min_price, max_price) for a zone."""
    return min(zone.L1_price, zone.L2_price), max(zone.L1_price, zone.L2_price)

def are_zones_nested(parent: B2BZoneInfo, child: B2BZoneInfo) -> bool:
    """
    Checks if 'child' is spatially nested within 'parent'.
    
    Rules:
    1. Parent must be a HIGHER timeframe (lower rank value).
    2. Child's price range must be contained within Parent's price range.
    3. (Optional) Directions should typically match, but structure is structure.
       Consensus usually requires same direction.
    """
    # 1. Check Rank (Lower value = Higher Timeframe)
    # e.g., D1 (2) is parent to H1 (4). 2 < 4.
    if parent.tf_rank >= child.tf_rank:
        return False
        
    # 2. Check Spatial Nesting
    p_min, p_max = get_zone_range(parent)
    c_min, c_max = get_zone_range(child)
    
    # Strict nesting: Child is fully inside Parent
    # Allow small tolerance? MQL5 uses strict comparison usually.
    return c_min >= p_min and c_max <= p_max

def detect_confluence(zones: List[B2BZoneInfo]) -> List[B2BZoneInfo]:
    """
    Annotates zones with parent/child relationships.
    Returns the modified list of zones.
    """
    # Sort zones by TF rank (Highest TF first -> MN1, W1, D1...)
    # This allows us to find parents efficiently.
    sorted_zones = sorted(zones, key=lambda z: z.tf_rank)
    
    # N^2 complexity is fine for reasonable zone counts (<100 active).
    # For production with 10k zones, we'd need a spatial tree, 
    # but strictly active zones are few.
    
    for i, child in enumerate(sorted_zones):
        # Reset parent info
        child.is_inside_parent = False
        child.parent_zone_id = ""
        child.parent_tf = ""
        child.parent_count = 0
        
        # Look for parents in higher timeframes (earlier in sorted list)
        best_parent = None
        
        # Iterate backwards from current zone to find immediate parent
        for j in range(i - 1, -1, -1):
            candidate = sorted_zones[j]
            
            # Optimization: If we reached same rank, stop (sorted by rank)
            if candidate.tf_rank == child.tf_rank:
                continue
                
            if are_zones_nested(candidate, child):
                # Found a parent!
                # Since we iterate backwards, the first one we find is the "closest" parent in terms of rank
                # (e.g. H1 child looking at D1, W1. If D1 is closer in rank and valid, it's the direct parent)
                
                # Check direction match for "Narrative Parent"
                if candidate.direction == child.direction:
                    child.has_narrative_parent = True
                    child.is_inside_parent = True
                    child.parent_count += 1
                    
                    # We only record one primary parent (the tightest one)
                    if best_parent is None:
                        best_parent = candidate
                        child.parent_zone_id = candidate.zone_id
                        child.parent_tf = candidate.timeframe
                        
                # Check "Control Parent" (could be opposing?) 
                # Definitions vary, but for B2B, strict confluence usually implies same direction.
                
    return sorted_zones
