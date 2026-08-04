//+------------------------------------------------------------------+
//|                                                      grw_types.mqh |
//|  GRW-001 — shared vocabulary for the compounding-strategy factory.  |
//|                                                                     |
//|  The meta-EA is a SUBSTRATE, not a strategy. It exposes four        |
//|  orthogonal axes and every pre-registered config is one point in    |
//|  that space:                                                        |
//|      InpEntryType   — WHERE the signal comes from   (enum, 1 of N)  |
//|      InpFilterMask  — WHICH gates must all pass     (bitmask)       |
//|      InpExitType    — HOW the trade ends            (enum, 1 of N)  |
//|      InpRiskFrac    — fraction of EQUITY at risk    (the compounding|
//|                       lever; lots re-derived from live equity)      |
//|                                                                     |
//|  Spec: docs/reference/grw_autonomous_workflow.md §3.0 — every        |
//|  primitive below carries its MECHANISM in one sentence. A primitive |
//|  with no mechanism is a lottery ticket and does not belong here.    |
//|  Adding a variant = EXTEND AN ENUM BRANCH, never copy the EA        |
//|  (playbook: one file per role, versions = git sha + .set).          |
//+------------------------------------------------------------------+
#ifndef GRW_TYPES_MQH
#define GRW_TYPES_MQH
#property strict

//--- MUST match #property version in grw_meta.mq5 — bump both together.
#define GRW_VERSION "0.3.0"

//+------------------------------------------------------------------+
//| ENTRY primitives — each line is the MECHANISM, not a description. |
//+------------------------------------------------------------------+
enum GRW_ENTRY
  {
   GRW_E_DONCHIAN_BREAK = 0,  // close beyond an N-bar extreme. MECHANISM: resting stop
                              // clusters sit just past well-observed range edges; taking
                              // them out forces a short-horizon liquidity cascade.
   GRW_E_BREAK_RETEST   = 1,  // same break, entered on the FIRST retouch of the broken
                              // level. MECHANISM: identical directional thesis, but filled
                              // against passive liquidity at the reclaimed level — cuts
                              // adverse excursion. (FOB's measured lesson: once exits are
                              // settled, ENTRY TIMING is the only lever left.)
   GRW_E_ATR_REVERSION  = 2,  // fade a close >= k*ATR from an N-bar anchor. MECHANISM:
                              // liquidity vacuum — whoever absorbed the impulse is now
                              // carrying unwanted inventory and rebalances back to anchor.
   GRW_E_MOMO_PULLBACK  = 3   // pullback to the anchor inside an established trend, entered
                              // on resumption. MECHANISM: large orders are worked in slices
                              // (VWAP/TWAP); execution resumes after each pullback.
  };

//+------------------------------------------------------------------+
//| FILTER bits — combined with InpFilterMask; ALL selected bits must |
//| pass (AND, never OR: an OR-gate is a different hypothesis and     |
//| therefore a different pre-registered config).                     |
//+------------------------------------------------------------------+
#define GRW_F_SESSION      1   // broker-hour window. MECHANISM: participation regime —
                               // the flow that drives the edge only shows up in session.
#define GRW_F_TREND_HTF    2   // higher-TF anchor slope agreement. MECHANISM: do not take
                               // the side that dominant flow is leaning against.
#define GRW_F_VOL_FLOOR    4   // ATR >= floor (in points). MECHANISM: a move must be big
                               // enough that the edge is not the same size as the spread.
#define GRW_F_COST_RATIO   8   // stop distance >= N * current spread. MECHANISM: the ONLY
                               // structural escape from transaction cost is a payoff
                               // materially bigger than it (CLAUDE.md rule 16).
#define GRW_F_NO_ROLLOVER 16   // skip the broker rollover hour. MECHANISM: spread blows out
                               // at rollover, so fills there are not representative.
#define GRW_F_ALL         31   // every bit — convenience for "maximally gated" configs.

