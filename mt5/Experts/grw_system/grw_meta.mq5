//+------------------------------------------------------------------+
//|                                                       grw_meta.mq5 |
//|  GRW-001 — the meta-EA. Task 292.                                   |
//|                                                                     |
//|  This is a SUBSTRATE, not a strategy. It exposes four orthogonal    |
//|  axes and each pre-registered config is one point in that space:    |
//|                                                                     |
//|      InpEntryType   WHERE the signal comes from   (1 of 4)          |
//|      InpFilterMask  WHICH gates must all pass     (bitmask, AND)    |
//|      InpExitType    HOW the trade ends            (1 of 4)          |
//|      InpRiskFrac    fraction of EQUITY per trade  (the compounding  |
//|                     lever — lots re-derived from live equity)       |
//|                                                                     |
//|  Objective: OnTester() returns log(final_equity / initial_deposit), |
//|  the declared fitness in research/config/grw_fitness.json. Log-     |
//|  growth, because wealth compounds multiplicatively and log-wealth   |
//|  is what adds up across sequential bets. No Sharpe, no drawdown     |
//|  penalty, no blend — a blended objective is how the thing you       |
//|  actually optimised stops matching the thing you said you wanted.   |
//|                                                                     |
//|  ONE FILE, forever. A new variant EXTENDS AN ENUM BRANCH and ships  |
//|  a new .set preset; it never copies this EA. Duplicating the file   |
//|  kills the tester sweep and the git lineage in one move.            |
//|                                                                     |
//|  REAL TICKS ONLY (Model=4). Entries are close-driven but exits are  |
//|  managed tick-by-tick, so an open-prices run measures a different   |
//|  strategy than the one written here.                                |
//|                                                                     |
//|  Modules — grw_system owns everything, nothing shared with          |
//|  fob_system or brc_system (CLAUDE.md rule 4a):                      |
//|    grw_types · grw_sizing · grw_entry · grw_filter · grw_exit ·      |
//|    grw_trade · grw_fitness · grw_ledger                             |
//+------------------------------------------------------------------+
#property copyright "Baysix Technologies"
#property version   "0.2.0"          // MUST match GRW_VERSION (grw_types.mqh) — bump both
#property strict

#include <grw_system/grw_types.mqh>
#include <grw_system/grw_version.mqh>   // AUTO-GEN — run gen_version.py grw before compile
#include <grw_system/grw_sizing.mqh>
#include <grw_system/grw_entry.mqh>
#include <grw_system/grw_filter.mqh>
#include <grw_system/grw_exit.mqh>
#include <grw_system/grw_trade.mqh>
#include <grw_system/grw_fitness.mqh>
#include <grw_system/grw_ledger.mqh>

//==================================================================
//  THE FOUR AXES
//==================================================================
input group          "══════  AXIS 1 — ENTRY (where the signal comes from)  ══════"
input GRW_ENTRY InpEntryType  = GRW_E_DONCHIAN_BREAK;  // entry primitive (mechanism per branch)
input int       InpLookback   = 20;      // Donchian window / anchor period / slope span (bars)
input double    InpExtK       = 2.0;     // ATR_REVERSION: fade at >= this many ATRs from anchor
input double    InpSlBufK     = 0.5;     // stop buffer beyond the structural level, in ATRs
input int       InpRetestBars = 5;       // BREAK_RETEST: bars a broken level stays armed

//--- STOP DISTANCE. At the 0.01 min lot (1 oz) a $1 price move is $1, so the stop distance
//--- in USD *is* the risk in USD — the stop is the sizing instrument, not a cosmetic. On $20
//--- the whole viable envelope is a 10-20 pip ($1.00-$2.00) stop at 5-10% risk. ATR_BUF on
//--- H1 lands at ~25 pips median, which is why the $20 smoke run clamped 100% of its orders.
input GRW_SL_MODE InpSlMode    = GRW_SL_ATR_BUF;  // ATR_BUF (structural) · ABS_PIPS (scalp) · STRUCT_CAP
input double      InpSlPips    = 10.0;   // ABS_PIPS: stop distance in pips (10 pips = $1.00 @0.01 lot)
input double      InpSlMaxPips = 20.0;   // STRUCT_CAP: widest structural stop tolerated, in pips

