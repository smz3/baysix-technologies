//+------------------------------------------------------------------+
//|                                            orb_visualizer.mqh     |
//|                          Copyright 2026, Baysix Technologies      |
//+------------------------------------------------------------------+
//| Chart visuals for the standalone ORB EAs (orb_system namespace).  |
//| Deliberately self-contained — NO Sigma_System includes — so a     |
//| change here can never touch the B2B money-maker.                  |
//|                                                                  |
//| Mirrors the Sigma Visualizer.mqh house style:                     |
//|   • Calibri Light text, "•" bullet glyphs, BACK objects, non-     |
//|     selectable. Every object name is prefixed ORB<NNN>_ so the    |
//|     whole layer clears in one ObjectsDeleteAll().                 |
//|                                                                  |
//| Draws, per session: the opening-range box + hi/lo rays, the entry |
//| marker, the ratcheting trail_1R staircase, and the exit marker.   |
//| Pure cosmetics — it reads no state and changes no trade logic.    |
//+------------------------------------------------------------------+
#ifndef ORB_VISUALIZER_MQH
#define ORB_VISUALIZER_MQH

#property strict

//+------------------------------------------------------------------+
//| COrbVisualizer                                                   |
//+------------------------------------------------------------------+
class COrbVisualizer
  {
private:
   string            m_prefix;          // object-name prefix, e.g. "ORB001_"
   bool              m_on;              // master enable
   int               m_trail_idx;       // ratchet segment counter (this session)
   datetime          m_trail_last_t;    // last trail vertex time
   double            m_trail_last_p;    // last trail vertex price

   // --- house palette (teal long / red short / amber trail / grey box) ---
   color             m_clr_long;
   color             m_clr_short;
   color             m_clr_trail;
   color             m_clr_box;
   color             m_clr_or;
   int               m_font_label;
   int               m_font_bullet;

   string            N(const string suffix) { return(m_prefix + suffix); }

   void              Text(const string name, datetime t, double p, const string txt,
                          color clr, int font_sz, ENUM_ANCHOR_POINT anchor);

public:
                     COrbVisualizer(void);
   void              Init(const string prefix, bool enabled);
   bool              Enabled(void) const { return(m_on); }

   void              ClearSession(void);                 // wipe the whole ORB layer
   void              DrawOpeningRange(datetime anchor, datetime or_close,
                                      double hi, double lo);
   void              DrawEntry(datetime t, double price, int dir, double range_w);
   void              UpdateTrail(datetime t, double sl_price, int dir);
   void              DrawExit(datetime t, double price, const string reason);
  };

//+------------------------------------------------------------------+
COrbVisualizer::COrbVisualizer(void)
  {
   m_prefix      = "ORB_";
   m_on          = true;
   m_trail_idx   = 0;
   m_trail_last_t= 0;
   m_trail_last_p= 0.0;
   m_clr_long    = clrTeal;
   m_clr_short   = clrCrimson;
   m_clr_trail   = clrGoldenrod;
   m_clr_box     = (color)C'40,55,71';   // muted slate fill
   m_clr_or      = clrSlateGray;
   m_font_label  = 9;
   m_font_bullet = 12;
  }

//+------------------------------------------------------------------+
void COrbVisualizer::Init(const string prefix, bool enabled)
  {
   m_prefix = prefix;
   m_on     = enabled;
  }

//+------------------------------------------------------------------+
//| Generic Calibri-Light text/bullet object (house style)           |
//+------------------------------------------------------------------+
void COrbVisualizer::Text(const string name, datetime t, double p, const string txt,
                          color clr, int font_sz, ENUM_ANCHOR_POINT anchor)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
   ObjectSetString (0, name, OBJPROP_TEXT,      txt);
   ObjectSetString (0, name, OBJPROP_FONT,      "Calibri Light");
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE,  font_sz);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR,    anchor);
   ObjectSetInteger(0, name, OBJPROP_COLOR,     clr);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0, name, OBJPROP_BACK,      false);
   ObjectSetInteger(0, name, OBJPROP_TIME, 0, t);
   ObjectSetDouble (0, name, OBJPROP_PRICE,0, p);
  }