//+------------------------------------------------------------------+
//| EXIT primitives.                                                  |
//+------------------------------------------------------------------+
enum GRW_EXIT
  {
   GRW_X_FIXED_RR      = 0,   // TP = RR * risk. The coin-flip null every payoff-asymmetry
                              // claim must beat.
   GRW_X_ATR_TRAIL     = 1,   // arm at aR, then trail by d*ATR. MECHANISM: right-tail
                              // capture — the escape from cost is bigger winners, not a
                              // tighter stop.
   GRW_X_TIME_STOP     = 2,   // close after N bars regardless. MECHANISM: every mechanism
                              // above has a horizon; past it the position is a coin flip
                              // paying spread.
   GRW_X_BREAKEVEN_ATR = 3    // move to breakeven at aR, then trail by d*ATR. Isolates the
                              // cost of BE-stopping from the trail itself.
  };

//+------------------------------------------------------------------+
//| STOP-DISTANCE mode — the axis a $20 stake needs.                  |
//|                                                                    |
//| [PARKED 2026-08-04, task 307] The "SCALP mandate" framing below is |
//| superseded. The mandate is a BARRIER method — one non-reloadable   |
//| $20 stake, half-potted at ~2:1, run to a fixed target with ruin    |
//| accepted, resolving in ~21 trades — NOT hundreds of trades a day.  |
//| Objective of record: research/config/grw_fitness.json v2.0.0.      |
//| What survives the reframe is the ARITHMETIC, which never depended  |
//| on trade frequency:                                                |
//|                                                                    |
//| Every primitive produces a STRUCTURAL stop (the level whose        |
//| violation falsifies its mechanism) offset by sl_buf_k * ATR. On H1 |
//| gold that lands at a $2.52 median stop, which is right for H1 and  |
//| unusable at $20: 5% of $20 is $1.00, so the sizing call asks for   |
//| 0.004 lot, floors to the 0.01 broker minimum, and the trade        |
//| silently risks ~2.5x what was declared (that is exactly the        |
//| clamp_up_frac = 1.000 seen on the grw_smoke_20usd run).            |
//|                                                                    |
//| At min lot the stop distance in USD IS the risk in USD — 0.01 lot  |
//| is 1 oz, so a $1 move is $1. The stop therefore is not a free      |
//| parameter, it is the sizing instrument. These modes make that      |
//| explicit instead of hoping ATR happens to land in range.           |
//+------------------------------------------------------------------+
enum GRW_SL_MODE
  {
   GRW_SL_ATR_BUF    = 0,  // structural level ± sl_buf_k*ATR. The original; correct
                           // wherever the account can actually express the risk it implies.
   GRW_SL_ABS_PIPS   = 1,  // fixed sl_pips from entry, structure ignored. THE FIXED-RISK
                           // MODE (was labelled "THE SCALP MODE" pre-2.0.0): pins
                           // risk-per-trade to an exact USD amount at min lot, which is
                           // what makes InpRiskFrac achievable at all on $20. It says
                           // nothing about trade FREQUENCY — that framing is parked.
   GRW_SL_STRUCT_CAP = 2   // structural, but never wider than sl_max_pips. Keeps the
                           // mechanism's own invalidation where it is already tight and
                           // truncates it where it is not. Truncating invalidation CHANGES
                           // THE MECHANISM, so this is its own pre-registered config —
                           // never a "tweak" of ATR_BUF.
  };

//+------------------------------------------------------------------+
//| One entry decision, produced by grw_entry and consumed by         |
//| grw_sizing + grw_trade. `sl` is STRUCTURAL (comes from the        |
//| mechanism's own invalidation level) — risk is measured off it,    |
//| never chosen to make an R-multiple look good ([[er_denominator    |
//| _illusion]]).                                                     |
//+------------------------------------------------------------------+
struct GrwSignal
  {
   bool     valid;        // false = no trade this bar
   bool     is_long;
   double   entry;        // reference price (market path uses live Ask/Bid)
   double   sl;           // structural invalidation
   double   atr;          // ATR at decision time — carried so exits use the SAME value
   string   tag;          // short reason string, lands in the trade ledger
  };

