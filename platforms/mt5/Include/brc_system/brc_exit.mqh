//+------------------------------------------------------------------+
//|                                                     brc_exit.mqh   |
//|  BRC trader — EXIT module (swappable strategy logic).             |
//|                                                                    |
//|  Owns ONLY the exit decision for an open position. The stop (SL =  |
//|  invalidation level) is attached to the order at send time by the  |
//|  entry plan and enforced natively by MT5 — it is NOT polled here.  |
//|  This module owns the TIME exit and the optional take-profit.      |
//|                                                                    |
//|  IS-01 = BRC_EXIT_TIME, max_hold = 6 bars, NO take-profit:         |
//|  close at market on the Nth bar after entry (or earlier if the     |
//|  native SL fires). The bounded hold is what kills the multi-year   |
//|  run-to-invalidation tail that poisoned the query-layer result.    |
//+------------------------------------------------------------------+
#ifndef BRC_EXIT_MQH
#define BRC_EXIT_MQH
#property strict

#include "brc_types.mqh"

//--- exit policy. TIME = stop OR clock only (IS-01). TIME_TP adds a fixed
//    +k*R take-profit (task 133 robustness).
enum BRC_EXIT_MODE
  {
   BRC_EXIT_TIME    = 0,   // IS-01: native SL, else close at max_hold bars
   BRC_EXIT_TIME_TP = 1    // task 133: + take-profit at entry + tp_mult * R
  };

//+------------------------------------------------------------------+
//| Take-profit price for TIME_TP mode (0.0 if TP disabled).         |
//| Direction inferred from a long flag the EA already knows.         |
//+------------------------------------------------------------------+
double BrcTakeProfitFor(const BRC_EXIT_MODE mode, const bool is_long,
                        const double entry, const double r_unit,
                        const double tp_mult)
  {
   if(mode != BRC_EXIT_TIME_TP || tp_mult <= 0.0 || r_unit <= 0.0)
      return 0.0;
   return is_long ? (entry + tp_mult * r_unit) : (entry - tp_mult * r_unit);
  }

//+------------------------------------------------------------------+
//| Time exit: true once `bars_held` complete bars have elapsed since |
//| the entry bar. bars_held is counted by the EA as closed bars      |
//| strictly after the fill bar; at >= max_hold we close at market.   |
//+------------------------------------------------------------------+
bool BrcTimeExitDue(const int bars_held, const int max_hold)
  {
   return (max_hold > 0 && bars_held >= max_hold);
  }

#endif // BRC_EXIT_MQH
