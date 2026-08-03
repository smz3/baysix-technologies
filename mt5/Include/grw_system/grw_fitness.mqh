//+------------------------------------------------------------------+
//|                                                    grw_fitness.mqh |
//|  GRW-001 — the OBJECTIVE. Task 292.                                 |
//|                                                                     |
//|  This file is the executable half of research/config/grw_fitness.json|
//|  and the two MUST agree. The JSON is the declared, versioned        |
//|  artifact required by spec §1.3(2): the origin failure was          |
//|  recommending a change that optimised DRAWDOWN when the stated      |
//|  objective was GROWTH. An objective that lives only in code can be  |
//|  swapped without anyone noticing; one that is hashed and cited by   |
//|  every batch cannot.                                                |
//|                                                                     |
//|  FITNESS = log(final_equity / initial_deposit)                       |
//|                                                                     |
//|  Total log-growth over the window, nothing else. Not Sharpe, not    |
//|  profit factor, not a drawdown-penalised blend. It is the right     |
//|  objective for a COMPOUNDING account because log-wealth is additive |
//|  across sequential bets, so maximising it maximises terminal wealth |
//|  — and it needs no risk term bolted on, since ruin is already       |
//|  log(0) = -inf and the objective flees it on its own.               |
//|                                                                     |
//|  Two guards, both SENTINELS rather than silent adjustments:         |
//|    • n_trades < min_trades  -> UNRANKABLE. A 3-trade pass has no    |
//|      growth rate, only an anecdote; giving it a merely-poor score   |
//|      would let it outrank a real strategy that had a bad window.    |
//|    • equity floored at ruin_floor_frac of the deposit before the    |
//|      log, so ruin returns a finite, correctly-ordered worst score   |
//|      instead of -inf/NaN, which MT5 ranks unpredictably.            |
//|                                                                     |
//|  Everything else here is REPORTED, never optimised — max drawdown   |
//|  included (spec §2: reported, never a constraint). clamp_up_frac is |
//|  the load-bearing one: see grw_sizing.mqh.                          |
//+------------------------------------------------------------------+
#ifndef GRW_FITNESS_MQH
#define GRW_FITNESS_MQH
#property strict

#include "grw_types.mqh"

//--- MUST match research/config/grw_fitness.json "version".
#define GRW_FITNESS_VERSION      "1.0.0"
#define GRW_FITNESS_UNRANKABLE   -1.0e9    // "cannot be scored", not "scored badly"
#define GRW_FITNESS_MIN_TRADES   30        // declared floor for a growth claim
#define GRW_FITNESS_RUIN_FLOOR   0.01      // equity floor as a fraction of the deposit

//+------------------------------------------------------------------+
//| Everything one pass produces. Fields map 1:1 onto grw_passes      |
//| columns so the Python side copies rather than interprets.         |
//+------------------------------------------------------------------+
struct GrwFitness
  {
   double fitness;        // -> grw_passes.is_fitness / .oos_fitness
   double growth;         // -> .is_growth  (same number; kept separate because a future
                          //    fitness version may diverge from raw log-growth)
   int    n_trades;       // -> .is_n_trades
   double net_usd;        // -> .is_net_usd
   double max_dd_pct;     // -> .is_max_dd_pct   REPORTED ONLY
   double initial_deposit;
   double final_equity;
   double profit_factor;
   double win_rate;
   bool   unrankable;     // the min-trades guard fired
   //--- sizing validity (grw_sizing.mqh) — decides whether "growth" is even a
   //--- compounding claim for this pass.
   double clamp_up_frac;  // share of orders forced UP to the broker minimum
   double mean_risk_pct;  // realised risk per trade, as % of equity
   double max_risk_pct;
   bool   sizing_valid;   // clamp_up_frac <= threshold
  };

//--- Above this share of forced-min-lot orders, the equity fraction was not being
//--- honoured and the pass measured a FIXED-LOT strategy. Reported, not penalised —
//--- promote_if in a prereg may cite it, but the fitness itself stays a pure objective.
#define GRW_SIZING_MAX_CLAMP_FRAC 0.20

//+------------------------------------------------------------------+
//| Compute the pass result from MT5's own tester statistics plus the |
//| EA's sizing telemetry. Call from OnTester().                      |
//+------------------------------------------------------------------+
void GrwFitnessCompute(const GrwStats &st, GrwFitness &f)
  {
   f.initial_deposit = TesterStatistics(STAT_INITIAL_DEPOSIT);
   f.net_usd         = TesterStatistics(STAT_PROFIT);
   f.n_trades        = (int)TesterStatistics(STAT_TRADES);
   f.max_dd_pct      = TesterStatistics(STAT_EQUITYDD_PERCENT);
   f.profit_factor   = TesterStatistics(STAT_PROFIT_FACTOR);
   f.final_equity    = f.initial_deposit + f.net_usd;

   double won = TesterStatistics(STAT_PROFIT_TRADES);
   f.win_rate = (f.n_trades > 0) ? (100.0 * won / f.n_trades) : 0.0;

   f.clamp_up_frac = (st.n_orders > 0) ? ((double)st.n_clamp_up / st.n_orders) : 0.0;
   f.mean_risk_pct = (st.n_orders > 0) ? (st.sum_risk_pct / st.n_orders) : 0.0;
   f.max_risk_pct  = st.max_risk_pct;
   f.sizing_valid  = (st.n_orders > 0 && f.clamp_up_frac <= GRW_SIZING_MAX_CLAMP_FRAC);

   //--- guard 1: too few trades to be a growth rate at all.
   if(f.n_trades < GRW_FITNESS_MIN_TRADES || f.initial_deposit <= 0.0)
     {
      f.unrankable = true;
      f.growth     = 0.0;
      f.fitness    = GRW_FITNESS_UNRANKABLE;
      return;
     }
   f.unrankable = false;

   //--- guard 2: floor equity so ruin is finite and ordered, not -inf.
   double floor_eq = f.initial_deposit * GRW_FITNESS_RUIN_FLOOR;
   double eq       = MathMax(f.final_equity, floor_eq);

   f.growth  = MathLog(eq / f.initial_deposit);
   f.fitness = f.growth;
  }

//+------------------------------------------------------------------+
//| One-line journal summary. Printed by OnTester so a run is legible |
//| in the tester log without opening the CSV.                        |
//+------------------------------------------------------------------+
string GrwFitnessLine(const GrwFitness &f)
  {
   if(f.unrankable)
      return StringFormat("[GRW] UNRANKABLE n=%d (<%d) net=%.2f — no growth claim possible",
                          f.n_trades, GRW_FITNESS_MIN_TRADES, f.net_usd);
   return StringFormat("[GRW] fit=%.5f growth=%.5f n=%d net=%.2f dd=%.2f%% "
                       "| sizing %s clamp_up=%.1f%% mean_risk=%.2f%% max_risk=%.2f%%",
                       f.fitness, f.growth, f.n_trades, f.net_usd, f.max_dd_pct,
                       (f.sizing_valid ? "VALID" : "INVALID(fixed-lot)"),
                       100.0 * f.clamp_up_frac, f.mean_risk_pct, f.max_risk_pct);
  }

#endif // GRW_FITNESS_MQH
