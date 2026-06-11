//+------------------------------------------------------------------+
//|                                          baysix_orb_001.mq5       |
//|                          Copyright 2026, Baysix Technologies      |
//+------------------------------------------------------------------+
//| ORB-001 — Opening-Range Breakout, XAUUSD, STANDALONE EA.         |
//|                                                                  |
//| Validated Gates 0-6 OOS on Dukascopy. FROZEN LIVE CONFIG         |
//| (research.db strategy_log.get_live_config('ORB-001')):           |
//|   anchor 09:00 UTC / N=5 min OR / immediate breakout /            |
//|   trail_1R exit / Mode-A min-lot, 5% risk-skip cap.               |
//|                                                                  |
//| Deliberately ISOLATED from the live Sigma B2B EA: own magic       |
//| (1001), own chart, no shared state. A bug here cannot touch the   |
//| B2B money-maker. Comment "ORB001" + magic 1001 let execution.db's |
//| D1 fill adapter reconcile these trades.                           |
//|                                                                  |
//| Strategy per UTC session:                                         |
//|   1. Build the opening range over [09:00, 09:05) UTC from M1 bars |
//|      (bar high/low). range_w = OR_high - OR_low = 1R.             |
//|   2. After 09:05, take the FIRST breakout (immediate, intra-bar): |
//|      bid >= OR_high -> long @ market; bid <= OR_low -> short.     |
//|      One trade per session, direction = first breach.            |
//|   3. Stop = opposite OR boundary (risk = range_w). Exit = trail_1R|
//|      trailing stop at distance range_w behind peak excursion.     |
//|   4. EOD-flat at 21:00 UTC (swap-free + flat = no overnight).     |
//|   5. Sizing: fixed min-lot; SKIP the trade if its $ risk          |
//|      (range_w * 100 * lot) exceeds InpRiskCapPct % of equity.     |
//|                                                                  |
//| Time base: anchors are UTC. LIVE -> TimeGMT() (correct on a PC    |
//| with a correct clock). STRATEGY TESTER -> TimeGMT() is unreliable; |
//| we treat the custom Dukascopy symbol as UTC-stamped (exported      |
//| "Original" = UTC) so server time IS UTC -> offset 0. On a VPS with |
//| a skewed clock, set InpUTCOffsetOverrideHours to server->UTC hrs.  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Baysix Technologies"
#property version   "1.00"
#property strict
#property description "ORB-001 standalone — 09:00 UTC opening-range breakout, trail_1R, XAUUSD"

#include <Trade/Trade.mqh>
#include <orb_system/orb_visualizer.mqh>

//--- Inputs (frozen live config; defaults = the validated values) ---
input long   InpMagic                  = 1001;        // Magic number (ORB family base 1000 + 1)
input int    InpAnchorHourUTC          = 9;           // OR anchor hour (UTC)
input int    InpAnchorMinuteUTC        = 0;           // OR anchor minute (UTC)
input int    InpORMinutes              = 5;           // N — opening-range length (minutes)
input int    InpSessionEndHourUTC      = 21;          // EOD-flat / stop hunting for entries (UTC)
input double InpLot                    = 0.01;        // Fixed lot (Mode-A min lot)
input double InpRiskCapPct             = 5.0;         // Skip trade if $risk > this % of equity (Mode-A cap)
input int    InpUTCOffsetOverrideHours = 999;         // LIVE: 999=use TimeGMT(); else server->UTC offset hrs
input int    InpTesterUTCOffsetHours    = 0;          // TESTER only: server->UTC offset (Dukascopy custom sym=UTC => 0)
input int    InpMaxSpreadPoints        = 0;           // 0=off; else skip entry if spread > this (points)
input string InpComment                = "ORB001";    // Order comment (execution.db reconcile key)
input bool   InpVerbose                = true;        // Log session/decision events
input bool   InpShowVisuals            = true;        // Draw OR box / entry / trail / exit on chart

