//+------------------------------------------------------------------+
//|                                                    brc_trader.mq5  |
//|        BRC TRADER — the strategy EA (sibling of the emitter).      |
//|                                                                    |
//|  Reuses the emitter's exact detection pipeline (swing -> break ->  |
//|  zone -> advance) on a SINGLE TF (the chart TF; run on H1 for      |
//|  IS-01), then trades it via swappable modules:                     |
//|    brc_entry  — where/what to enter (limit at zone level)          |
//|    brc_exit   — when to exit (native SL + time/clock + optional TP)|
//|    brc_sizing — lot (FIXED_LOT 0.01 at $50)                        |
//|                                                                    |
//|  Trust: MT5 tester is the arbiter (CLAUDE.md MT5 Trust rule). All  |
//|  fills are LEVEL-BASED (pending limit at the zone level) so the    |
//|  result is deterministic under the "Open prices only" model. The   |
//|  EA prints its git provenance on init — a DIRTY-tree run is        |
//|  exploratory, not reproducible.                                    |
//|                                                                    |
//|  IS-01 atom: H1 · enter T1=L1 first-retest, continuation ·         |
//|  SL=invalidation(L2) · close at 6 H1 bars · no TP · ONE position.  |
//|  ⚠️ COMPILE-UNTESTED until headless compile passes.                |
//+------------------------------------------------------------------+
#property copyright "Baysix Technologies"
#property version   "1.10"        // keep in lockstep with BRC_VERSION (brc_types.mqh)
#property strict

#include <brc_system/brc_types.mqh>
#include <brc_system/brc_version.mqh>
#include <brc_system/brc_swings.mqh>
#include <brc_system/brc_breakouts.mqh>
#include <brc_system/brc_zones.mqh>
#include <brc_system/brc_lifecycle.mqh>
#include <brc_system/brc_entry.mqh>
#include <brc_system/brc_exit.mqh>
#include <brc_system/brc_sizing.mqh>
#include <brc_system/brc_visual.mqh>    // chart eyeball layer (shared with the emitter; InpVisualize master toggle)

//--- detection (match emitter run-5: window 3, no age filter)
input int              InpSwingWindow = 3;
input int              InpMaxAge      = 0;
//--- entry module
input BRC_ENTRY_TOUCH  InpEntryTouch  = BRC_ENTRY_L1;          // IS-01
input BRC_ENTRY_SIDE   InpEntrySide   = BRC_CONTINUATION;      // IS-01
//--- T1-limit expiry: cancel the resting limit this many HOURS after the break
//    (P4). 72h chosen from the emitted P4->T1 retest-lag distribution (8.5yr H1
//    primary zones, 2026-06-23): keeps ~86% of retests, drops the stale tail,
//    frees the single slot (the 1.2% never-retested zones were the 3-trade bug).
//    0 = GTC (legacy, never expires).
input int              InpRetestExpiryHrs = 72;                // IS-01
//--- exit module
input BRC_EXIT_MODE    InpExitMode    = BRC_EXIT_TIME;         // IS-01
input int              InpMaxHoldBars = 6;                     // IS-01
input double           InpTpMult      = 0.0;                   // IS-01 (no TP)
//--- sizing module
input BRC_SIZE_MODE    InpSizeMode    = BRC_SIZE_FIXED_LOT;    // IS-01
input double           InpFixedLot    = 0.01;                  // $50 min-lot floor
input double           InpRiskPct     = 1.0;                   // FIXED_FRAC only
//--- execution
input ulong            InpMagic       = 2001;                  // BRC trader magic
//--- trade visuals (eyeball: do entries land on the zone level?). Needs tester
//    Visual Mode; gated under InpVisualize (the emitter's master toggle).
input bool             InpBrcShowTrades = true;                // draw entry/SL/TP/exit markers

//+------------------------------------------------------------------+
//| Single-TF detection state (mirror of the emitter's TfState).     |
//+------------------------------------------------------------------+
struct TraderState
  {
   datetime last_time;
   datetime bt[];   double bh[];  double bl[];  double bc[];
   BrcSwing swings[];
   BrcBreak breaks[];
   BrcZone  zones[];
   int      live_sw[];
   int      alive_idx[];
   int      zone_seq;
  };

//--- one-position state machine
enum TRADE_STATE { TS_FLAT = 0, TS_PENDING = 1, TS_INPOS = 2 };

TraderState g_s;
int         g_radius   = 1;
TRADE_STATE g_state    = TS_FLAT;
string      g_armed_key = "";       // zone_key we placed the pending order for
ulong       g_pending_ticket = 0;
datetime    g_entry_time = 0;       // position open time (for bar counting)

