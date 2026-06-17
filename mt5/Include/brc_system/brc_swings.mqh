//+------------------------------------------------------------------+
//|                                                    brc_swings.mqh  |
//|  CLOSE-based swing pivots — faithful port of detectors.py         |
//|  detect_swings (itself the SwingPointDetector.mqh re-port).       |
//|                                                                    |
//|  Rule (MQL5 CSwingPointDetector::IsSwingHigh/IsSwingLow): a pivot  |
//|  close must be STRICTLY greater (high) / lower (low) than EVERY    |
//|  other close in a window of `window` bars centred on it           |
//|  (radius = window // 2). window must be odd and >= 3; live EA = 3. |
//+------------------------------------------------------------------+
#ifndef BRC_SWINGS_MQH
#define BRC_SWINGS_MQH
#property strict

#include "brc_types.mqh"

//+------------------------------------------------------------------+
//| radius = window // 2, with the MQH odd/>=3 guard.                 |
//+------------------------------------------------------------------+
int BrcSwingRadius(const int window)
  {
   if(window < 3 || (window % 2) == 0)
     {
      PrintFormat("[BRC] FATAL swing_window must be odd and >=3 (got %d)", window);
      return -1;
     }
   return window / 2;
  }

//+------------------------------------------------------------------+
//| Test whether absolute series index `p` is a swing pivot.          |
//|   c[], t[]  : full TF series, index 0 = OLDEST (chronological).    |
//|   p         : candidate pivot absolute index.                      |
//|   radius    : window//2.                                           |
//| Returns true + fills `out` (bar_index=p, price=close, broken=false)|
//| Mirrors detect_swings inner loop incl. the early-exit.             |
//+------------------------------------------------------------------+
bool BrcDetectSwingAt(const datetime &t[], const double &c[], const int n,
                      const int p, const int radius, BrcSwing &out)
  {
   if(p - radius < 0 || p + radius >= n)
      return false;                          // not enough neighbours to confirm

   double curr = c[p];
   bool   is_high = true;
   bool   is_low  = true;

   for(int j = p - radius; j <= p + radius; j++)
     {
      if(j == p)
         continue;
      if(curr <= c[j]) is_high = false;      // STRICT: ties disqualify both
      if(curr >= c[j]) is_low  = false;
      if(!is_high && !is_low)
         return false;                       // early exit (detectors.py parity)
     }

   if(!is_high && !is_low)
      return false;

   out.time      = t[p];
   out.price     = curr;
   out.type      = is_high ? BRC_SWING_HIGH : BRC_SWING_LOW;
   out.bar_index = p;
   out.broken    = false;
   return true;
  }

#endif // BRC_SWINGS_MQH
