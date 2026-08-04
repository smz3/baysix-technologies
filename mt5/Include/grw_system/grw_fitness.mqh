//+------------------------------------------------------------------+
//|                                                    grw_fitness.mqh |
//|  GRW-001 — the OBJECTIVE. Task 292, replaced at v2.0.0 (task 307).  |
//|                                                                     |
//|  This file is the executable half of research/config/grw_fitness.json|
//|  and the two MUST agree. The JSON is the declared, versioned        |
//|  artifact required by spec §1.3(2): the origin failure was          |
//|  recommending a change that optimised DRAWDOWN when the stated      |
//|  objective was GROWTH. An objective that lives only in code can be  |
//|  swapped without anyone noticing; one that is hashed and cited by   |
//|  every batch cannot.                                                |
//|                                                                     |
//|  FITNESS = P(equity >= target_mult*stake BEFORE equity <= floor_frac*stake)
//|                                                                     |
//|  A BARRIER problem, not a terminal-wealth problem. The mandate is   |
//|  one NON-RELOADABLE $20 stake, half-potted at roughly 2:1, run to a |
//|  fixed dollar target with ruin ACCEPTED as the cost of speed        |
//|  (Syafiq, 2026-08-04). Log-growth ranks the opposite preference —   |
//|  it treats ruin as log(0) = -inf and therefore refuses the bet size |
//|  the mandate is built on. See "parked_objective" in the JSON: the   |
//|  v1.x objective was not wrong, the mandate changed underneath it.   |
//|                                                                     |
//|  ONE PASS = ONE EPISODE = ONE BERNOULLI DRAW. A single pass cannot  |
//|  estimate a probability and does not pretend to:                    |
//|      target touched first  -> 1.0                                   |
//|      floor  touched first  -> 0.0                                   |
//|      neither, window ended -> UNRANKABLE (CENSORED)                 |
//|  p_hat is formed in the Python layer over K independent,            |
//|  NON-OVERLAPPING windows. Censored episodes leave the denominator;  |
//|  scoring one at 0.0 would make "we ran out of window" and "the      |
//|  method died" the same number, which is the substitution this whole |
//|  file exists to prevent.                                            |
//|                                                                     |
//|  Barriers are on EQUITY, floating P&L included — ruin is an equity  |
//|  event and the disclosed exit is a dollar target read off open P&L. |
//|  On resolution the EA closes everything and stops (grw_meta.mq5):   |
//|  the one shot is over, and trading past it is a different           |
//|  experiment wearing the same pass id.                               |
//|                                                                     |
//|  Everything else here is REPORTED, never optimised — max drawdown   |
//|  included (spec §2), and log-growth itself, kept as a diagnostic so |
//|  v1 and v2 passes stay mutually legible.                            |
//+------------------------------------------------------------------+
#ifndef GRW_FITNESS_MQH
#define GRW_FITNESS_MQH
#property strict

#include "grw_types.mqh"

//--- MUST match research/config/grw_fitness.json "version".
#define GRW_FITNESS_VERSION      "2.0.0"
#define GRW_FITNESS_UNRANKABLE   -1.0e9    // "cannot be scored", not "scored badly"

//--- THE BARRIERS. These are the objective's own parameters, NOT tuning knobs, so they are
//--- #defines here and declared in the JSON — never EA inputs. A .set preset must not be
//--- able to move a barrier: that would silently change the question the batch answers.
//--- Moving one is a version bump and a new trial family (JSON change_policy).
#define GRW_BARRIER_STAKE_USD    20.0      // declared stake; the tester deposit MUST equal it
#define GRW_BARRIER_TARGET_MULT  2.0       // +100% — the disclosed manual target
#define GRW_BARRIER_FLOOR_FRAC   0.10      // $2.00 on $20: below this no risk fraction under
                                           // 50% is expressible at the 0.01 min lot, so the
                                           // account is dead before the broker says so
                                           // (stop-out sits near $0.30 — justmarkets.yaml:99)

//--- Diagnostic only (the PARKED v1.x objective). Floors equity before the log so ruin is a
//--- finite, correctly-ordered number instead of -inf/NaN, which MT5 ranks unpredictably.
#define GRW_FITNESS_RUIN_FLOOR   0.01

//+------------------------------------------------------------------+
//| Episode states. LIVE until a barrier is touched.                  |
//+------------------------------------------------------------------+
#define GRW_EP_LIVE    0
#define GRW_EP_TARGET  1
#define GRW_EP_FLOOR   2

