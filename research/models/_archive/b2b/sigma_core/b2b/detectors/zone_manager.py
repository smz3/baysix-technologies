"""
SIGMA-Crypto-ASCEND Zone Manager
Port of B2BZoneManager.mqh
"""

from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from ..models.structures import B2BZoneInfo, DetectionContext, SignalDirection
from .confluence import detect_confluence

class ZoneManager:
    """
    Central repository for managing the lifecycle of B2B zones.
    Handles storage, deduplication, pruning, and hierarchy updates.
    """
    
    def __init__(self, context: DetectionContext):
        self.context = context
        # Primary storage: Dict[zone_id, B2BZoneInfo]
        # We might reference the context's zone storage or maintain our own active set.
        # For the port, let's treat context.zones as the "historical register" 
        # and this Manager as the "Active Set" maintainer if needed.
        # However, MQL5 `B2BZoneManager` often manages the live list.
        # Let's verify SKILL.md: "Zone CRUD, dedup, pruning, consolidation".
        
        # Flattened active zones for easy access
        self.active_zones: List[B2BZoneInfo] = []

    def update(self, new_zones: List[B2BZoneInfo], current_time: datetime):
        """
        Main tick function.
        1. Ingest new zones (deduplicate).
        2. Prune old/invalid zones.
        3. Recalculate confluence.
        """
        self._ingest_zones(new_zones)
        self._prune_zones(current_time)
        self._update_confluence()
        
    def _ingest_zones(self, new_zones: List[B2BZoneInfo]):
        """Adds new zones if they don't already exist."""
        existing_ids = {z.zone_id for z in self.active_zones}
        
        for zone in new_zones:
            if zone.zone_id not in existing_ids:
                # Add check for specific conditions if needed (e.g., minimum size)
                self.active_zones.append(zone)
                # Also ensure it's in the global context
                self._register_to_context(zone)
                existing_ids.add(zone.zone_id)

    def _register_to_context(self, zone: B2BZoneInfo):
        """Ensures zone is in the global DetectionContext for persistence."""
        tf_zones = self.context.get_zones(zone.timeframe)
        # Check if typically already there? 
        # The detector usually puts it there. 
        # If detector uses context directly, this might be redundant, 
        # but safe to keep "Manager" as the authority.
        
        found = False
        for z in tf_zones:
            if z.zone_id == zone.zone_id:
                found = True
                break
        if not found:
            tf_zones.append(zone)

    def _prune_zones(self, current_time: datetime):
        """
        Removes zones that:
        1. Are invalidated (L2 broken).
        2. Are too old (max_zone_age_bars).
        """
        alive = []
        for z in self.active_zones:
            # 1. Invalidation Check
            if z.is_invalidated:
                # Check for "Ghost" logic (persistence after death)? 
                # MQL5 usually kills them locally unless strictly tracking history.
                continue
                
            # 2. Age Check (if applicable)
            # Need bar count since creation. MQL5 uses 'bars_since_creation'.
            # We approximate with time if needed, or rely on an external updater to inc 'zone_age_bars'.
            if z.zone_age_bars > self.context.config.max_zone_age_bars:
                continue
                
            alive.append(z)
            
        self.active_zones = alive

    def _update_confluence(self):
        """Refreshes parent-child relationships for all active zones."""
        # Detect confluence modifies the zone objects in place
        detect_confluence(self.active_zones)

    def get_active_zones(self, tf: str = None) -> List[B2BZoneInfo]:
        """Returns all active zones, optionally filtered by timeframe."""
        if tf:
            return [z for z in self.active_zones if z.timeframe == tf]
        return self.active_zones
        
    def get_zone_by_id(self, zone_id: str) -> Optional[B2BZoneInfo]:
        for z in self.active_zones:
            if z.zone_id == zone_id:
                return z
        return None
