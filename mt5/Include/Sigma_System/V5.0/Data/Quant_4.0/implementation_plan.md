# W1 Independent Authorization (Minimalist Plan)

## Goal
Add W1 as a main authorizer alongside D1. This ensures that if a valid trap exists inside a W1 anchor, it will be authorized, even if a D1 anchor exists but doesn't have a trap.

## Proposed Changes

### 1. `StrategyOrchestrator.mqh`

#### [MODIFY] `TrapState` Struct
Add `parent_tf` so `IsTradeAllowed` knows which Magnet to target.

```cpp
struct TrapState {
   bool is_active;
   ulong zone_id;
   ENUM_TIMEFRAMES tf;
   double L1_price;
   double L2_price;
   ENUM_SIGNAL_DIRECTION direction;
   ENUM_TIMEFRAMES parent_tf; // <-- ADDED: W1 or D1
   
   TrapState() { Reset(); }
   void Reset() { 
      is_active=false; zone_id=0; tf=PERIOD_CURRENT; L1_price=0; L2_price=0; 
      direction=DIRECTION_NONE; parent_tf=PERIOD_CURRENT; 
   }
};
```

#### [MODIFY] `ScanTraps`
Refactor to find the **best** trap (highest TF) across both providers.

```cpp
void CStrategyOrchestrator::ScanTraps(...) {
   m_trap.Reset();

   // Priority: H4 > H1 > M30
   ENUM_TIMEFRAMES trap_tfs[] = {PERIOD_H4, PERIOD_H1, PERIOD_M30};
   
   for(int t=0; t<3; t++) {
      ENUM_TIMEFRAMES ttf = trap_tfs[t];
      
      // Look for ttf trap in D1 anchor FIRST
      if(m_d1.anchor_id > 0 && m_d1.anchor_touch_time > 0) {
          // Hunt... if found, set m_trap.parent_tf = D1 and RETURN.
      }
      
      // Look for ttf trap in W1 anchor SECOND
      if(m_w1.anchor_id > 0 && m_w1.anchor_touch_time > 0) {
          // Hunt... if found, set m_trap.parent_tf = W1 and RETURN.
      }
   }
}
```

## Diagnostic Logging
Add specific `Print` statements for when W1 is skipped:
- "W1 Scan Skipped: No Anchor"
- "W1 Scan Skipped: Anchor not touched"
- "W1 Trap Rejected: Created before touch"


#### [MODIFY] `IsTradeAllowed`
Update anchor/magnet detection to use the timeframe that actually authorized the trap.

```cpp
out_anchor = (m_trap.parent_tf == PERIOD_D1) ? m_d1.anchor_id : m_w1.anchor_id;
out_magnet = (m_trap.parent_tf == PERIOD_D1) ? m_d1.magnet_id : m_w1.magnet_id;
```

## Verification Plan
1. Compile and run visual backtest.
2. Verify that traps can fire from W1 anchors when D1 is not in a touch state.
3. Confirm targets (TP) correctly switch between W1 and D1 magnets.