//+------------------------------------------------------------------+
//| Arm the episode. Called ONCE from OnInit with the account balance |
//| the run actually started on — not the declared constant, so a     |
//| deposit that disagrees with the mandate is measured and reported  |
//| rather than silently corrected into agreement.                    |
//+------------------------------------------------------------------+
void GrwBarrierInit(GrwStats &st, const double start_balance)
  {
   st.ep_state        = GRW_EP_LIVE;
   st.ep_stake        = start_balance;
   st.ep_peak_eq      = start_balance;
   st.ep_min_eq       = start_balance;
   st.ep_resolved_at  = 0;
   st.ep_orders_at_res = 0;
   st.ep_days_at_res  = 0;
  }

//+------------------------------------------------------------------+
//| Mark the equity path against both barriers. Call on EVERY tick.   |
//| Returns true on the tick the episode RESOLVES (once, ever) so the |
//| caller can close out and stand down.                              |
//+------------------------------------------------------------------+
bool GrwBarrierMark(GrwStats &st, const double equity, const datetime now)
  {
   if(st.ep_state != GRW_EP_LIVE || st.ep_stake <= 0.0)
      return false;

   if(equity > st.ep_peak_eq) st.ep_peak_eq = equity;
   if(equity < st.ep_min_eq)  st.ep_min_eq  = equity;

   //--- FLOOR is tested FIRST. Both barriers can be crossed inside one tick's gap only if
   //--- the account blew through the target and back, which is not a success; and on a
   //--- weekend gap the loss side is the one that actually happened to the account.
   if(equity <= st.ep_stake * GRW_BARRIER_FLOOR_FRAC)
      st.ep_state = GRW_EP_FLOOR;
   else if(equity >= st.ep_stake * GRW_BARRIER_TARGET_MULT)
      st.ep_state = GRW_EP_TARGET;
   else
      return false;

   st.ep_resolved_at   = now;
   st.ep_orders_at_res = st.n_orders;
   st.ep_days_at_res   = st.n_days;
   return true;
  }

//+------------------------------------------------------------------+
//| Everything one pass produces. Fields map 1:1 onto grw_passes      |
//| columns so the Python side copies rather than interprets.         |
//+------------------------------------------------------------------+
struct GrwFitness
  {
   double fitness;        // -> grw_passes.is_fitness / .oos_fitness  (1.0 / 0.0 / sentinel)
   double growth;         // -> .is_growth   PARKED v1 objective, diagnostic only
   int    n_trades;       // -> .is_n_trades
   double net_usd;        // -> .is_net_usd
   double max_dd_pct;     // -> .is_max_dd_pct   REPORTED ONLY
   double initial_deposit;
   double final_equity;
   double profit_factor;
   double win_rate;
   bool   unrankable;     // the episode never resolved — CENSORED, not failed
   //--- BARRIER EPISODE. The objective itself.
   int      ep_state;         // GRW_EP_LIVE / _TARGET / _FLOOR
   bool     resolved;         // ep_state != LIVE
   double   ep_stake;         // account balance the episode started on
   double   target_eq;        // ep_stake * GRW_BARRIER_TARGET_MULT
   double   floor_eq;         // ep_stake * GRW_BARRIER_FLOOR_FRAC
   int      trades_to_res;    // orders opened before resolution (mandate unit: ~21 expected)
   int      days_to_res;
   datetime resolved_at;
   bool     stake_mismatch;   // deposit != declared stake -> the min-lot arithmetic that
                              // drives this whole mandate is NOT the one being measured
   //--- MANDATE UNIT. REPORTED, never optimised.
   int    n_days;
   double trades_per_day;
   double signals_per_day;  // the SUBSTRATE's raw firing rate, before max-open serialisation
                            // and margin refusals — the ceiling frequency can ever reach
   //--- sizing telemetry (grw_sizing.mqh). NOTE: under a half-pot barrier mandate a high
   //--- clamp rate is EXPECTED, not an invalidation — see the JSON validity_flags entry.
   double clamp_up_frac;  // share of orders forced UP to the broker minimum
   double mean_risk_pct;  // realised risk per trade, as % of equity
   double max_risk_pct;
   bool   sizing_valid;   // clamp_up_frac <= threshold
  };

