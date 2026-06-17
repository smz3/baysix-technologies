//+------------------------------------------------------------------+
//|                                                     brc_types.mqh  |
//|        BRC zone-emitter — shared types (self-contained, no Sigma) |
//|                                                                    |
//| Port targets (owned Python spec — do NOT fork from old EA):        |
//|   swings    : research/models/struct/struct001/detectors.py        |
//|   breakouts : research/models/struct/struct001/rawbreakout.py      |
//|   5-pointer : research/models/brc/brc001/zones.py   (PATH B)        |
//|   lifecycle : research/models/brc/brc001/{retest,continuation,      |
//|               lifecycle}.py                                         |
//| Design     : mt5/Documentation/brc_system/BRC_Emitter_Design.md    |
//+------------------------------------------------------------------+
#ifndef BRC_TYPES_MQH
#define BRC_TYPES_MQH
#property strict

//--- Single source of truth for the BRC code version. Bump this on any
//    behaviour change; it is printed at OnInit, set as the EA #property
//    version, and stamped into the run-id so every emitted CSV traces back
//    to the exact code that produced it (filenames stay unversioned — git
//    SHA + this define are the real version control).
#define BRC_VERSION "1.0.0"

//--- direction / swing type (self-contained; mirrors SignalDirection/SwingType)
enum BRC_DIR        { BRC_BULL = 0, BRC_BEAR = 1 };
enum BRC_SWING_TYPE { BRC_SWING_HIGH = 0, BRC_SWING_LOW = 1 };

//+------------------------------------------------------------------+
//| A confirmed swing pivot (CLOSE-based — the Sigma doctrinal rule). |
//| price == close (detectors.py: close-based pivot).                 |
//+------------------------------------------------------------------+
struct BrcSwing
  {
   datetime          time;        // pivot bar time
   double            price;       // pivot close
   int              type;        // BRC_SWING_HIGH | BRC_SWING_LOW
   int              bar_index;   // absolute bar index in the TF series
   bool              broken;      // stateful: a swing breaks at most once
  };

//+------------------------------------------------------------------+
//| A raw breakout event (rawbreakout.py RawBreakoutInfo, trimmed).   |
//| L2/impulse_start_price is OMITTED — Path B (zones.py) never        |
//| consumes it, and PASS-1 shared-L2 does not change WHICH breaks     |
//| fire (PASS-2 breaking is independent of L2).                       |
//+------------------------------------------------------------------+
struct BrcBreak
  {
   datetime          swing_time;   // broken swing time  (unique key — a swing breaks once)
   double            swing_price;  // broken swing price
   int              swing_type;   // broken swing type
   int              dir;          // BRC_BULL | BRC_BEAR
   datetime          bar_time;     // breakout bar time
   double            bar_close;    // breakout bar close (beyond the swing)
   int              bar_index;    // breakout bar absolute index
  };

//+------------------------------------------------------------------+
//| A confirmed 5-pointer BRC zone (zones.py BrcZone) + lifecycle.    |
//| Lifecycle fields are filled post-confirmation by BrcLifecycle.    |
//+------------------------------------------------------------------+
struct BrcZone
  {
   //--- geometry (zones.py) -----------------------------------------
   int              direction;    // BRC_BULL | BRC_BEAR
   double            l1;           // = P2.price  (entry)
   double            l2;           // = extreme(P1,P3) (invalidation) == P1 under P3<P1 gate
   double            mid;          // 0.5*(l1+l2)
   datetime          p1_time;   double p1_price;   // L2 origin swing
   datetime          p2_time;   double p2_price;   // L1 entry swing (1st-break target)
   datetime          p3_time;   double p3_price;   // context-gate swing (P3<P1)
   datetime          p4_time;   double p4_price;   // confirmation bar (broke P5) close
   datetime          p5_time;   double p5_price;   // 2nd barrier swing
   int              break_kind;   // 0=same_bar, 1=sequential   (H_alt-2 input)

   //--- lifecycle (retest.py / continuation.py / lifecycle.py) ------
   datetime          t1_time;      // first wick touch of L1  (0 = never)
   datetime          t2_time;      // first wick touch of mid
   datetime          t3_time;      // first wick touch of L2
   datetime          invalidation_time; // first CLOSE beyond L2 (0 = alive at data-end)
   bool              alive;        // still open?
   bool              continued;    // closed >= +1R in break dir before invalidation
   double            mfe_r;        // max favourable excursion / R   (from L1 entry)
   double            mae_r;        // max adverse excursion / R
   double            realized_r;   // unmanaged hold to invalidation/data-end
   int              bars_alive;   // P4 -> death/data-end (in this TF's bars)
   //--- entry bookkeeping for lifecycle math ------------------------
   double            entry;        // = l1 (the L1 retest fill)
   double            r_unit;       // = |l1 - l2|
   bool              entered;      // has the L1 retest touch fired? (entry armed)
  };

#define BRC_SAME_BAR   0
#define BRC_SEQUENTIAL 1

#endif // BRC_TYPES_MQH
