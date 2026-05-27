import pandas as pd
from typing import List, Dict, Optional
from ..models.structures import B2BZoneInfo, SignalDirection, FlowState
from .engines.fracture_engine import FractureEngine
from .engines.state_manager import StateManager
from .engines.efficiency_governor import EfficiencyGovernor

class StrategyOrchestrator:
    """
    The BRAIN of the SIGMA Strategy.
    V6.7: Inertial Flow (Structural Memory) + Modular Engines.
    """
    
    def __init__(self, tf_state=None, symbol: str = "BTCUSDT"):
        self.tf_state = tf_state
        self.symbol = symbol
        self.states: Dict[str, FlowState] = {
            tf: FlowState() for tf in ["MN1", "W1", "D1", "H4", "H1", "M30"]
        }
        self.blacklisted_origins: Dict[str, set] = {
            tf: set() for tf in ["MN1", "W1", "D1", "H4", "H1", "M30"]
        }
        
        # Engines
        self.fracture = FractureEngine()
        self.manager = StateManager({'fracture': self.fracture})
        
    def blacklist_origin(self, origin_id: str, tf: str):
        if tf in self.blacklisted_origins and origin_id:
            self.blacklisted_origins[tf].add(origin_id)

    def update_flow_state(self, tf_zones: Dict[str, List[B2BZoneInfo]], current_price: float, current_time: pd.Timestamp):
        for tf in self.states.keys():
            old_origin = self.states[tf].origin_id
            self.manager.update_timeframe_flow(tf, self.states[tf], tf_zones.get(tf, []), current_price)
            
            # Phase 12B: Safety Interrupt - Reset cooldown on new structure idea
            if self.states[tf].origin_id != old_origin and self.states[tf].origin_id != "":
                EfficiencyGovernor.reset_cooldown(self.symbol, tf, self.states[tf].origin_dir)

            # Update roadblocks using the global context
            self.states[tf].roadblock_id = self.fracture.is_inside_opposing_zone(
                tf, self.states[tf].origin_dir, current_price, 
                [z for zones_list in tf_zones.values() for z in zones_list],
                siege_magnet_id=self.states[tf].magnet_id if self.states[tf].is_siege_active else ""
            )
            
        if current_time.minute % 30 == 0 and current_time.second == 0:
            self._print_heartbeat(current_time)

    def _validate_trap(self, trap: B2BZoneInfo, narrative: FlowState, flow_tf: str, is_fader: bool = False, is_flow_liberated: bool = False) -> bool:
        """
        Structural validation of a trap against a specific narrative state.
        is_flow_liberated: If True, bypasses strict nesting (Inertial Flow).
        """
        if not is_fader and trap.direction != narrative.origin_dir: return False
        if is_fader and trap.direction == narrative.origin_dir: return False
        
        # 1. Freshness Check
        if is_fader:
            freshness_baseline = narrative.magnet_touch_time
        else:
            freshness_baseline = narrative.origin_touch_time
            if narrative.outpost_id != "":
                if narrative.outpost_touch_time > pd.Timestamp.min:
                     freshness_baseline = narrative.outpost_touch_time
                else:
                     return False # Untouched Outpost blocks traps
        
        if trap.zone_created_time <= freshness_baseline:
            return False
            
        # 2. Roadblock check
        # V6.7: In Liberated Flow (Inertial), we bypass roadblocks as we are "Bulldozing".
        if not is_flow_liberated and narrative.roadblock_id != "":
            return False

        # 3. Hierarchy Alignment (H4/H1/M30 must align with D1/W1 Latches)
        if flow_tf in ['H4', 'H1', 'M30']:
            d1 = self.states['D1']
            w1 = self.states['W1']
            # We align with the LATCH (The Storyline), not necessarily the current zone
            # D1 is the Primary Driver in V6.7
            if d1.latch_dir != SignalDirection.NONE and trap.direction != d1.latch_dir:
                return False
            
            # W1 Veto: Only blocks if we are NOT in Liberated Flow (Strict Sniper Mode)
            # In Liberated Flow (2022 Waterfall), we allow D1 to lead even if W1 is slow.
            if not is_flow_liberated:
                if w1.latch_dir != SignalDirection.NONE and trap.direction != w1.latch_dir:
                    return False

        # 4. Spatial Nesting (Sniper Gate)
        if is_flow_liberated:
             # Inertial Flow: We allow liberated entry if local magnet is not fading
             if (narrative.magnet_fifty_touched or narrative.magnet_L2_touched) and not narrative.is_siege_active:
                 # BULLDOZER EXCEPTION: If we have smashed through the magnet (L2), we continue flow.
                 is_bulldozing = False
                 if narrative.magnet_L2_touched:
                     if narrative.origin_dir == SignalDirection.BEARISH: # Shorting into Support
                         # If we are below the support (L2), we plowed through it.
                         if trap.L2_price < narrative.details_magnet_L2:
                             is_bulldozing = True
                     elif narrative.origin_dir == SignalDirection.BULLISH: # Longing into Resistance
                         # If we are above the resistance (L2), we plowed through it.
                         if trap.L2_price > narrative.details_magnet_L2:
                             is_bulldozing = True
                 
                 if not is_bulldozing:
                     return False
        else:
             # Strict Sniper Mode: Origin or Outpost nesting required
             epsilon = 0.0
             is_origin_nested = False
             is_outpost_nested = False

             if trap.direction == SignalDirection.BULLISH:
                 if trap.L1_price <= narrative.details_origin_price + epsilon: is_origin_nested = True
             else:
                 if trap.L1_price >= narrative.details_origin_price - epsilon: is_origin_nested = True
             
             if not is_origin_nested and narrative.outpost_id != "" and narrative.anchor_is_traded:
                 if trap.direction == SignalDirection.BULLISH:
                     if trap.L1_price <= narrative.details_outpost_price + epsilon: is_outpost_nested = True
                 else:
                     if trap.L1_price >= narrative.details_outpost_price - epsilon: is_outpost_nested = True
             
             if not is_origin_nested and not is_outpost_nested:
                 return False
            
        return True

    def is_trade_allowed(self, signal_tf: str, direction: SignalDirection, zone: B2BZoneInfo, current_price: float, current_time: pd.Timestamp, probe_price: Optional[float] = None, trigger_type: str = "T1") -> tuple[bool, str, float, str]:
        """
        V6.7 ASYMMETRIC GATEKEEPER.
        Uses Storyline Latches to provide structural memory and inertia.
        """
        eval_price = probe_price if probe_price is not None else current_price

        # 0. Basic Filter: Officers Only
        if signal_tf not in ['H4', 'H1', 'M30', 'M15', 'M5', 'M1']:
            return False, "Context Only (Generals Don't Fight)", 0.0, ""

        # 0.5 Pillar 1: Tactical Tier Gating (Phase 12A)
        if not EfficiencyGovernor.is_tier_allowed(signal_tf, trigger_type):
            return False, f"Tier Gating Block: {signal_tf} {trigger_type} Restricted", 0.0, ""

        # [VAULTED]: 0.5.5 Pillar 1.5: Tactical Veto (Phase 12D)
        # H4 Veto is currently deactivated to maximize CAGR (Restoring 10C Alpha).
        # See Logic_Vault_V6.md if re-activation is required.


        # [VAULTED]: 0.6 Pillar 2: Temporal Muter (Phase 12B/D/E)
        # Structural Memory muting is currently deactivated (Restoring 10C Alpha).
        # if not EfficiencyGovernor.is_temporally_clean(signal_tf, self.symbol, direction, current_time):
        #     return False, f"Temporal Mute: {signal_tf} {direction.value} Cooldown Active", 0.0, ""

        # 0.7 Pillar 3: Structural Gasket (Phase 12C)
        efficient, gasket_reason = EfficiencyGovernor.is_spatially_efficient(eval_price, zone)
        if not efficient:
            return False, gasket_reason, 0.0, ""

        # 1. Load Narrative Latches
        mn1 = self.states['MN1']
        w1 = self.states['W1']
        d1 = self.states['D1']
        
        # 2. Identify the Narrative State
        # Flow Agreement: Is the signal moving with the "Upstream" storyline?
        is_mn1_confluent = (mn1.latch_dir == SignalDirection.NONE or direction == mn1.latch_dir)
        is_w1_confluent = (w1.latch_dir == SignalDirection.NONE or direction == w1.latch_dir)
        is_d1_confluent = (d1.latch_dir == SignalDirection.NONE or direction == d1.latch_dir)
        
        # WE ARE IN FLOW if we match the D1 storyline (Primary Driver)
        # V6.7 FIX: W1 Latch is too slow to turn. D1 Latch leads the reversal.
        is_downstream_flow = is_d1_confluent
        
        # If D1 is conflicted with W1 (Civil War), we still allow D1 if it has latched firmly.
        # Strict Consensus (Old Logic) blocked 2022 Shorts because W1 was late to flip.
        
        # 3. GATE A: ANTI-TREND FADERS (Reversal Sieges)
        # These are HIGH FRICTION trades. Only allowed at major Magnets.
        if not is_downstream_flow:
            # Check for MN1/W1 Magnet Fade
            for tf_name in ['MN1', 'W1', 'D1']:
                ref = self.states[tf_name]
                if ref.is_valid and (ref.magnet_fifty_touched or ref.magnet_L2_touched):
                    mag_fifty = ref.details_magnet_price + (ref.details_magnet_L2 - ref.details_magnet_price) * 0.5
                    core_high = max(ref.details_magnet_L2, mag_fifty)
                    core_low = min(ref.details_magnet_L2, mag_fifty)
                    
                    if core_low <= eval_price <= core_high and direction != ref.origin_dir:
                        if self._validate_trap(zone, ref, signal_tf, is_fader=True):
                            return True, f"{tf_name} Magnet Fade (Storyline Reversal)", 0.0, ref.magnet_id
            
            return False, "Blocked: Fighting the Storyline without a Fortress", 0.0, ""

        # 4. GATE B: INERTIAL FLOW (Continuation)
        # These are LIBERATED trades. We follow the last major force.
        # We target the nearest HTF magnet for the current flow.
        target_tf = 'D1' if d1.is_valid and d1.origin_dir == direction else 'W1'
        narrative = self.states[target_tf]
        
        if narrative.is_valid and narrative.origin_dir == direction:
             # Check for Siege Block (Don't join a crowded trade)
             if narrative.is_siege_active:
                 # EXCEPTION: If we are Bulldozing (Price beyond Magnet), Siege is Over/Won.
                 is_bulldozing = False
                 if narrative.magnet_L2_touched:
                     if narrative.origin_dir == SignalDirection.BEARISH: # Shorting into Support
                         if zone.L2_price < narrative.details_magnet_L2:
                             is_bulldozing = True
                     elif narrative.origin_dir == SignalDirection.BULLISH: # Longing into Resistance
                         if zone.L2_price > narrative.details_magnet_L2:
                             is_bulldozing = True
                 
                 if not is_bulldozing:
                     return False, f"Siege Active on {target_tf}", 0.0, ""
             
             # INERTIAL FLOW LIBERATION: is_flow_liberated = True
             if self._validate_trap(zone, narrative, signal_tf, is_flow_liberated=True):
                 return True, f"{target_tf} Inertial Flow (Liberated)", 0.0, narrative.origin_id

        # 5. DISCOVERY BRIDGE: Recovery when HTF is currently invalid
        # If D1 is invalid (Discovery) but the Latch (Memory) is confluent, we allow local leadership.
        if not d1.is_valid and (is_w1_confluent or is_d1_confluent):
            # Target the origin we are bridging TO (usually D1 or W1 depending on who is leading)
            # Actually, if D1 is not valid, we bridge to the D1 Latch direction using local officer structures.
             if self._validate_trap(zone, self.states[signal_tf], signal_tf, is_flow_liberated=True):
                 return True, f"Discovery Flow ({signal_tf} Command)", 0.0, self.states[signal_tf].origin_id

        return False, "No Strategy Alignment", 0.0, ""

    def report_trade_failure(self, tf: str, direction: str | SignalDirection, current_time: pd.Timestamp):
        """Exposes the failure reporting to the backtest engine."""
        dir_enum = direction if isinstance(direction, SignalDirection) else SignalDirection(direction)
        EfficiencyGovernor.report_trade_failure(self.symbol, tf, dir_enum, current_time)

    def _print_heartbeat(self, current_time: pd.Timestamp):
        mn, w1, d1 = self.states['MN1'], self.states['W1'], self.states['D1']
        h4, h1, m3 = self.states['H4'], self.states['H1'], self.states['M30']
        
        print(f"\n[{current_time}] === V6.7 ORCHESTRATOR HEARTBEAT ===")
        print(f"MN1 Tide: {mn.latch_dir.value} | Origin: #{mn.origin_id[:4]} -> Magnet: #{mn.magnet_id[:4]}")
        print(f"W1 Wind:  {w1.latch_dir.value} | Origin: #{w1.origin_id[:4]} -> Magnet: #{w1.magnet_id[:4]}")
        print(f"D1 Path:  {d1.latch_dir.value} | Origin: #{d1.origin_id[:4]} -> Magnet: #{d1.magnet_id[:4]}")
        print(f">>> OFFICERS: H4:#{h4.origin_id[:4]} | H1:#{h1.origin_id[:4]} | M30:#{m3.origin_id[:4]}")