//--- visuals
CBrcVisual  g_vis;                  // shared zone visualizer (no-op unless InpVisualize)
string      g_vistf  = "";          // chart TF short name ("H1"); "" if unmapped
bool        g_trade_drawn = false;  // entry/level markers drawn for the current position

//--- trade-marker object stems (own prefix so brc_visual's ClearAll never wipes them)
#define BRC_TR_PREFIX "BRC_TR_"

//--- per-trade ledger: position_id -> 1R unit (range_w = |entry - SL|), captured at
//    ARM time (task 138) keyed on the pending-order ticket. In MT5 the triggered
//    position's identifier == that ticket, so OnDeinit recovers range_w even for
//    same-bar fill+SL trades that ManageTrades() (bar-close cadence) never sees as
//    TS_INPOS — the 31% instant-SL cohort that previously logged realized_R=0.
//    Auto-written to a CSV on deinit -> no manual MT5 "Export XLSX" step (task 43).
long       g_pid[];                 // position identifiers (== arming pending ticket)
double     g_rw[];                  // matching 1R unit for that position
string     g_zk[];                  // matching zone_key for that position

//--- short TF name matching CBrcVisual::PeriodName (visualizer is chart-TF gated).
string TraderTfName()
  {
   switch((ENUM_TIMEFRAMES)_Period)
     {
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30";
      case PERIOD_H1:  return "H1";
      case PERIOD_H4:  return "H4";
      case PERIOD_D1:  return "D1";
      case PERIOD_W1:  return "W1";
      case PERIOD_MN1: return "MN1";
     }
   return "";
  }

//+------------------------------------------------------------------+
//| Trade-marker drawing (eyeball the fill against the zone level).   |
//| Own object prefix BRC_TR_ so CBrcVisual::ClearAll never wipes it. |
//| Markers persist per trade (keyed on entry time) so a whole replay |
//| can be scrolled back and audited zone-by-zone.                   |
//+------------------------------------------------------------------+
void TrLine(const string name, const datetime t0, const double p0,
            const datetime t1, const double p1, const color clr, const ENUM_LINE_STYLE st)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TREND, 0, t0, p0, t1, p1);
   ObjectMove(0, name, 0, t0, p0);
   ObjectMove(0, name, 1, t1, p1);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, st);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
  }

void DrawTradeEntry(const datetime t_entry, const double entry, const double sl,
                    const double tp, const bool is_long)
  {
   if(!InpVisualize || !InpBrcShowTrades)
      return;
   string   stem = BRC_TR_PREFIX + (string)t_entry;
   datetime t1   = t_entry + (datetime)(PeriodSeconds((ENUM_TIMEFRAMES)_Period) * (InpMaxHoldBars + 2));

   //--- entry arrow at the fill
   string an = stem + "_e";
   if(ObjectFind(0, an) < 0)
      ObjectCreate(0, an, OBJ_ARROW, 0, t_entry, entry);
   ObjectMove   (0, an, 0, t_entry, entry);
   ObjectSetInteger(0, an, OBJPROP_ARROWCODE, is_long ? 233 : 234);   // up / down arrow
   ObjectSetInteger(0, an, OBJPROP_COLOR, is_long ? clrAqua : clrMagenta);
   ObjectSetInteger(0, an, OBJPROP_ANCHOR, is_long ? ANCHOR_TOP : ANCHOR_BOTTOM);
   ObjectSetInteger(0, an, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, an, OBJPROP_HIDDEN, true);

   //--- entry / SL / TP level segments spanning the holding window
   TrLine(stem + "_eL", t_entry, entry, t1, entry, clrGold, STYLE_SOLID);
   TrLine(stem + "_sL", t_entry, sl,    t1, sl,    clrRed,  STYLE_DASH);
   if(tp > 0.0)
      TrLine(stem + "_tL", t_entry, tp, t1, tp, clrLimeGreen, STYLE_DASH);

   //--- fill label (price the EA actually got, to compare against the L1 line)
   string ln = stem + "_lbl";
   if(ObjectFind(0, ln) < 0)
      ObjectCreate(0, ln, OBJ_TEXT, 0, t_entry, entry);
   ObjectMove   (0, ln, 0, t_entry, entry);
   ObjectSetString (0, ln, OBJPROP_TEXT, StringFormat("  %s fill %s",
                    (is_long ? "BUY" : "SELL"), DoubleToString(entry, _Digits)));
   ObjectSetString (0, ln, OBJPROP_FONT, "Calibri Light");
   ObjectSetInteger(0, ln, OBJPROP_FONTSIZE, 8);
   ObjectSetInteger(0, ln, OBJPROP_ANCHOR, is_long ? ANCHOR_LEFT_LOWER : ANCHOR_LEFT_UPPER);
   ObjectSetInteger(0, ln, OBJPROP_COLOR, clrGold);
   ObjectSetInteger(0, ln, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, ln, OBJPROP_HIDDEN, true);
  }