input group          "══════  AXIS 2 — FILTERS (bitmask; ALL selected bits must pass)  ══════"
//--- 1 SESSION · 2 TREND_HTF · 4 VOL_FLOOR · 8 COST_RATIO · 16 NO_ROLLOVER · 31 ALL · 0 baseline
input int       InpFilterMask   = 0;     // sum the bits; 0 = take everything (the baseline)
input int       InpSessStart    = 8;     // SESSION: first broker hour, inclusive
input int       InpSessEnd      = 20;    // SESSION: last broker hour, inclusive (start>end wraps)
input double    InpVolFloorPts  = 0;     // VOL_FLOOR: minimum ATR in POINTS
input double    InpCostMult     = 5.0;   // COST_RATIO: stop must be >= this many live spreads
input int       InpRolloverHr   = 0;     // NO_ROLLOVER: broker hour to sit out

input group          "══════  AXIS 3 — EXIT (how the trade ends)  ══════"
input GRW_EXIT  InpExitType     = GRW_X_FIXED_RR;  // exit primitive
input double    InpRR           = 2.0;   // FIXED_RR: TP = RR * risk
input double    InpArmR         = 1.0;   // TRAIL/BE: R at which management arms
input double    InpTrailAtr     = 1.5;   // TRAIL/BE: trail distance in ATRs (frozen at fill)
input int       InpTimeStopBars = 20;    // TIME_STOP: close after this many signal-TF bars

input group          "══════  AXIS 4 — SIZING (the compounding lever)  ══════"
input double        InpRiskFrac = 0.01;  // fraction of EQUITY risked per trade (0.01 = 1%)
//--- What to do when that fraction asks for less than the broker's minimum lot. NOT a
//--- cosmetic default: FORCE_MIN silently converts the run into a FIXED-LOT strategy, so
//--- the clamp rate is counted and reported by OnTester. See grw_sizing.mqh.
input GRW_UNDERSIZE InpUndersize = GRW_UNDER_FORCE_MIN;  // below min lot: skip, or force min

input group          "══════  PLUMBING  ══════"
input ENUM_TIMEFRAMES InpSignalTf = PERIOD_CURRENT;  // signal TF (PERIOD_CURRENT = chart/tester)
input ENUM_TIMEFRAMES InpHtf      = PERIOD_H4;       // TREND_HTF filter timeframe
input int             InpAtrPeriod = 14;             // ATR period (all ATR uses share it)
input int             InpMaxOpen   = 1;              // max concurrent positions (1 keeps the
                                                     // risk fraction meaning what it says)
input ulong           InpMagic     = 4001;           // GRW magic number
input string          InpBatchId   = "";             // pre-registered batch id, stamped on the CSV

//==================================================================
//  STATE
//==================================================================
GrwCfg      g_cfg;
GrwCtx      g_ctx;
GrwStats    g_stats;
datetime    g_last_bar = 0;
bool        g_ready    = false;