void GrwSignalClear(GrwSignal &s)
  {
   s.valid   = false;
   s.is_long = false;
   s.entry   = 0.0;
   s.sl      = 0.0;
   s.atr     = 0.0;
   s.tag     = "";
  }

//+------------------------------------------------------------------+
//| Live state for one open position, so exits never re-derive risk   |
//| from the current price (which silently changes R mid-trade).      |
//+------------------------------------------------------------------+
struct GrwOpen
  {
   long     pos_id;
   bool     is_long;
   double   entry;
   double   sl0;          // ORIGINAL stop — the 1R denominator, frozen at fill
   double   risk;         // |entry - sl0| in price units, frozen at fill
   double   lots;
   double   atr0;         // ATR at fill, frozen (trail distance must not drift with vol)
   datetime opened_at;
   int      bars_held;
   bool     armed;        // trail/BE has been triggered at least once
   string   tag;
  };

//+------------------------------------------------------------------+
//| The config point being tested, in one struct.                     |
//|                                                                    |
//| MQL5 cannot see an EA's `input` variables from inside an include,  |
//| so the EA fills this once in OnInit and every module reads it. One |
//| struct instead of 15-argument functions, and — more importantly —  |
//| ONE object to serialise into the pass row, so what the ledger says |
//| ran is literally what ran.                                         |
//+------------------------------------------------------------------+
struct GrwCfg
  {
   //--- axes
   GRW_ENTRY       entry_type;
   int             filter_mask;
   GRW_EXIT        exit_type;
   double          risk_frac;
   //--- timeframes
   ENUM_TIMEFRAMES tf;            // signal TF
   ENUM_TIMEFRAMES htf;           // higher TF for the trend gate
   //--- entry shaping
   int             lookback;      // Donchian window / anchor period
   double          ext_k;         // ATR-extension threshold (reversion)
   double          sl_buf_k;      // stop buffer in ATR units beyond the structural level
   int             retest_bars;   // how long a break stays armed for a retest
   //--- stop distance = the sizing instrument at min lot (see GRW_SL_MODE)
   GRW_SL_MODE     sl_mode;
   double          sl_pips;       // ABS_PIPS: exact stop distance from entry, in pips
   double          sl_max_pips;   // STRUCT_CAP: widest structural stop tolerated, in pips
   //--- filters
   int             sess_start;    // broker hour, inclusive
   int             sess_end;      // broker hour, inclusive (start > end wraps midnight)
   double          vol_floor_pts; // ATR floor in POINTS
   double          cost_mult;     // required stop distance as a multiple of live spread
   int             rollover_hr;   // broker hour to avoid
   //--- exits
   double          rr;            // fixed-RR target
   double          arm_r;         // R at which a trail/BE arms
   double          trail_atr;     // trail distance in ATR units
   int             time_stop_bars;
   //--- plumbing
   int             atr_period;
   ulong           magic;
  };

//+------------------------------------------------------------------+
//| Indicator handles, created once in OnInit. Held in one place so a |
//| failed handle is caught at init rather than as silent NaNs later. |
//+------------------------------------------------------------------+
struct GrwCtx
  {
   int h_atr;      // ATR on the signal TF
   int h_anchor;   // SMA on the signal TF — the reversion/momo anchor
   int h_htf;      // SMA on the higher TF — the trend gate
  };

//+------------------------------------------------------------------+
//| Read one indicator value at `shift`. Returns false on a short     |
//| buffer instead of leaving the caller with a stale number.         |
//+------------------------------------------------------------------+
bool GrwBuf(const int handle, const int shift, double &out)
  {
   double b[];
   if(handle == INVALID_HANDLE) return false;
   if(CopyBuffer(handle, 0, shift, 1, b) != 1) return false;
   out = b[0];
   return true;
  }