//--- Session state machine (per UTC day) ---
enum ORB_STATE { ST_WAIT_OR, ST_ARMED, ST_IN_TRADE, ST_DONE };

CTrade         g_trade;
COrbVisualizer g_viz;
ORB_STATE g_state          = ST_WAIT_OR;
datetime g_session_day     = 0;        // UTC midnight of the active session
double   g_or_high         = 0.0;
double   g_or_low          = 0.0;
double   g_range_w         = 0.0;
ulong    g_ticket          = 0;        // active position ticket
int      g_dir             = 0;        // +1 long, -1 short
double   g_peak            = 0.0;      // peak favorable price since entry
double   g_point           = 0.0;
double   g_contract        = 100.0;    // XAUUSD oz/lot (for $risk; informational)

//+------------------------------------------------------------------+
int OnInit()
  {
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(20);
   g_point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   g_viz.Init(InpComment + "_", InpShowVisuals);   // prefix ORB001_ ties visuals to the reconcile key

   PrintFormat("[ORB-001] init | magic=%I64d | anchor=%02d:%02d UTC | N=%d | EOD=%02d UTC | lot=%.2f | cap=%.1f%%",
               InpMagic, InpAnchorHourUTC, InpAnchorMinuteUTC, InpORMinutes, InpSessionEndHourUTC,
               InpLot, InpRiskCapPct);

   // Adopt any pre-existing ORB position (EA restart mid-trade).
   if(AdoptExistingPosition())
      g_state = ST_IN_TRADE;
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason) { }

//+------------------------------------------------------------------+
//| UTC now (broker-server time corrected to UTC)                    |
//+------------------------------------------------------------------+
datetime UtcNow()
  {
   // Strategy Tester: TimeGMT() is unreliable. The custom Dukascopy symbol is
   // UTC-stamped (QDM export "Original"=UTC) => tester server time IS UTC =>
   // subtract InpTesterUTCOffsetHours (default 0). Sanity check: London open
   // bar should land at 08:00 server time.
   if(MQLInfoInteger(MQL_TESTER))
      return(TimeCurrent() - (datetime)InpTesterUTCOffsetHours * 3600);

   if(InpUTCOffsetOverrideHours == 999)
      return(TimeGMT());                                   // live: PC-clock GMT
   return(TimeCurrent() - (datetime)InpUTCOffsetOverrideHours * 3600); // live: server - offset
  }

datetime DayMidnight(datetime t) { return(t - (t % 86400)); }

//+------------------------------------------------------------------+
//| OnTick                                                           |
//+------------------------------------------------------------------+
void OnTick()
  {
   datetime utc = UtcNow();
   datetime today = DayMidnight(utc);

   // --- New UTC session: reset everything ---
   if(today != g_session_day)
     {
      // close any straggler before rolling the day (defensive; EOD should have)
      if(g_state == ST_IN_TRADE) ClosePosition("NEWDAY");
      g_session_day = today;
      g_state       = ST_WAIT_OR;
      g_or_high = g_or_low = g_range_w = 0.0;
      g_ticket  = 0; g_dir = 0; g_peak = 0.0;
      g_viz.ClearSession();   // fresh visual layer each UTC day
      if(InpVerbose) PrintFormat("[ORB-001] new session %s UTC", TimeToString(today, TIME_DATE));
     }

   datetime anchor   = today + InpAnchorHourUTC * 3600 + InpAnchorMinuteUTC * 60;
   datetime or_close = anchor + InpORMinutes * 60;
   datetime eod      = today + InpSessionEndHourUTC * 3600;

   // --- EOD-flat: close + done for the day ---
   if(utc >= eod)
     {
      if(g_state == ST_IN_TRADE) ClosePosition("EOD");
      if(g_state != ST_DONE) { g_state = ST_DONE; }
      return;
     }

   switch(g_state)
     {
      case ST_WAIT_OR:
         // Wait until the OR window has fully closed, then compute it.
         if(utc >= or_close)
           {
            if(ComputeOpeningRange(anchor, or_close))
              {
               g_state = ST_ARMED;
               int off = (int)(TimeCurrent() - utc);   // UTC -> chart/server time for drawing
               g_viz.DrawOpeningRange(anchor + off, or_close + off, g_or_high, g_or_low);
               if(InpVerbose)
                  PrintFormat("[ORB-001] OR set: hi=%.2f lo=%.2f range_w=%.2f -> ARMED",
                              g_or_high, g_or_low, g_range_w);
              }
            else
              {
               // no OR data this session (holiday/gap) -> stand down
               g_state = ST_DONE;
               if(InpVerbose) Print("[ORB-001] no OR data this session -> DONE");
              }
           }
         break;

      case ST_ARMED:
         TryEnter();
         break;

      case ST_IN_TRADE:
         ManageTrail();
         break;

      case ST_DONE:
         break;
     }
  }