//+------------------------------------------------------------------+
//| OnInit — build the config, create handles, and RESET EVERYTHING.  |
//|                                                                    |
//| The full reset is not defensive padding. MT5 keeps globals alive   |
//| across a recompile or a period switch, so a stale armed break or a |
//| leftover open-book entry survives into the next run and fires a    |
//| phantom trade ([[mt5_oninit_full_reset]]).                         |
//+------------------------------------------------------------------+
int OnInit()
  {
   GrwEntryReset();
   GrwExitReset();
   GrwStatsClear(g_stats);
   g_last_bar = 0;
   g_ready    = false;

   g_cfg.entry_type     = InpEntryType;
   g_cfg.filter_mask    = InpFilterMask;
   g_cfg.exit_type      = InpExitType;
   g_cfg.risk_frac      = InpRiskFrac;
   g_cfg.tf             = (InpSignalTf == PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)Period() : InpSignalTf;
   g_cfg.htf            = InpHtf;
   g_cfg.lookback       = InpLookback;
   g_cfg.ext_k          = InpExtK;
   g_cfg.sl_buf_k       = InpSlBufK;
   g_cfg.retest_bars    = InpRetestBars;
   g_cfg.sl_mode        = InpSlMode;
   g_cfg.sl_pips        = InpSlPips;
   g_cfg.sl_max_pips    = InpSlMaxPips;
   g_cfg.sess_start     = InpSessStart;
   g_cfg.sess_end       = InpSessEnd;
   g_cfg.vol_floor_pts  = InpVolFloorPts;
   g_cfg.cost_mult      = InpCostMult;
   g_cfg.rollover_hr    = InpRolloverHr;
   g_cfg.rr             = InpRR;
   g_cfg.arm_r          = InpArmR;
   g_cfg.trail_atr      = InpTrailAtr;
   g_cfg.time_stop_bars = InpTimeStopBars;
   g_cfg.atr_period     = InpAtrPeriod;
   g_cfg.magic          = InpMagic;

   //--- fail LOUDLY on a nonsensical config rather than producing a clean-looking number
   //--- from a strategy nobody described.
   if(g_cfg.lookback < 2)
     { Print("[GRW] InpLookback must be >= 2"); return INIT_PARAMETERS_INCORRECT; }
   if(g_cfg.risk_frac <= 0.0 || g_cfg.risk_frac > 1.0)
     { Print("[GRW] InpRiskFrac must be in (0, 1]"); return INIT_PARAMETERS_INCORRECT; }
   if(g_cfg.atr_period < 1)
     { Print("[GRW] InpAtrPeriod must be >= 1"); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxOpen < 1)
     { Print("[GRW] InpMaxOpen must be >= 1"); return INIT_PARAMETERS_INCORRECT; }
   if(g_cfg.sl_buf_k < 0.0)
     { Print("[GRW] InpSlBufK must be >= 0"); return INIT_PARAMETERS_INCORRECT; }
   if(g_cfg.sl_mode == GRW_SL_ABS_PIPS && g_cfg.sl_pips <= 0.0)
     { Print("[GRW] ABS_PIPS needs InpSlPips > 0"); return INIT_PARAMETERS_INCORRECT; }
   if(g_cfg.sl_mode == GRW_SL_STRUCT_CAP && g_cfg.sl_max_pips <= 0.0)
     { Print("[GRW] STRUCT_CAP needs InpSlMaxPips > 0"); return INIT_PARAMETERS_INCORRECT; }

   g_ctx.h_atr    = iATR(_Symbol, g_cfg.tf,  g_cfg.atr_period);
   g_ctx.h_anchor = iMA(_Symbol, g_cfg.tf,  g_cfg.lookback, 0, MODE_SMA, PRICE_CLOSE);
   g_ctx.h_htf    = iMA(_Symbol, g_cfg.htf, g_cfg.lookback, 0, MODE_SMA, PRICE_CLOSE);
   if(g_ctx.h_atr == INVALID_HANDLE || g_ctx.h_anchor == INVALID_HANDLE
      || g_ctx.h_htf == INVALID_HANDLE)
     {
      Print("[GRW] indicator handle creation failed");
      return INIT_FAILED;
     }

   //--- provenance on every run: a number produced by a DIRTY tree is not reproducible.
   PrintFormat("[GRW] v%s fitness v%s | git %s%s | built %s",
               GRW_VERSION, GRW_FITNESS_VERSION, GRW_GIT_SHA,
               (GRW_GIT_DIRTY ? "-DIRTY(exploratory)" : ""), GRW_BUILD_TIME);
   PrintFormat("[GRW] entry=%s filters=%s exit=%s risk_frac=%.4f tf=%s htf=%s sl_mode=%s",
               GrwEntryName(g_cfg.entry_type), GrwFilterMaskName(g_cfg.filter_mask),
               GrwExitName(g_cfg.exit_type), g_cfg.risk_frac,
               EnumToString(g_cfg.tf), EnumToString(g_cfg.htf),
               GrwSlModeName(g_cfg.sl_mode));

   //--- FEASIBILITY, stated up front instead of discovered as a 100% clamp rate afterwards.
   //--- With a known stop distance the minimum expressible risk is arithmetic: min lot is
   //--- 0.01 (1 oz), so a 10-pip stop risks exactly $1.00 and a risk_frac of 5% therefore
   //--- needs $20 of equity to be honoured. Below that the pass is a fixed-lot strategy
   //--- wearing a compounding label — which is what grw_smoke_20usd measured.
   if(g_cfg.sl_mode == GRW_SL_ABS_PIPS)
     {
      double mpu  = GrwMoneyPerPricePerLot();
      double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double minrisk = g_cfg.sl_pips * GrwPip() * mpu * vmin;
      if(minrisk > 0.0)
         PrintFormat("[GRW] FEASIBILITY: %.1f-pip stop risks $%.2f at min lot %.2f -> needs "
                     "equity >= $%.2f to express risk_frac=%.4f without clamping (equity now $%.2f)",
                     g_cfg.sl_pips, minrisk, vmin, minrisk / g_cfg.risk_frac,
                     g_cfg.risk_frac, AccountInfoDouble(ACCOUNT_EQUITY));
     }

   g_ready = true;
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(g_ctx.h_atr    != INVALID_HANDLE) IndicatorRelease(g_ctx.h_atr);
   if(g_ctx.h_anchor != INVALID_HANDLE) IndicatorRelease(g_ctx.h_anchor);
   if(g_ctx.h_htf    != INVALID_HANDLE) IndicatorRelease(g_ctx.h_htf);
  }