//+------------------------------------------------------------------+
//| ClearSession — wipe the whole ORB visual layer + reset trail      |
//+------------------------------------------------------------------+
void COrbVisualizer::ClearSession(void)
  {
   ObjectsDeleteAll(0, m_prefix);
   m_trail_idx    = 0;
   m_trail_last_t = 0;
   m_trail_last_p = 0.0;
  }

//+------------------------------------------------------------------+
//| Opening range: filled box + hi/lo extension rays + label          |
//+------------------------------------------------------------------+
void COrbVisualizer::DrawOpeningRange(datetime anchor, datetime or_close,
                                      double hi, double lo)
  {
   if(!m_on) return;

   // --- OR box [anchor..or_close] x [lo..hi] ---
   string box = N("OR_BOX");
   if(ObjectFind(0, box) < 0)
      ObjectCreate(0, box, OBJ_RECTANGLE, 0, anchor, hi, or_close, lo);
   ObjectSetInteger(0, box, OBJPROP_TIME,  0, anchor);
   ObjectSetInteger(0, box, OBJPROP_TIME,  1, or_close);
   ObjectSetDouble (0, box, OBJPROP_PRICE, 0, hi);
   ObjectSetDouble (0, box, OBJPROP_PRICE, 1, lo);
   ObjectSetInteger(0, box, OBJPROP_COLOR,      m_clr_box);
   ObjectSetInteger(0, box, OBJPROP_FILL,       true);
   ObjectSetInteger(0, box, OBJPROP_BACK,       true);
   ObjectSetInteger(0, box, OBJPROP_SELECTABLE, false);

   // --- hi / lo extension rays (OBJ_TREND, ray-right, dashed) ---
   string hl[2]; hl[0] = N("OR_HI"); hl[1] = N("OR_LO");
   double pv[2]; pv[0] = hi;         pv[1] = lo;
   for(int i = 0; i < 2; i++)
     {
      if(ObjectFind(0, hl[i]) < 0)
         ObjectCreate(0, hl[i], OBJ_TREND, 0, anchor, pv[i], or_close, pv[i]);
      ObjectSetInteger(0, hl[i], OBJPROP_TIME,  0, anchor);
      ObjectSetInteger(0, hl[i], OBJPROP_TIME,  1, or_close);
      ObjectSetDouble (0, hl[i], OBJPROP_PRICE, 0, pv[i]);
      ObjectSetDouble (0, hl[i], OBJPROP_PRICE, 1, pv[i]);
      ObjectSetInteger(0, hl[i], OBJPROP_COLOR,      m_clr_or);
      ObjectSetInteger(0, hl[i], OBJPROP_STYLE,      STYLE_DOT);
      ObjectSetInteger(0, hl[i], OBJPROP_RAY_RIGHT,  true);
      ObjectSetInteger(0, hl[i], OBJPROP_BACK,       true);
      ObjectSetInteger(0, hl[i], OBJPROP_SELECTABLE, false);
     }

   // --- range label above the box ---
   Text(N("OR_LBL"), anchor, hi,
        "•  OR " + TimeToString(anchor, TIME_MINUTES) + "  w=" + DoubleToString(hi - lo, _Digits),
        m_clr_or, m_font_label, ANCHOR_LEFT_LOWER);
  }