//+------------------------------------------------------------------+
//| Build the opening range from M1 bars in [anchor, or_close)       |
//+------------------------------------------------------------------+
bool ComputeOpeningRange(datetime anchor, datetime or_close)
  {
   // Convert UTC window to SERVER time for CopyRates (bars are server-stamped).
   datetime srv_now   = TimeCurrent();
   datetime utc_now   = UtcNow();
   int      off_sec   = (int)(srv_now - utc_now);          // server = utc + off
   datetime srv_from  = anchor   + off_sec;
   datetime srv_to    = or_close + off_sec;

   MqlRates r[];
   int n = CopyRates(_Symbol, PERIOD_M1, srv_from, srv_to - 1, r);  // inclusive..exclusive-ish
   if(n <= 0) return(false);

   double hi = -DBL_MAX, lo = DBL_MAX;
   for(int i = 0; i < n; i++)
     {
      if(r[i].high > hi) hi = r[i].high;
      if(r[i].low  < lo) lo = r[i].low;
     }
   if(hi <= 0 || lo >= DBL_MAX || hi <= lo) return(false);

   g_or_high = hi; g_or_low = lo; g_range_w = hi - lo;
   return(true);
  }

//+------------------------------------------------------------------+
//| Immediate breakout entry (first breach wins)                     |
//+------------------------------------------------------------------+
void TryEnter()
  {
   if(g_range_w <= 0.0) { g_state = ST_DONE; return; }

   // spread guard (optional)
   if(InpMaxSpreadPoints > 0)
     {
      long spr = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
      if(spr > InpMaxSpreadPoints) return;  // wait for spread to normalise
     }

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   int dir = 0;
   if(bid >= g_or_high)      dir = +1;   // upside breakout -> long
   else if(bid <= g_or_low)  dir = -1;   // downside breakout -> short
   if(dir == 0) return;                  // no breach yet

   // Mode-A 5% risk-skip: $risk of a min-lot trade = range_w * contract * lot.
   double risk_usd = g_range_w * g_contract * InpLot;
   double equity   = AccountInfoDouble(ACCOUNT_EQUITY);
   if(InpRiskCapPct > 0.0 && equity > 0.0 && (risk_usd / equity) * 100.0 > InpRiskCapPct)
     {
      if(InpVerbose)
         PrintFormat("[ORB-001] SKIP %s: $risk=%.2f > %.1f%% of equity %.2f",
                     (dir>0?"LONG":"SHORT"), risk_usd, InpRiskCapPct, equity);
      g_state = ST_DONE;   // one decision per session
      return;
     }

   double sl = (dir > 0) ? g_or_low : g_or_high;   // initial stop = opposite boundary (1R)
   bool ok;
   if(dir > 0) ok = g_trade.Buy(InpLot, _Symbol, 0.0, sl, 0.0, InpComment);
   else        ok = g_trade.Sell(InpLot, _Symbol, 0.0, sl, 0.0, InpComment);

   if(!ok)
     {
      PrintFormat("[ORB-001] ENTRY FAILED %s: ret=%d %s",
                  (dir>0?"LONG":"SHORT"), g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
      return;   // retry next tick while still ARMED and within session
     }

   g_ticket = g_trade.ResultOrder();
   g_dir    = dir;
   double fill = g_trade.ResultPrice();
   g_peak   = fill;                       // seed peak at entry fill
   g_state  = ST_IN_TRADE;
   g_viz.DrawEntry(TimeCurrent(), fill, dir, g_range_w);
   PrintFormat("[ORB-001] ENTER %s @ %.2f | SL=%.2f | range_w=%.2f | risk$=%.2f | ticket=%I64u",
               (dir>0?"LONG":"SHORT"), fill, sl, g_range_w, risk_usd, g_ticket);
  }

//+------------------------------------------------------------------+
//| trail_1R: trailing stop at distance range_w behind peak          |
//+------------------------------------------------------------------+
void ManageTrail()
  {
   if(!PositionSelectByTicket(g_ticket))
     {
      // position gone (SL hit / closed) -> done for the session
      double xp = (g_dir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                              : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      g_viz.DrawExit(TimeCurrent(), xp, "STOP");
      if(InpVerbose) Print("[ORB-001] position closed -> DONE (trail/SL or manual)");
      g_state = ST_DONE; g_ticket = 0;
      return;
     }

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double cur_sl = PositionGetDouble(POSITION_SL);
   double new_sl = cur_sl;

   if(g_dir > 0)
     {
      if(bid > g_peak) g_peak = bid;                 // track peak favourable
      double want = g_peak - g_range_w;              // trail 1R behind peak
      if(want > new_sl + g_point) new_sl = want;     // raise only
     }
   else
     {
      if(g_peak == 0.0 || ask < g_peak) g_peak = ask;
      double want = g_peak + g_range_w;
      if(new_sl == 0.0 || want < new_sl - g_point) new_sl = want;  // lower only
     }

   if(MathAbs(new_sl - cur_sl) > g_point)
     {
      double tp = PositionGetDouble(POSITION_TP);
      if(g_trade.PositionModify(g_ticket, NormalizeDouble(new_sl, _Digits), tp))
         g_viz.UpdateTrail(TimeCurrent(), NormalizeDouble(new_sl, _Digits), g_dir);
      else if(InpVerbose)
         PrintFormat("[ORB-001] trail modify failed: ret=%d", g_trade.ResultRetcode());
     }
  }

//+------------------------------------------------------------------+
//| Close the active position with a reason tag                      |
//+------------------------------------------------------------------+
void ClosePosition(string why)
  {
   if(g_ticket == 0 || !PositionSelectByTicket(g_ticket)) { g_ticket = 0; return; }
   double xp = (g_dir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                           : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(g_trade.PositionClose(g_ticket))
     {
      g_viz.DrawExit(TimeCurrent(), xp, why);
      PrintFormat("[ORB-001] CLOSE (%s) ticket=%I64u", why, g_ticket);
     }
   else
      PrintFormat("[ORB-001] CLOSE FAILED (%s): ret=%d", why, g_trade.ResultRetcode());
   g_ticket = 0;
  }

//+------------------------------------------------------------------+
//| Adopt an existing magic-1001 position on (re)start               |
//+------------------------------------------------------------------+
bool AdoptExistingPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0 || !PositionSelectByTicket(t)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      g_ticket = t;
      g_dir    = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? +1 : -1;
      g_peak   = PositionGetDouble(POSITION_PRICE_OPEN);
      // recover range_w from initial stop distance if present
      double sl = PositionGetDouble(POSITION_SL);
      double op = PositionGetDouble(POSITION_PRICE_OPEN);
      if(sl > 0) g_range_w = MathAbs(op - sl);
      PrintFormat("[ORB-001] adopted existing position ticket=%I64u dir=%d range_w=%.2f",
                  g_ticket, g_dir, g_range_w);
      return(true);
     }
   return(false);
  }
//+------------------------------------------------------------------+