//--- Above this share of forced-min-lot orders the declared risk fraction was not being
//--- honoured. REPORTED, never penalised — and at 2.0.0 it means "the fraction was not
//--- expressible", NOT "the pass is invalid". A promote_if may cite it; fitness never does.
#define GRW_SIZING_MAX_CLAMP_FRAC 0.20

//+------------------------------------------------------------------+
//| Compute the pass result from MT5's own tester statistics plus the |
//| EA's episode + sizing telemetry. Call from OnTester().            |
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

   f.n_days          = st.n_days;
   f.trades_per_day  = (st.n_days > 0) ? ((double)f.n_trades   / st.n_days) : 0.0;
   f.signals_per_day = (st.n_days > 0) ? ((double)st.n_signals / st.n_days) : 0.0;

   f.clamp_up_frac = (st.n_orders > 0) ? ((double)st.n_clamp_up / st.n_orders) : 0.0;
   f.mean_risk_pct = (st.n_orders > 0) ? (st.sum_risk_pct / st.n_orders) : 0.0;
   f.max_risk_pct  = st.max_risk_pct;
   f.sizing_valid  = (st.n_orders > 0 && f.clamp_up_frac <= GRW_SIZING_MAX_CLAMP_FRAC);

   //--- the episode.
   f.ep_state       = st.ep_state;
   f.ep_stake       = st.ep_stake;
   f.target_eq      = st.ep_stake * GRW_BARRIER_TARGET_MULT;
   f.floor_eq       = st.ep_stake * GRW_BARRIER_FLOOR_FRAC;
   f.resolved       = (st.ep_state != GRW_EP_LIVE);
   f.trades_to_res  = st.ep_orders_at_res;
   f.days_to_res    = st.ep_days_at_res;
   f.resolved_at    = st.ep_resolved_at;
   //--- REPORTED, never fatal. A deposit that is not the declared stake measures a
   //--- different account: the min-lot escalation that drives the whole mandate is a
   //--- property of $20, not of the strategy (MEASURED, task 300).
   f.stake_mismatch = (MathAbs(st.ep_stake - GRW_BARRIER_STAKE_USD) > 0.01);

   //--- DIAGNOSTIC ONLY: the parked v1.x objective, kept so v1 and v2 passes remain
   //--- comparable on the same axis. It is NOT the fitness and must not be ranked on.
   if(f.initial_deposit > 0.0)
     {
      double floor_eq = f.initial_deposit * GRW_FITNESS_RUIN_FLOOR;
      double eq       = MathMax(f.final_equity, floor_eq);
      f.growth = MathLog(eq / f.initial_deposit);
     }
   else
      f.growth = 0.0;

   //--- THE OBJECTIVE.
   if(st.ep_state == GRW_EP_TARGET)      { f.unrankable = false; f.fitness = 1.0; }
   else if(st.ep_state == GRW_EP_FLOOR)  { f.unrankable = false; f.fitness = 0.0; }
   else                                  { f.unrankable = true;  f.fitness = GRW_FITNESS_UNRANKABLE; }
  }

//+------------------------------------------------------------------+
//| One-line journal summary. Printed by OnTester so a run is legible |
//| in the tester log without opening the CSV.                        |
//+------------------------------------------------------------------+
string GrwFitnessLine(const GrwFitness &f)
  {
   if(!f.resolved)
      return StringFormat("[GRW] CENSORED — episode never resolved: equity stayed inside "
                          "[%.2f, %.2f] on a %.2f stake for the whole window. n=%d over %d days. "
                          "NOT a failure: excluded from p_hat, never scored 0.",
                          f.floor_eq, f.target_eq, f.ep_stake, f.n_trades, f.n_days);
   return StringFormat("[GRW] %s fit=%.1f | stake=%.2f target=%.2f floor=%.2f | resolved in "
                       "%d trades / %d days | growth=%.5f(parked) n=%d net=%.2f dd=%.2f%% | "
                       "clamp_up=%.1f%% mean_risk=%.2f%% max_risk=%.2f%%",
                       (f.ep_state == GRW_EP_TARGET ? "TARGET HIT" : "FLOOR HIT"),
                       f.fitness, f.ep_stake, f.target_eq, f.floor_eq,
                       f.trades_to_res, f.days_to_res, f.growth, f.n_trades, f.net_usd,
                       f.max_dd_pct, 100.0 * f.clamp_up_frac, f.mean_risk_pct, f.max_risk_pct);
  }

#endif // GRW_FITNESS_MQH
