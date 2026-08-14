//+------------------------------------------------------------------+
//|                                                   brc_sizing.mqh   |
//|  BRC trader — POSITION SIZING module (swappable).                 |
//|                                                                    |
//|  Owns ONLY lot calculation. At $50 XAUUSD the broker MIN-LOT floor |
//|  (0.01) dominates: fixed-fractional risk rounds straight down to   |
//|  the minimum and the drawdown floor is structural, not tunable     |
//|  (see [[orb_dd_structural_floor]]). So IS-01 = FIXED_LOT 0.01; the |
//|  FIXED_FRAC path is here for larger accounts / robustness, and is  |
//|  honest about flooring to min-lot when the risk budget can't even  |
//|  fund one minimum lot.                                             |
//+------------------------------------------------------------------+
#ifndef BRC_SIZING_MQH
#define BRC_SIZING_MQH
#property strict

enum BRC_SIZE_MODE
  {
   BRC_SIZE_FIXED_LOT  = 0,   // IS-01: always `fixed_lot` (clamped to broker limits)
   BRC_SIZE_FIXED_FRAC = 1    // risk `risk_pct`% of equity per R (floors to min-lot)
  };

//+------------------------------------------------------------------+
//| Clamp a raw volume to the symbol's min/max and round DOWN to the |
//| volume step (never over-risk by rounding up).                    |
//+------------------------------------------------------------------+
double BrcNormalizeLot(const double raw)
  {
   double vmin  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double vstep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(vstep <= 0.0)
      vstep = vmin;

   double v = raw;
   if(v < vmin) v = vmin;                    // floor to min (honest: cannot trade smaller)
   v = MathFloor(v / vstep) * vstep;         // round DOWN to step
   if(v < vmin) v = vmin;
   if(v > vmax) v = vmax;
   return NormalizeDouble(v, 2);
  }

//+------------------------------------------------------------------+
//| Lot for one trade. `r_price` = stop distance in PRICE (|entry-sl|)|
//| — used only by FIXED_FRAC. Returns a broker-valid volume.        |
//+------------------------------------------------------------------+
double BrcLotSize(const BRC_SIZE_MODE mode, const double fixed_lot,
                  const double risk_pct, const double r_price)
  {
   if(mode == BRC_SIZE_FIXED_LOT || risk_pct <= 0.0 || r_price <= 0.0)
      return BrcNormalizeLot(fixed_lot);

   //--- FIXED_FRAC: lots = (equity * risk%) / (loss per lot at the stop).
   double equity     = AccountInfoDouble(ACCOUNT_EQUITY);
   double tick_val   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_size  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_val <= 0.0 || tick_size <= 0.0)
      return BrcNormalizeLot(fixed_lot);

   double risk_money    = equity * risk_pct / 100.0;
   double loss_per_lot  = (r_price / tick_size) * tick_val;   // money lost at SL per 1.0 lot
   if(loss_per_lot <= 0.0)
      return BrcNormalizeLot(fixed_lot);

   return BrcNormalizeLot(risk_money / loss_per_lot);
  }

#endif // BRC_SIZING_MQH
