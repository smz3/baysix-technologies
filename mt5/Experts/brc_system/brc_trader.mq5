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
#property version   "1.00"        // keep in lockstep with BRC_VERSION (brc_types.mqh)
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

//--- detection (match emitter run-5: window 3, no age filter)
input int              InpSwingWindow = 3;
input int              InpMaxAge      = 0;
//--- entry module
input BRC_ENTRY_TOUCH  InpEntryTouch  = BRC_ENTRY_L1;          // IS-01
input BRC_ENTRY_SIDE   InpEntrySide   = BRC_CONTINUATION;      // IS-01
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

//+------------------------------------------------------------------+
int OnInit()
  {
   g_radius = BrcSwingRadius(InpSwingWindow);
   if(g_radius < 0)
      return INIT_PARAMETERS_INCORRECT;

   PrintFormat("[BRC TRADER] v%s | git %s%s | built %s | %s",
               BRC_VERSION, BRC_GIT_SHA,
               (BRC_GIT_DIRTY ? "-DIRTY(exploratory)" : ""),
               BRC_BUILD_TIME, EnumToString((ENUM_TIMEFRAMES)_Period));
   PrintFormat("[BRC TRADER] atom: touch=%s side=%s exit=%s maxhold=%d tp=%.2f size=%s lot=%.2f magic=%I64u",
               EnumToString(InpEntryTouch), EnumToString(InpEntrySide),
               EnumToString(InpExitMode), InpMaxHoldBars, InpTpMult,
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
        }
     }

   int before = ArraySize(g_s.breaks);
   BrcDetectBreaksOnBar(g_s.swings, g_s.live_sw, i, bt, cl, g_radius, InpMaxAge, g_s.breaks);
   int after = ArraySize(g_s.breaks);

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
        }
     }

   int na = ArraySize(g_s.alive_idx);
   int w  = 0;
   for(int j = 0; j < na; j++)
     {
      int z = g_s.alive_idx[j];
      if(g_s.zones[z].p4_time < bt)
         BrcAdvanceZone(g_s.zones[z], bt, h, l, cl);
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
                    const string comment)
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
   req.type_time    = ORDER_TIME_GTC;
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
   for(int j = 0; j < ArraySize(g_s.alive_idx); j++)
     {
      BrcZone z = g_s.zones[g_s.alive_idx[j]];
      if(!z.alive || !z.is_primary || z.entered)
         continue;

      BrcEntryPlan plan = BrcBuildEntryPlan(z, InpEntryTouch, InpEntrySide);
      if(!plan.valid)
         continue;

      double lot = BrcLotSize(InpSizeMode, InpFixedLot, InpRiskPct, plan.r_unit);
      bool   is_long = (plan.type == ORDER_TYPE_BUY_LIMIT);
      double tp   = BrcTakeProfitFor(InpExitMode, is_long, plan.entry, plan.r_unit, InpTpMult);

      ulong tk = BrcPlaceLimit(plan.type, lot, plan.entry, plan.sl, tp, z.zone_key);
      if(tk > 0)
        {
         g_pending_ticket = tk;
         g_armed_key      = z.zone_key;
         g_state          = TS_PENDING;
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
      if(!has)                                   // closed by native SL (or TP)
        {
         g_state = TS_FLAT; g_armed_key = ""; g_pending_ticket = 0;
        }
      else if(BrcTimeExitDue(BarsSince(g_entry_time), InpMaxHoldBars))
        {
         BrcClosePosition();                     // clock exit -> market close
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