//+------------------------------------------------------------------+
//| OnTick — two jobs, in this order.                                 |
//|                                                                    |
//|  1. MANAGE open positions on EVERY tick. Trails must see the path, |
//|     not just the closes; that is why real ticks are mandatory.     |
//|  2. On a NEW CLOSED signal-TF bar, evaluate the entry primitive.   |
//|     Detection is close-only and reads shift 1 or older — a forming |
//|     bar is not information yet.                                    |
//+------------------------------------------------------------------+
void OnTick()
  {
   if(!g_ready) return;

   GrwExitManageAll(g_cfg);

   datetime bt = iTime(_Symbol, g_cfg.tf, 0);
   if(bt == 0 || bt == g_last_bar)
      return;                                   // same bar — entry logic runs once per bar
   g_last_bar = bt;

   GrwExitOnNewBar(g_cfg);                      // age positions, apply TIME_STOP
   GrwEntryOnNewBar();                          // age the armed break — MUST run even when
                                                // in a position, or the arm freezes and
                                                // later fires on a stale level

   if(GrwCountOpen(g_cfg.magic) >= InpMaxOpen)
      return;                                   // full — a fresh signal is simply not taken

   GrwSignal s;
   GrwEntryEvaluate(g_cfg, g_ctx, s, g_stats);
   if(!s.valid)
      return;
   g_stats.n_signals++;

   string why = "";
   if(!GrwFilterPass(g_cfg, g_ctx, s, why))
     {
      g_stats.n_gated++;
      return;
     }

   double lots = 0.0, risk_pct = 0.0;
   GrwOpenMarket(g_cfg, s, InpUndersize, g_stats, lots, risk_pct);
  }

//+------------------------------------------------------------------+
//| OnTester — THE OBJECTIVE.                                         |
//|                                                                    |
//| Returns log(final_equity / initial_deposit) per                    |
//| research/config/grw_fitness.json v1.0.0, and writes the two CSVs   |
//| the Python side turns into a grw_passes row. It writes NOTHING to  |
//| research.db: a pass is raw material, not a finding, and the DB is  |
//| reachable only through the code layer (CLAUDE.md rule 10).         |
//+------------------------------------------------------------------+
double OnTester()
  {
   GrwFitness f;
   GrwFitnessCompute(g_stats, f);

   Print(GrwFitnessLine(f));
   PrintFormat("[GRW] signals=%d gated=%d skipped=%d orders=%d sl_too_tight=%d",
               g_stats.n_signals, g_stats.n_gated, g_stats.n_skipped, g_stats.n_orders,
               g_stats.n_sl_too_tight);
   if(g_stats.n_sl_too_tight > 0)
      PrintFormat("[GRW] NOTE: %d signals dropped because the stop was inside the broker's "
                  "min distance or the live spread — the scalp stop is too tight for this venue "
                  "at those moments, not merely unprofitable.", g_stats.n_sl_too_tight);
   if(!f.sizing_valid && g_stats.n_orders > 0)
      PrintFormat("[GRW] WARNING: %.1f%% of orders were forced to the broker minimum lot. "
                  "This pass measured a FIXED-LOT strategy — its growth is NOT a "
                  "compounding claim at risk_frac=%.4f.",
                  100.0 * f.clamp_up_frac, g_cfg.risk_frac);

   string tag = GrwRunTag(InpBatchId);
   GrwWriteRunSummary(tag, g_cfg, g_stats, f, InpBatchId);
   GrwWriteTrades(tag, g_cfg.magic);

   return f.fitness;
  }
