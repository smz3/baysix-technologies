//+------------------------------------------------------------------+
//|                                                     grw_sizing.mqh |
//|  GRW-001 — the COMPOUNDING lever. Task 292.                        |
//|                                                                     |
//|  Every trade risks a fixed FRACTION of live equity, so lots are     |
//|  re-derived from AccountInfoDouble(ACCOUNT_EQUITY) at each fill.    |
//|  That, and only that, is what makes the objective log-growth: with  |
//|  a fixed lot the account grows arithmetically and log-growth        |
//|  degenerates into "net USD with extra steps".                       |
//|                                                                     |
//|  THE VALIDITY TRAP THIS MODULE EXISTS TO EXPOSE                     |
//|  A small account cannot express a small risk fraction. XAUUSD min   |
//|  lot is 0.01 = 1 oz = $1 per $1 of gold, so a $10 stop risks $10    |
//|  no matter what InpRiskFrac says. On a $20 deposit that is 50% of   |
//|  equity per trade — the fraction is not being honoured, and any     |
//|  "compounding" read off that pass is a fiction.                     |
//|                                                                     |
//|  So the clamp is NEVER silent. It is counted (GrwStats.n_clamp_up), |
//|  reported by OnTester as clamp_up_frac, and the behaviour is an     |
//|  explicit input (GRW_UNDERSIZE) rather than a hidden default. This  |
//|  is spec §1.3(2): substituting a different objective (fixed-lot     |
//|  net profit) for the declared one (fractional-risk growth) without  |
//|  saying so is the exact failure Loop A exists to catch.             |
//|                                                                     |
//|  Rounding is always DOWN to the volume step. Rounding up would      |
//|  over-risk by up to a full step on every single trade.              |
//+------------------------------------------------------------------+
#ifndef GRW_SIZING_MQH
#define GRW_SIZING_MQH
#property strict

#include "grw_types.mqh"

//--- What to do when the risk-fraction lot lands below the broker minimum.
enum GRW_UNDERSIZE
  {
   GRW_UNDER_SKIP      = 0,  // do not trade — the declared risk fraction cannot be honoured.
                             // Honest, but on a small deposit it can yield n=0, which tests
                             // the ACCOUNT, not the mechanism.
   GRW_UNDER_FORCE_MIN = 1   // trade at min lot and COUNT it. The pass then measures a
                             // fixed-lot strategy; clamp_up_frac says how much of it.
  };

//+------------------------------------------------------------------+
//| Money risked per 1.0 of PRICE movement, per 1.0 lot.              |
//| Derived from the symbol's own tick spec so nothing is hardcoded   |
//| per instrument (XAUUSD: tick 0.01 / $1.00 per lot -> $100).       |
//| Returns 0.0 if the broker spec is unreadable — caller must skip.  |
//+------------------------------------------------------------------+
double GrwMoneyPerPricePerLot()
  {
   double tick_val  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_val <= 0.0 || tick_size <= 0.0)
      return 0.0;
   return tick_val / tick_size;
  }

//+------------------------------------------------------------------+
//| Round a volume DOWN to the broker's step, then normalise for the  |
//| step's own decimal count (0.01 steps must not ship as 0.0099999). |
//+------------------------------------------------------------------+
double GrwFloorToStep(const double vol, const double step)
  {
   if(step <= 0.0) return vol;
   double n = MathFloor(vol / step + 1e-9) * step;
   int    d = (int)MathMax(0, MathCeil(-MathLog10(step) - 1e-9));
   return NormalizeDouble(n, d);
  }

//+------------------------------------------------------------------+
//| THE sizing call.                                                  |
//|   risk_price  — |entry - sl| in PRICE units (structural, frozen)  |
//|   risk_frac   — InpRiskFrac, fraction of equity to put at risk    |
//|   under       — what to do if the answer is below the broker min  |
//|   st          — telemetry, mutated in place                       |
//|   out_risk_pct— realised risk as % of equity AFTER all clamping    |
//|                 (this is the number that is true, not the input)   |
//| Returns lots, or 0.0 when the trade must be skipped.              |
//+------------------------------------------------------------------+
double GrwSizeLots(const double risk_price, const double risk_frac,
                   const GRW_UNDERSIZE under, GrwStats &st, double &out_risk_pct)
  {
   out_risk_pct = 0.0;
   if(risk_price <= 0.0 || risk_frac <= 0.0)
      return 0.0;

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity <= 0.0)
      return 0.0;                                   // ruined; nothing left to size against

   double mpu = GrwMoneyPerPricePerLot();
   if(mpu <= 0.0)
      return 0.0;                                   // unreadable symbol spec -> refuse to guess

   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   double risk_usd = equity * risk_frac;
   double want     = risk_usd / (risk_price * mpu);  // the lot the fraction actually asks for
   double lots     = GrwFloorToStep(want, step);

   //--- Clamps are FLAGGED here and only COUNTED on the way out, after we know an order is
   //--- actually being sent. Counting them inline double-counts every signal that clamps and
   //--- is then refused by the margin check below — which is not hypothetical: the first M1
   //--- scalp smoke reported n_clamp_up=9815 against n_orders=16, i.e. clamp_up_frac=613,
   //--- because a $20 account at 1:100 leverage clamped up and then could not afford the
   //--- position. A "fraction" above 1.0 silently voids the sizing_valid flag it feeds.
   bool clamped_up   = false;
   bool clamped_down = false;

   //--- BELOW the broker minimum: the declared fraction is not expressible on this account.
   if(lots < vmin)
     {
      if(under == GRW_UNDER_SKIP)
        {
         st.n_skipped++;
         return 0.0;
        }
      lots = vmin;
      clamped_up = true;                             // over-risk, counted on the way out
     }

   //--- ABOVE the broker maximum.
   if(lots > vmax)
     {
      lots = GrwFloorToStep(vmax, step);
      clamped_down = true;
     }

   //--- FREE MARGIN: shrink until it fits, never send an order we know will be rejected.
   //--- Leverage on this venue is equity-tiered and changes as the account grows, so margin
   //--- is asked for fresh here rather than assumed (spec §3.2(1)).
   double price  = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double margin = 0.0;
   double freem  = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(OrderCalcMargin(ORDER_TYPE_BUY, _Symbol, lots, price, margin) && margin > freem)
     {
      double scaled = GrwFloorToStep(lots * (freem * 0.95) / MathMax(margin, 1e-9), step);
      if(scaled < vmin)
        {
         st.n_skipped++;
         return 0.0;                                 // cannot afford even the minimum
        }
      lots = scaled;
      clamped_down = true;
     }

   //--- Order is going out — now the clamps are real and get counted.
   if(clamped_up)   st.n_clamp_up++;
   if(clamped_down) st.n_clamp_down++;

   //--- The truth about this trade, whatever the input said.
   out_risk_pct = 100.0 * (lots * risk_price * mpu) / equity;
   if(out_risk_pct > st.max_risk_pct)
      st.max_risk_pct = out_risk_pct;
   st.sum_risk_pct += out_risk_pct;
   return lots;
  }

#endif // GRW_SIZING_MQH