void DrawTradeExit(const datetime t_entry, const datetime t_exit, const double price)
  {
   if(!InpVisualize || !InpBrcShowTrades)
      return;
   string xn = BRC_TR_PREFIX + (string)t_entry + "_x";
   if(ObjectFind(0, xn) < 0)
      ObjectCreate(0, xn, OBJ_ARROW, 0, t_exit, price);
   ObjectMove   (0, xn, 0, t_exit, price);
   ObjectSetInteger(0, xn, OBJPROP_ARROWCODE, 251);   // small "x"
   ObjectSetInteger(0, xn, OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, xn, OBJPROP_ANCHOR, ANCHOR_CENTER);
   ObjectSetInteger(0, xn, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, xn, OBJPROP_HIDDEN, true);
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   g_radius = BrcSwingRadius(InpSwingWindow);
   if(g_radius < 0)
      return INIT_PARAMETERS_INCORRECT;

   g_vistf = TraderTfName();
   g_vis.SyncChartTF();
   g_vis.ClearAll();
   ObjectsDeleteAll(0, BRC_TR_PREFIX);   // wipe trade markers from any prior run

   PrintFormat("[BRC TRADER] v%s | git %s%s | built %s | %s",
               BRC_VERSION, BRC_GIT_SHA,
               (BRC_GIT_DIRTY ? "-DIRTY(exploratory)" : ""),
               BRC_BUILD_TIME, EnumToString((ENUM_TIMEFRAMES)_Period));
   PrintFormat("[BRC TRADER] atom: touch=%s side=%s exit=%s maxhold=%d tp=%.2f expiry=%dh size=%s lot=%.2f magic=%I64u",
               EnumToString(InpEntryTouch), EnumToString(InpEntrySide),
               EnumToString(InpExitMode), InpMaxHoldBars, InpTpMult, InpRetestExpiryHrs,
               EnumToString(InpSizeMode), InpFixedLot, InpMagic);
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Task 127 helpers copied from the emitter so the trader's primary |
//| set matches the run-5 ledger (trade only is_primary zones).      |
//+------------------------------------------------------------------+
string BrcMakeZoneKey(const string tf, const BrcZone &zones[], const int zi)
  {
   string dir  = (zones[zi].direction == BRC_BEAR) ? "SELL" : "BUY";
   string base = tf + "|" + dir + "|" + IntegerToString((long)zones[zi].p4_time);
   for(int e = 0; e < zi; e++)
      if(zones[e].zone_key == base)
         return base + "|" + DoubleToString(zones[zi].l2, 3);
   return base;
  }

void BrcConsolidateNewZone(TraderState &s, const int zi)
  {
   double top_n = MathMax(s.zones[zi].l1, s.zones[zi].l2);
   double bot_n = MathMin(s.zones[zi].l1, s.zones[zi].l2);
   double range_n = top_n - bot_n;
   if(range_n <= 0)
      return;

   int na = ArraySize(s.alive_idx);
   for(int j = 0; j < na; j++)
     {
      int ez = s.alive_idx[j];
      if(ez == zi || !s.zones[ez].is_primary)
         continue;
      if(s.zones[ez].direction != s.zones[zi].direction)
         continue;

      double top_e = MathMax(s.zones[ez].l1, s.zones[ez].l2);
      double bot_e = MathMin(s.zones[ez].l1, s.zones[ez].l2);
      double range_e = top_e - bot_e;
      if(range_e <= 0)
         continue;

      double itop = MathMin(top_n, top_e);
      double ibot = MathMax(bot_n, bot_e);
      double inter = (itop > ibot) ? (itop - ibot) : 0;
      if(inter <= 0)
         continue;

      double pct = (inter / MathMin(range_n, range_e)) * 100.0;
      if(pct < 50.0)
         continue;

      if(range_n >= range_e)
        {
         s.zones[ez].is_primary        = false;
         s.zones[ez].consolidated_into = s.zones[zi].zone_key;
        }
      else
        {
         s.zones[zi].is_primary        = false;
         s.zones[zi].consolidated_into = s.zones[ez].zone_key;
         return;
        }
     }
  }

//+------------------------------------------------------------------+
//| Ingest one closed bar: swing -> break -> zone confirm -> advance.|
//| Byte-identical pipeline to the emitter (minus visuals/CSV).      |
//+------------------------------------------------------------------+
void IngestBar(const datetime bt, const double h, const double l, const double cl)
  {
   int i = ArraySize(g_s.bt);
   ArrayResize(g_s.bt, i + 1, 4096);
   ArrayResize(g_s.bh, i + 1, 4096);
   ArrayResize(g_s.bl, i + 1, 4096);
   ArrayResize(g_s.bc, i + 1, 4096);
   g_s.bt[i] = bt; g_s.bh[i] = h; g_s.bl[i] = l; g_s.bc[i] = cl;
   int n = i + 1;

   int p = i - g_radius;
   if(p >= 0)
     {
      BrcSwing sw;
      if(BrcDetectSwingAt(g_s.bt, g_s.bc, n, p, g_radius, sw))
        {
         int si = ArraySize(g_s.swings);
         ArrayResize(g_s.swings, si + 1, 512);
         g_s.swings[si] = sw;
         int li = ArraySize(g_s.live_sw);
         ArrayResize(g_s.live_sw, li + 1, 512);
         g_s.live_sw[li] = si;
         g_vis.OnSwing(g_vistf, sw);
        }
     }

   int before = ArraySize(g_s.breaks);
   BrcDetectBreaksOnBar(g_s.swings, g_s.live_sw, i, bt, cl, g_radius, InpMaxAge, g_s.breaks);
   int after = ArraySize(g_s.breaks);
   for(int b = before; b < after; b++)
      g_vis.OnBreak(g_vistf, g_s.breaks[b]);

   for(int k = before; k < after; k++)
     {
      BrcZone z;
      if(BrcTryConfirmZone(g_s.breaks[k], g_s.swings, g_s.breaks, g_s.bc, n, g_s.zones, z))
        {
         int zi = ArraySize(g_s.zones);
         ArrayResize(g_s.zones, zi + 1, 256);
         g_s.zones[zi] = z;
         int ai = ArraySize(g_s.alive_idx);
         ArrayResize(g_s.alive_idx, ai + 1, 256);
         g_s.alive_idx[ai] = zi;
         g_s.zones[zi].seq               = ++g_s.zone_seq;
         g_s.zones[zi].zone_key          = BrcMakeZoneKey(EnumToString((ENUM_TIMEFRAMES)_Period), g_s.zones, zi);
         g_s.zones[zi].is_primary        = true;
         g_s.zones[zi].consolidated_into = "";
         BrcConsolidateNewZone(g_s, zi);
         g_vis.OnZoneConfirmed(g_vistf, g_s.zones[zi]);
        }
     }

   int na = ArraySize(g_s.alive_idx);
   int w  = 0;
   for(int j = 0; j < na; j++)
     {
      int z = g_s.alive_idx[j];
      if(g_s.zones[z].p4_time < bt)
        {
         BrcAdvanceZone(g_s.zones[z], bt, h, l, cl);
         g_vis.OnZoneAdvanced(g_vistf, g_s.zones[z]);
        }
      if(g_s.zones[z].alive)
         g_s.alive_idx[w++] = g_s.alive_idx[j];
     }
   ArrayResize(g_s.alive_idx, w);
  }

//+------------------------------------------------------------------+
//| Raw trade API (self-contained; avoids the standard-library CTrade |
//| dependency so the EA compiles against the repo include tree).    |
//+------------------------------------------------------------------+
ENUM_ORDER_TYPE_FILLING BrcFilling()
  {
   long mode = (long)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((mode & SYMBOL_FILLING_FOK) != 0) return ORDER_FILLING_FOK;
   if((mode & SYMBOL_FILLING_IOC) != 0) return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
  }

ulong BrcPlaceLimit(const ENUM_ORDER_TYPE type, const double volume,
                    const double price, const double sl, const double tp,
                    const string comment, const datetime expiration)
  {
   MqlTradeRequest req;  MqlTradeResult res;
   ZeroMemory(req);  ZeroMemory(res);
   req.action       = TRADE_ACTION_PENDING;
   req.symbol       = _Symbol;
   req.magic        = InpMagic;
   req.type         = type;
   req.volume       = volume;
   req.price        = NormalizeDouble(price, _Digits);
   req.sl           = NormalizeDouble(sl, _Digits);
   req.tp           = (tp > 0.0) ? NormalizeDouble(tp, _Digits) : 0.0;
   if(expiration > 0)
     { req.type_time = ORDER_TIME_SPECIFIED; req.expiration = expiration; }
   else
      req.type_time = ORDER_TIME_GTC;
   req.type_filling = ORDER_FILLING_RETURN;
   req.comment      = comment;
   if(!OrderSend(req, res))
      return 0;
   if(res.retcode != TRADE_RETCODE_DONE && res.retcode != TRADE_RETCODE_PLACED)
      return 0;
   return res.order;
  }

bool BrcDeleteOrder(const ulong ticket)
  {
   MqlTradeRequest req;  MqlTradeResult res;
   ZeroMemory(req);  ZeroMemory(res);
   req.action = TRADE_ACTION_REMOVE;
   req.order  = ticket;
   return OrderSend(req, res);
  }

bool BrcClosePosition()
  {
   if(!PositionSelect(_Symbol))
      return false;
   ulong  ticket = (ulong)PositionGetInteger(POSITION_TICKET);
   long   ptype  = PositionGetInteger(POSITION_TYPE);
   double vol    = PositionGetDouble(POSITION_VOLUME);
   ENUM_ORDER_TYPE otype = (ptype == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   double price = (otype == ORDER_TYPE_SELL)
                  ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                  : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   MqlTradeRequest req;  MqlTradeResult res;
   ZeroMemory(req);  ZeroMemory(res);
   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = _Symbol;
   req.magic        = InpMagic;
   req.position     = ticket;
   req.type         = otype;
   req.volume       = vol;
   req.price        = NormalizeDouble(price, _Digits);
   req.deviation    = 50;
   req.type_filling = BrcFilling();
   if(!OrderSend(req, res))
      return false;
   return (res.retcode == TRADE_RETCODE_DONE);
  }

//+------------------------------------------------------------------+
//| Is there an open position belonging to this EA?                  |
//+------------------------------------------------------------------+
bool HasPosition(datetime &open_time)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
        {
         open_time = (datetime)PositionGetInteger(POSITION_TIME);
         return true;
        }
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Find an alive zone by key; return its alive flag (false if gone).|
//+------------------------------------------------------------------+
bool ZoneAliveByKey(const string key)
  {
   for(int j = ArraySize(g_s.alive_idx) - 1; j >= 0; j--)
      if(g_s.zones[g_s.alive_idx[j]].zone_key == key)
         return g_s.zones[g_s.alive_idx[j]].alive;
   return false;   // not in the alive set anymore
  }

//+------------------------------------------------------------------+
//| Closed bars elapsed since the position opened (for time exit).   |
//+------------------------------------------------------------------+
int BarsSince(const datetime t0)
  {
   int c = 0;
   for(int j = ArraySize(g_s.bt) - 1; j >= 0 && g_s.bt[j] > t0; j--)
      c++;
   return c;
  }

//+------------------------------------------------------------------+
//| Arm the first eligible alive, primary, not-yet-entered zone.     |
//+------------------------------------------------------------------+
void TryArm()
  {
   datetime now   = g_s.last_time;
   long     win_s = (long)InpRetestExpiryHrs * 3600;
   //--- freshest-first: the newest P4 (end of the formation-ordered alive set)
   //    wins, so the slot tracks the live break, not the stalest zone. Skip any
   //    zone already past its retest window (arming it = an already-expired order
   //    + it was the single-slot starver — see the 8.5yr P4->T1 lag analysis).
   for(int j = ArraySize(g_s.alive_idx) - 1; j >= 0; j--)
     {
      BrcZone z = g_s.zones[g_s.alive_idx[j]];
      if(!z.alive || !z.is_primary || z.entered)
         continue;
      if(win_s > 0 && (long)(now - z.p4_time) >= win_s)
         continue;

      BrcEntryPlan plan = BrcBuildEntryPlan(z, InpEntryTouch, InpEntrySide);
      if(!plan.valid)
         continue;

      double   lot     = BrcLotSize(InpSizeMode, InpFixedLot, InpRiskPct, plan.r_unit);
      bool     is_long = (plan.type == ORDER_TYPE_BUY_LIMIT);
      double   tp      = BrcTakeProfitFor(InpExitMode, is_long, plan.entry, plan.r_unit, InpTpMult);
      datetime expiry  = (win_s > 0) ? (datetime)(z.p4_time + win_s) : (datetime)0;

      ulong tk = BrcPlaceLimit(plan.type, lot, plan.entry, plan.sl, tp, z.zone_key, expiry);
      if(tk > 0)
        {
         g_pending_ticket = tk;
         g_armed_key      = z.zone_key;
         g_state          = TS_PENDING;
         //--- stash 1R + zone_key at ARM keyed on the pending ticket (== future
         //    position_id). Captures the instant same-bar SL cohort that the
         //    bar-close ManageTrades() fill-detect would miss (task 138).
         int m = ArraySize(g_pid);
         ArrayResize(g_pid, m + 1);  ArrayResize(g_rw, m + 1);  ArrayResize(g_zk, m + 1);
         g_pid[m] = (long)tk;
         g_rw[m]  = plan.r_unit;
         g_zk[m]  = z.zone_key;
        }
      return;   // one at a time
     }
  }

//+------------------------------------------------------------------+
//| Run the one-position state machine once per newly closed bar.    |
//+------------------------------------------------------------------+
void ManageTrades()
  {
   datetime ptime = 0;
   bool has = HasPosition(ptime);

   if(g_state == TS_PENDING)
     {
      if(has)                                   // pending limit filled -> in position
        {
         g_state      = TS_INPOS;
         g_entry_time = ptime;
         if(PositionSelect(_Symbol))            // draw the fill against the zone level
           {
            bool   is_long = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
            double entry   = PositionGetDouble(POSITION_PRICE_OPEN);
            double sl      = PositionGetDouble(POSITION_SL);
            DrawTradeEntry(ptime, entry, sl,
                           PositionGetDouble(POSITION_TP), is_long);
            g_trade_drawn = true;
            //--- range_w / zone_key already stashed at ARM (task 138), keyed on the
            //    pending ticket == this position's identifier.
           }
        }
      else if(!OrderSelect(g_pending_ticket))   // pending gone (expired/removed)
        {
         g_state = TS_FLAT; g_armed_key = ""; g_pending_ticket = 0;
        }
      else if(!ZoneAliveByKey(g_armed_key))     // zone invalidated before fill -> cancel
        {
         BrcDeleteOrder(g_pending_ticket);
         g_state = TS_FLAT; g_armed_key = ""; g_pending_ticket = 0;
        }
     }

   if(g_state == TS_INPOS)
     {
      int last = ArraySize(g_s.bc) - 1;
      double px = (last >= 0) ? g_s.bc[last] : 0.0;   // bar close = exit ref under open-prices model
      if(!has)                                   // closed by native SL (or TP)
        {
         if(g_trade_drawn) DrawTradeExit(g_entry_time, g_s.last_time, px);
         g_trade_drawn = false;
         g_state = TS_FLAT; g_armed_key = ""; g_pending_ticket = 0;
        }
      else if(BrcTimeExitDue(BarsSince(g_entry_time), InpMaxHoldBars))
        {
         BrcClosePosition();                     // clock exit -> market close
         if(g_trade_drawn) DrawTradeExit(g_entry_time, g_s.last_time, px);
         g_trade_drawn = false;
         g_state = TS_FLAT; g_armed_key = ""; g_pending_ticket = 0;
        }
     }

   if(g_state == TS_FLAT && !has)
      TryArm();
  }

//+------------------------------------------------------------------+
//| On each tick, ingest any newly CLOSED bar of the chart TF, then  |
//| run trade management once per new bar.                           |
//+------------------------------------------------------------------+
void OnTick()
  {
   MqlRates r[];
   ArraySetAsSeries(r, true);
   int got = CopyRates(_Symbol, (ENUM_TIMEFRAMES)_Period, 1, 64, r);
   if(got <= 0)
      return;

   bool new_bar = false;
   for(int k = got - 1; k >= 0; k--)
     {
      if(r[k].time <= g_s.last_time)
         continue;
      IngestBar(r[k].time, r[k].high, r[k].low, r[k].close);
      g_s.last_time = r[k].time;
      new_bar = true;
     }

   if(new_bar)
      ManageTrades();
  }

//+------------------------------------------------------------------+
//| Chart period switched -> rebuild the zone layer for the new TF.  |
//| Trade markers (BRC_TR_) are absolute price/time and survive.     |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(id != CHARTEVENT_CHART_CHANGE)
      return;
   g_vistf = TraderTfName();
   g_vis.SyncChartTF();
   g_vis.RedrawCurrentTF(g_vistf,
                         g_s.swings, ArraySize(g_s.swings),
                         g_s.breaks, ArraySize(g_s.breaks),
                         g_s.zones,  ArraySize(g_s.zones));
  }

//+------------------------------------------------------------------+
//| Map a closed position's id -> its captured 1R unit / zone_key.   |
//+------------------------------------------------------------------+
double RangeWForPos(const long pid, string &zkey)
  {
   for(int i = ArraySize(g_pid) - 1; i >= 0; i--)
      if(g_pid[i] == pid)
        { zkey = g_zk[i]; return g_rw[i]; }
   zkey = "";
   return 0.0;
  }

//+------------------------------------------------------------------+
//| Max favorable / adverse excursion over a trade's hold, measured  |
//| on the WORKING timeframe (_Period). The open-prices tester model |
//| only materialises the chart TF — sub-TF (M5) + ticks come back   |
//| empty, and OnTick is bar-open-only, so this model is path-blind  |
//| intrabar by design. So MFE/MAE here = excursion ACROSS THE HOLD  |
//| at bar resolution: faithful for multi-bar TIME runners (steers   |
//| trail/BE/max-hold); the entry bar's H/L includes pre-fill move   |
//| (modest overstatement), and same-bar SL trades collapse to one   |
//| bar — their true intrabar path needs a real-tick run (task 136). |
//| SIGNED in price + R: favorable = move in trade dir, adverse =    |
//| against. Negative MFE = never traded past entry.                 |
//+------------------------------------------------------------------+
void ExcursionForTrade(const datetime entry_ts, const datetime exit_ts, const int dir,
                       const double entry_px, const double rw,
                       double &mfe_px, double &mae_px, double &mfe_r, double &mae_r)
  {
   mfe_px = 0.0; mae_px = 0.0; mfe_r = 0.0; mae_r = 0.0;
   MqlRates r[];
   ArraySetAsSeries(r, false);
   datetime t1 = (exit_ts > entry_ts) ? exit_ts : entry_ts + PeriodSeconds((ENUM_TIMEFRAMES)_Period);
   int got = CopyRates(_Symbol, (ENUM_TIMEFRAMES)_Period, entry_ts, t1, r);
   if(got <= 0)
      return;
   double hi = -DBL_MAX, lo = DBL_MAX;
   for(int k = 0; k < got; k++)
     {
      if(r[k].high > hi) hi = r[k].high;
      if(r[k].low  < lo) lo = r[k].low;
     }
   if(dir > 0)  // long: favorable = up, adverse = down
     { mfe_px = hi - entry_px;  mae_px = entry_px - lo; }
   else         // short: favorable = down, adverse = up
     { mfe_px = entry_px - lo;  mae_px = hi - entry_px; }
   if(rw > 0.0)
     { mfe_r = mfe_px / rw;  mae_r = mae_px / rw; }
  }

//+------------------------------------------------------------------+
//| Human-readable exit reason from the closing deal's DEAL_REASON.  |
//| SL / TP are broker-native; EXPERT = our clock/time-exit close.  |
//+------------------------------------------------------------------+
string ExitReasonName(const long reason)
  {
   switch((ENUM_DEAL_REASON)reason)
     {
      case DEAL_REASON_SL: return "SL";
      case DEAL_REASON_TP: return "TP";
      case DEAL_REASON_SO: return "SO";        // stop-out (margin)
      case DEAL_REASON_EXPERT: return "TIME";  // EA market-close = our clock exit
     }
   return "OTHER";
  }

//+------------------------------------------------------------------+
//| Write the per-trade ledger CSV from the tester's deal history.   |
//| One row per CLOSED position (paired IN->OUT deal), with exact    |
//| entry/exit time+price, PnL, broker exit reason, and realized_R   |
//| (using the 1R unit stashed at fill). Auto-runs on deinit so the  |
//| trade ledger never depends on a manual MT5 "Export XLSX". File   |
//| lands in Common\Files\BRC alongside the emitter's zone CSVs.     |
//+------------------------------------------------------------------+
void WriteTradeLedger()
  {
   if(!HistorySelect(0, TimeCurrent()))
      return;
   int total = HistoryDealsTotal();
   if(total <= 0)
      return;

   //--- pass 1: index the entry (IN) deals by position id
   long     in_pid[];   datetime in_time[];  double in_px[];  double in_lot[];  int in_dir[];
   for(int i = 0; i < total; i++)
     {
      ulong tk = HistoryDealGetTicket(i);
      if((long)HistoryDealGetInteger(tk, DEAL_MAGIC) != (long)InpMagic)
         continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(tk, DEAL_ENTRY) != DEAL_ENTRY_IN)
         continue;
      int n = ArraySize(in_pid);
      ArrayResize(in_pid, n+1); ArrayResize(in_time, n+1); ArrayResize(in_px, n+1);
      ArrayResize(in_lot, n+1); ArrayResize(in_dir, n+1);
      in_pid[n]  = (long)HistoryDealGetInteger(tk, DEAL_POSITION_ID);
      in_time[n] = (datetime)HistoryDealGetInteger(tk, DEAL_TIME);
      in_px[n]   = HistoryDealGetDouble(tk, DEAL_PRICE);
      in_lot[n]  = HistoryDealGetDouble(tk, DEAL_VOLUME);
      //--- DEAL_TYPE of the IN deal: BUY in = long, SELL in = short
      in_dir[n]  = (HistoryDealGetInteger(tk, DEAL_TYPE) == DEAL_TYPE_BUY) ? 1 : -1;
     }

   //--- open the CSV (Common\Files\BRC, named like the zone files)
   //--- sanitize the stamp/version SEPARATELY so we don't eat the ".csv" dot
   string stamp = TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES);  // "2024.06.28 23:59"
   StringReplace(stamp, ".", "");  StringReplace(stamp, ":", "");  StringReplace(stamp, " ", "_");
   string ver = BRC_VERSION;       StringReplace(ver, ".", "");
   string fname = StringFormat("BRC\\brc_trades_%s_v%s_%s.csv", _Symbol, ver, stamp);
   int h = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE)
     {
      PrintFormat("BRC ledger: FileOpen failed (%d) for %s", GetLastError(), fname);
      return;
     }
   FileWrite(h, "position_id","direction","entry_ts","entry_px","exit_ts","exit_px",
             "exit_reason","lots","range_w","realized_r","realized_pnl_usd",
             "mfe_px","mae_px","mfe_r","mae_r","zone_key");

   //--- pass 2: emit one row per OUT deal, paired to its IN
   int rows = 0;
   for(int i = 0; i < total; i++)
     {
      ulong tk = HistoryDealGetTicket(i);
      if((long)HistoryDealGetInteger(tk, DEAL_MAGIC) != (long)InpMagic)
         continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(tk, DEAL_ENTRY) != DEAL_ENTRY_OUT)
         continue;

      long     pid      = (long)HistoryDealGetInteger(tk, DEAL_POSITION_ID);
      datetime exit_ts  = (datetime)HistoryDealGetInteger(tk, DEAL_TIME);
      double   exit_px  = HistoryDealGetDouble(tk, DEAL_PRICE);
      double   pnl      = HistoryDealGetDouble(tk, DEAL_PROFIT)
                          + HistoryDealGetDouble(tk, DEAL_SWAP)
                          + HistoryDealGetDouble(tk, DEAL_COMMISSION);
      string   reason   = ExitReasonName(HistoryDealGetInteger(tk, DEAL_REASON));

      //--- find the matching IN deal
      datetime entry_ts = 0;  double entry_px = 0, lots = 0;  int dir = 0;
      for(int j = ArraySize(in_pid) - 1; j >= 0; j--)
         if(in_pid[j] == pid)
           { entry_ts = in_time[j]; entry_px = in_px[j]; lots = in_lot[j]; dir = in_dir[j]; break; }

      string zkey  = "";
      double rw    = RangeWForPos(pid, zkey);
      double rR    = (rw > 0.0) ? (dir * (exit_px - entry_px) / rw) : 0.0;

      double mfe_px, mae_px, mfe_r, mae_r;
      ExcursionForTrade(entry_ts, exit_ts, dir, entry_px, rw, mfe_px, mae_px, mfe_r, mae_r);

      FileWrite(h, (string)pid, (dir > 0 ? "BUY" : "SELL"),
                TimeToString(entry_ts, TIME_DATE|TIME_SECONDS), DoubleToString(entry_px, _Digits),
                TimeToString(exit_ts,  TIME_DATE|TIME_SECONDS), DoubleToString(exit_px, _Digits),
                reason, DoubleToString(lots, 2), DoubleToString(rw, _Digits),
                DoubleToString(rR, 4), DoubleToString(pnl, 2),
                DoubleToString(mfe_px, _Digits), DoubleToString(mae_px, _Digits),
                DoubleToString(mfe_r, 4), DoubleToString(mae_r, 4), zkey);
      rows++;
     }
   FileClose(h);
   PrintFormat("BRC ledger: wrote %d trades -> Common\\Files\\%s", rows, fname);
  }

//+------------------------------------------------------------------+
//| Detach / recompile / chart-close -> wipe drawn objects, and on   |
//| a tester run write the per-trade ledger CSV (no manual export).  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   WriteTradeLedger();
   g_vis.ClearAll();
   ObjectsDeleteAll(0, BRC_TR_PREFIX);
  }
//+------------------------------------------------------------------+