//+------------------------------------------------------------------+
//| Entry marker (▲ long / ▼ short) + label                          |
//+------------------------------------------------------------------+
void COrbVisualizer::DrawEntry(datetime t, double price, int dir, double range_w)
  {
   if(!m_on) return;
   color  c    = (dir > 0) ? m_clr_long : m_clr_short;
   string glyph= (dir > 0) ? "▲" : "▼";
   string side = (dir > 0) ? "LONG" : "SHORT";

   ENUM_ANCHOR_POINT a = (dir > 0) ? (ENUM_ANCHOR_POINT)ANCHOR_TOP : (ENUM_ANCHOR_POINT)ANCHOR_BOTTOM;
   Text(N("ENTRY_M"), t, price, glyph, c, m_font_bullet, a);
   Text(N("ENTRY_L"), t, price,
        "•  " + side + " @ " + DoubleToString(price, _Digits) + "  1R=" + DoubleToString(range_w, _Digits),
        c, m_font_label, ANCHOR_LEFT);

   // seed the trail staircase at the entry fill
   m_trail_idx    = 0;
   m_trail_last_t = t;
   m_trail_last_p = price;
  }

//+------------------------------------------------------------------+
//| Trail staircase — one OBJ_TREND segment per ratchet step          |
//+------------------------------------------------------------------+
void COrbVisualizer::UpdateTrail(datetime t, double sl_price, int dir)
  {
   if(!m_on) return;
   if(m_trail_last_t == 0) { m_trail_last_t = t; m_trail_last_p = sl_price; return; }
   if(MathAbs(sl_price - m_trail_last_p) < _Point) return;   // no ratchet, no segment

   // horizontal run at the old level, then the step to the new level
   string h = N("TRL_H" + (string)m_trail_idx);
   ObjectCreate(0, h, OBJ_TREND, 0, m_trail_last_t, m_trail_last_p, t, m_trail_last_p);
   ObjectSetInteger(0, h, OBJPROP_COLOR, m_clr_trail);
   ObjectSetInteger(0, h, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, h, OBJPROP_RAY_RIGHT,  false);
   ObjectSetInteger(0, h, OBJPROP_BACK,       false);
   ObjectSetInteger(0, h, OBJPROP_SELECTABLE, false);

   string v = N("TRL_V" + (string)m_trail_idx);
   ObjectCreate(0, v, OBJ_TREND, 0, t, m_trail_last_p, t, sl_price);
   ObjectSetInteger(0, v, OBJPROP_COLOR, m_clr_trail);
   ObjectSetInteger(0, v, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, v, OBJPROP_STYLE, STYLE_DOT);
   ObjectSetInteger(0, v, OBJPROP_RAY_RIGHT,  false);
   ObjectSetInteger(0, v, OBJPROP_BACK,       false);
   ObjectSetInteger(0, v, OBJPROP_SELECTABLE, false);

   m_trail_idx++;
   m_trail_last_t = t;
   m_trail_last_p = sl_price;
  }

//+------------------------------------------------------------------+
//| Exit marker (✕) + reason label                                   |
//+------------------------------------------------------------------+
void COrbVisualizer::DrawExit(datetime t, double price, const string reason)
  {
   if(!m_on) return;
   Text(N("EXIT_M"), t, price, "✕", clrWhite, m_font_bullet, ANCHOR_CENTER);
   Text(N("EXIT_L"), t, price,
        "•  EXIT " + reason + " @ " + DoubleToString(price, _Digits),
        clrWhite, m_font_label, ANCHOR_LEFT);

   // pin the final trail level out to the exit
   if(m_trail_last_t != 0 && m_trail_last_t < t)
     {
      string h = N("TRL_H" + (string)m_trail_idx);
      ObjectCreate(0, h, OBJ_TREND, 0, m_trail_last_t, m_trail_last_p, t, m_trail_last_p);
      ObjectSetInteger(0, h, OBJPROP_COLOR, m_clr_trail);
      ObjectSetInteger(0, h, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, h, OBJPROP_RAY_RIGHT,  false);
      ObjectSetInteger(0, h, OBJPROP_SELECTABLE, false);
      m_trail_idx++;
     }
  }

#endif // ORB_VISUALIZER_MQH
