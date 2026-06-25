//+------------------------------------------------------------------+
//|                                                    fob_swings.mqh  |
//|  FOB's OWN close-based swing pivots — copy of the STRUCT-001        |
//|  primitive (brc_swings.mqh), so FOB owns its detection end-to-end  |
//|  and is never coupled to brc_system's copy. Logic is identical     |
//|  (faithful port of detectors.py detect_swings).                    |
//|                                                                    |
//|  Rule: a pivot close must be STRICTLY greater (high) / lower (low) |
//|  than EVERY other close in a window of `window` bars centred on it |
//|  (radius = window // 2). window must be odd and >= 3; live EA = 3. |
//|                                                                    |
//|  Types (BrcSwing / BRC_SWING_*) stay shared from brc_types — they  |
//|  are the STRUCT-001 data primitive, not detection logic.           |
//+------------------------------------------------------------------+
#ifndef FOB_SWINGS_MQH
#define FOB_SWINGS_MQH
#property strict

#include <brc_system/brc_types.mqh>   // BrcSwing, BRC_SWING_HIGH/LOW (STRUCT-001 types)

//+------------------------------------------------------------------+
//| radius = window // 2, with the odd/>=3 guard.                     |
//+------------------------------------------------------------------+
int FobSwingRadius(const int window)
  {
   if(window < 3 || (window % 2) == 0)
     {
      PrintFormat("[FOB] FATAL swing_window must be odd and >=3 (got %d)", window);
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
//+------------------------------------------------------------------+
bool FobDetectSwingAt(const datetime &t[], const double &c[], const int n,
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

#endif // FOB_SWINGS_MQH