//+------------------------------------------------------------------+
//| Run-level telemetry. These are NOT performance metrics — they are |
//| VALIDITY metrics. `n_clamp_up` in particular: if the requested    |
//| risk-fraction lot lands below the broker minimum, the trade is    |
//| forced to over-risk and the "compounding" claim is void for that  |
//| pass. That must be MEASURED and reported, never assumed away.     |
//+------------------------------------------------------------------+
struct GrwStats
  {
   int      n_signals;    // entry primitive fired
   int      n_gated;      // ...and was rejected by the filter mask
   int      n_skipped;    // ...passed filters but could not be sized/sent
   int      n_orders;     // ...actually reached the broker
   int      n_clamp_up;   // requested lot < broker min -> FORCED UP (over-risk)
   int      n_clamp_down; // requested lot > broker max / free margin -> forced down
   int      n_sl_too_tight; // stop landed inside the broker's min stop distance and the
                            // signal was DROPPED. At scalp distances this is the gate
                            // between "my stop is 4 pips" and "the broker refused it" —
                            // silently widening instead would change the risk without
                            // telling anyone, so it is counted and the trade is skipped.
   double   sum_risk_pct; // sum of realised risk-as-%-of-equity, for the mean
   double   max_risk_pct; // worst single-trade risk as % of equity
   //--- TRADING DAYS actually seen (distinct dates with ticks), so trades-per-day is
   //--- computed against real sessions rather than calendar span. It is the mandate's
   //--- own unit — "hundreds of trades a day" is unfalsifiable without it — and it is
   //--- REPORTED, never optimised: the objective stays a pure barrier hit-rate (v2.0.0).
   int      n_days;
   datetime cur_day;      // last date bucket seen, for the day-change edge
   datetime first_seen;   // FIRST tick the EA actually processed = the true window start.
                          // SeriesInfoInteger(SERIES_FIRSTDATE) is the symbol's whole
                          // history, not this run's window, and reporting it as
                          // period_start mislabels every pass (v0.2.0 smoke claimed
                          // 2016.06.13 for a window that began 2017.01.01).
   //--- BARRIER EPISODE (v2.0.0 objective). The state lives here because it is written on
   //--- every tick, but the LOGIC and the barrier constants live in grw_fitness.mqh with
   //--- the objective they belong to — the state struct must not own the question.
   int      ep_state;         // GRW_EP_LIVE / _TARGET / _FLOOR
   double   ep_stake;         // account balance the episode started on (armed in OnInit)
   double   ep_peak_eq;       // highest equity while LIVE
   double   ep_min_eq;        // lowest equity while LIVE
   datetime ep_resolved_at;   // tick the episode resolved (0 = never)
   int      ep_orders_at_res; // n_orders at resolution — trades-to-target, the mandate unit
   int      ep_days_at_res;   // n_days at resolution
  };

void GrwStatsClear(GrwStats &st)
  {
   st.n_signals    = 0;
   st.n_gated      = 0;
   st.n_skipped    = 0;
   st.n_orders     = 0;
   st.n_clamp_up   = 0;
   st.n_clamp_down = 0;
   st.n_sl_too_tight = 0;
   st.sum_risk_pct = 0.0;
   st.max_risk_pct = 0.0;
   st.n_days       = 0;
   st.cur_day      = 0;
   st.first_seen   = 0;
   //--- episode: cleared to LIVE with a ZERO stake on purpose. GrwBarrierMark refuses to
   //--- act on a zero stake, so a run that forgets to arm the episode in OnInit produces a
   //--- CENSORED pass rather than a barrier silently measured against $0.
   st.ep_state        = 0;
   st.ep_stake        = 0.0;
   st.ep_peak_eq      = 0.0;
   st.ep_min_eq       = 0.0;
   st.ep_resolved_at  = 0;
   st.ep_orders_at_res = 0;
   st.ep_days_at_res  = 0;
  }

//+------------------------------------------------------------------+
//| Count a distinct trading DAY. Called from OnTick with the current |
//| server time; cheap integer-divide, no date parsing per tick.      |
//+------------------------------------------------------------------+
void GrwStatsMarkDay(GrwStats &st, const datetime now)
  {
   if(st.first_seen == 0)
      st.first_seen = now;                    // true window start, for period_start
   datetime day = (datetime)((long)now / 86400);
   if(day != st.cur_day)
     {
      st.cur_day = day;
      st.n_days++;
     }
  }

//+------------------------------------------------------------------+
//| Helpers shared across modules.                                    |
//+------------------------------------------------------------------+
double GrwSpread()
  {
   return SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
  }

double GrwStopsLevel()
  {
   return (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL)
          * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
  }

//+------------------------------------------------------------------+
//| One pip in PRICE units.                                           |
//|                                                                    |
//| JM quotes XAUUSD at 2 digits, so point = 0.01 and a pip = 10       |
//| points = 0.10 of price — which at the 0.01 min lot (1 oz) is       |
//| exactly $0.10 of P&L. That matches brokers/justmarkets.yaml        |
//| (pip_usd: 0.10), and it is the unit the whole $20 envelope is      |
//| written in: a 10-pip stop = $1.00 = 5% of $20.                     |
//|                                                                    |
//| The 2/3/5-digit rule also gives the conventional pip on FX.        |
//+------------------------------------------------------------------+
double GrwPip()
  {
   int    d  = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   return (d == 2 || d == 3 || d == 5) ? pt * 10.0 : pt;
  }

string GrwEntryName(const GRW_ENTRY e)
  {
   switch(e)
     {
      case GRW_E_DONCHIAN_BREAK: return "DONCHIAN_BREAK";
      case GRW_E_BREAK_RETEST:   return "BREAK_RETEST";
      case GRW_E_ATR_REVERSION:  return "ATR_REVERSION";
      case GRW_E_MOMO_PULLBACK:  return "MOMO_PULLBACK";
     }
   return "UNKNOWN";
  }

string GrwSlModeName(const GRW_SL_MODE m)
  {
   switch(m)
     {
      case GRW_SL_ATR_BUF:    return "ATR_BUF";
      case GRW_SL_ABS_PIPS:   return "ABS_PIPS";
      case GRW_SL_STRUCT_CAP: return "STRUCT_CAP";
     }
   return "UNKNOWN";
  }

string GrwExitName(const GRW_EXIT x)
  {
   switch(x)
     {
      case GRW_X_FIXED_RR:      return "FIXED_RR";
      case GRW_X_ATR_TRAIL:     return "ATR_TRAIL";
      case GRW_X_TIME_STOP:     return "TIME_STOP";
      case GRW_X_BREAKEVEN_ATR: return "BREAKEVEN_ATR";
     }
   return "UNKNOWN";
  }

//--- human-readable filter mask, e.g. 9 -> "SESSION|COST_RATIO". Goes in the ledger so a
//--- pass row can be read without decoding a bitmask by hand.
string GrwFilterMaskName(const int mask)
  {
   if(mask == 0) return "NONE";
   string s = "";
   if((mask & GRW_F_SESSION)     != 0) s += (StringLen(s) > 0 ? "|" : "") + "SESSION";
   if((mask & GRW_F_TREND_HTF)   != 0) s += (StringLen(s) > 0 ? "|" : "") + "TREND_HTF";
   if((mask & GRW_F_VOL_FLOOR)   != 0) s += (StringLen(s) > 0 ? "|" : "") + "VOL_FLOOR";
   if((mask & GRW_F_COST_RATIO)  != 0) s += (StringLen(s) > 0 ? "|" : "") + "COST_RATIO";
   if((mask & GRW_F_NO_ROLLOVER) != 0) s += (StringLen(s) > 0 ? "|" : "") + "NO_ROLLOVER";
   return s;
  }

#endif // GRW_TYPES_MQH
