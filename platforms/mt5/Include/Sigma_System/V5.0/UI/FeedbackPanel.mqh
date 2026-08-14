//+------------------------------------------------------------------+
//|                                                 FeedbackPanel.mqh |
//|                             Copyright 2025, Sigma Trading System |
//+------------------------------------------------------------------+
//| V5.0 - Redesigned B2B Command Centre                             |
//| 6 Sections: Header, Account, Balance, Timeline, Zones, Positions |
//+------------------------------------------------------------------+
#ifndef V50_FEEDBACKPANEL_MQH
#define V50_FEEDBACKPANEL_MQH

#property strict

#include "../Common/Defines.mqh"
#include "../Common/Utils.mqh"
#include "../Data/Structures.mqh"
#include "../Configuration/TradingParameters.mqh"

//--- Display configuration
#ifndef InpDisplayFontColor
input color InpDisplayFontColor = clrWhite;
#endif

//--- Constants
#define MAX_ZONE_ROWS 9          // One per timeframe
#define MAX_POSITION_ROWS 5      // Max positions to display

//+------------------------------------------------------------------+
//| CFeedbackPanel Class - V5.0 Redesign                             |
//+------------------------------------------------------------------+
class CFeedbackPanel
{
private:
    long              m_chart_id;
    string            m_panel_name;
    
    // Panel dimensions
    int               m_x_pos;
    int               m_y_pos;
    int               m_panel_width;
    int               m_line_height;
    bool              m_is_minimized;
    int               m_full_height;
    int               m_header_height;
    
    // UI Element Names
    // Header
    string            m_background_name;
    string            m_header_bg_name;
    string            m_title_name;
    string            m_status_name;
    string            m_minimize_name;
    
    // Account Section
    string            m_account_name_label;
    string            m_account_id_label;
    string            m_broker_label;
    string            m_account_type_label;
    string            m_symbol_label;
    string            m_timestamp_label;
    string            m_divider1_name;
    
    // Balance Section
    string            m_balance_header_names[5];  // Equity, Balance, Margin, P&L, DD
    string            m_balance_value_names[5];
    string            m_divider2_name;
    
    // SIGMA Timeline
    string            m_timeline_header_name;
    string            m_timeline_tf_names[TOTAL_TIMEFRAMES];
    string            m_timeline_indicator_names[TOTAL_TIMEFRAMES];
    string            m_divider3_name;
    
    // Active Zones
    string            m_zones_header_name;
    string            m_zones_col_headers[5];     // TF, Zone, Status, Dir, 2nd Barrier
    string            m_zones_data[MAX_ZONE_ROWS][5];
    string            m_divider4_name;
    
    // Open Positions
    string            m_positions_header_name;
    string            m_positions_col_headers[6]; // Zone, TF, Dir, Lots, Entry, P&L
    string            m_positions_data[MAX_POSITION_ROWS][6];
    string            m_positions_summary_name;

public:
    CFeedbackPanel();
    ~CFeedbackPanel() { Destroy(); }

    void Create(const long chart_id);
    void Destroy();
    void Update(const B2BZoneInfo &zones[], int zones_count);
    bool HandleMinimizeClick(const int x, const int y);

private:
    void CreateLabel(const string &name, int x, int y, string text, color clr, int font_size = 9);
    void CreateDivider(const string &name, int y);
    void UpdateAccountSection();
    void UpdateBalanceSection();
    void UpdateTimeline(const B2BZoneInfo &zones[], int zones_count);
    void UpdateActiveZones(const B2BZoneInfo &zones[], int zones_count);
    void UpdateOpenPositions();
    void ToggleMinimize();
    void SetAllElementsVisibility(bool visible);
};

//+------------------------------------------------------------------+
//| Constructor                                                       |
//+------------------------------------------------------------------+
CFeedbackPanel::CFeedbackPanel()
{
    m_chart_id = 0;
    m_panel_name = "SigmaPanel";
    m_x_pos = 10;
    m_y_pos = 30;
    m_panel_width = 480;  // Reduced width for cleaner look
    m_line_height = 16;
    m_is_minimized = false;
    m_header_height = 30;
    m_full_height = 400;  // Will be calculated
    
    // Generate element names
    m_background_name = m_panel_name + "_Bg";
    m_header_bg_name = m_panel_name + "_HeaderBg";
    m_title_name = m_panel_name + "_Title";
    m_status_name = m_panel_name + "_Status";
    m_minimize_name = m_panel_name + "_Min";
    
    m_account_name_label = m_panel_name + "_AccName";
    m_account_id_label = m_panel_name + "_AccID";
    m_broker_label = m_panel_name + "_Broker";
    m_account_type_label = m_panel_name + "_AccType";
    m_symbol_label = m_panel_name + "_Symbol";
    m_timestamp_label = m_panel_name + "_Time";
    m_divider1_name = m_panel_name + "_Div1";
    
    for(int i = 0; i < 5; i++)
    {
        m_balance_header_names[i] = m_panel_name + "_BalH" + IntegerToString(i);
        m_balance_value_names[i] = m_panel_name + "_BalV" + IntegerToString(i);
    }
    m_divider2_name = m_panel_name + "_Div2";
    
    m_timeline_header_name = m_panel_name + "_TLHeader";
    for(int i = 0; i < TOTAL_TIMEFRAMES; i++)
    {
        m_timeline_tf_names[i] = m_panel_name + "_TLTF" + IntegerToString(i);
        m_timeline_indicator_names[i] = m_panel_name + "_TLInd" + IntegerToString(i);
    }
    m_divider3_name = m_panel_name + "_Div3";
    
    m_zones_header_name = m_panel_name + "_ZHeader";
    for(int i = 0; i < 5; i++)
        m_zones_col_headers[i] = m_panel_name + "_ZColH" + IntegerToString(i);
    for(int r = 0; r < MAX_ZONE_ROWS; r++)
        for(int c = 0; c < 5; c++)
            m_zones_data[r][c] = m_panel_name + "_ZD" + IntegerToString(r) + "_" + IntegerToString(c);
    m_divider4_name = m_panel_name + "_Div4";
    
    m_positions_header_name = m_panel_name + "_PHeader";
    for(int i = 0; i < 6; i++)
        m_positions_col_headers[i] = m_panel_name + "_PColH" + IntegerToString(i);
    for(int r = 0; r < MAX_POSITION_ROWS; r++)
        for(int c = 0; c < 6; c++)
            m_positions_data[r][c] = m_panel_name + "_PD" + IntegerToString(r) + "_" + IntegerToString(c);
    m_positions_summary_name = m_panel_name + "_PSummary";
}

//+------------------------------------------------------------------+
//| CreateLabel - Helper to create text labels                       |
//+------------------------------------------------------------------+
void CFeedbackPanel::CreateLabel(const string &name, int x, int y, string text, color clr, int font_size = 9)
{
    ObjectCreate(m_chart_id, name, OBJ_LABEL, 0, 0, 0);
    ObjectSetInteger(m_chart_id, name, OBJPROP_XDISTANCE, x);
    ObjectSetInteger(m_chart_id, name, OBJPROP_YDISTANCE, y);
    ObjectSetInteger(m_chart_id, name, OBJPROP_COLOR, clr);
    ObjectSetInteger(m_chart_id, name, OBJPROP_FONTSIZE, font_size);
    ObjectSetString(m_chart_id, name, OBJPROP_FONT, "Consolas");
    ObjectSetString(m_chart_id, name, OBJPROP_TEXT, text);
    ObjectSetInteger(m_chart_id, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
    ObjectSetInteger(m_chart_id, name, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
    ObjectSetInteger(m_chart_id, name, OBJPROP_BACK, false);
    ObjectSetInteger(m_chart_id, name, OBJPROP_ZORDER, 1001);
}

//+------------------------------------------------------------------+
//| CreateDivider - Creates a proper graphical divider line          |
//+------------------------------------------------------------------+
void CFeedbackPanel::CreateDivider(const string &name, int y)
{
    int offset = 15;      // Offset from left and right borders
    int top_offset = 6;   // Offset from top of line position
    int div_width = m_panel_width - (offset * 2);  // Width with equal margins
    
    ObjectCreate(m_chart_id, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
    ObjectSetInteger(m_chart_id, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
    ObjectSetInteger(m_chart_id, name, OBJPROP_XDISTANCE, m_x_pos + offset);
    ObjectSetInteger(m_chart_id, name, OBJPROP_YDISTANCE, y + top_offset);
    ObjectSetInteger(m_chart_id, name, OBJPROP_XSIZE, div_width);
    ObjectSetInteger(m_chart_id, name, OBJPROP_YSIZE, 1);  // 1 pixel height
    ObjectSetInteger(m_chart_id, name, OBJPROP_COLOR, C'80,80,80');  // Dark gray
    ObjectSetInteger(m_chart_id, name, OBJPROP_BGCOLOR, C'80,80,80');  // Dark gray background
    ObjectSetInteger(m_chart_id, name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
    ObjectSetInteger(m_chart_id, name, OBJPROP_BACK, false);
    ObjectSetInteger(m_chart_id, name, OBJPROP_ZORDER, 1001);
}

//+------------------------------------------------------------------+
//| Create - Build the entire panel                                  |
//+------------------------------------------------------------------+
void CFeedbackPanel::Create(const long chart_id)
{
    m_chart_id = chart_id;
    int y = m_y_pos;
    
    // Calculate full height
    m_full_height = m_header_height + 
                   (3 * m_line_height) +    // Account (3 rows)
                   m_line_height +           // Divider
                   (2 * m_line_height) +     // Balance (2 rows)
                   m_line_height +           // Divider
                   (3 * m_line_height) +     // Timeline (header + TF + indicators)
                   m_line_height +           // Divider
                   ((MAX_ZONE_ROWS + 2) * m_line_height) + // Zones (header + col headers + rows)
                   m_line_height +           // Divider
                   ((MAX_POSITION_ROWS + 3) * m_line_height) + // Positions
                   20;                        // Bottom padding
    
    // Main Background
    ObjectCreate(m_chart_id, m_background_name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
    ObjectSetInteger(m_chart_id, m_background_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
    ObjectSetInteger(m_chart_id, m_background_name, OBJPROP_XDISTANCE, m_x_pos);
    ObjectSetInteger(m_chart_id, m_background_name, OBJPROP_YDISTANCE, m_y_pos);
    ObjectSetInteger(m_chart_id, m_background_name, OBJPROP_XSIZE, m_panel_width);
    ObjectSetInteger(m_chart_id, m_background_name, OBJPROP_YSIZE, m_is_minimized ? m_header_height : m_full_height);
    ObjectSetInteger(m_chart_id, m_background_name, OBJPROP_BGCOLOR, C'30,30,40');
    ObjectSetInteger(m_chart_id, m_background_name, OBJPROP_BORDER_COLOR, C'50,50,60');
    ObjectSetInteger(m_chart_id, m_background_name, OBJPROP_BACK, false);
    ObjectSetInteger(m_chart_id, m_background_name, OBJPROP_ZORDER, 1000);

    // Header Background
    ObjectCreate(m_chart_id, m_header_bg_name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
    ObjectSetInteger(m_chart_id, m_header_bg_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
    ObjectSetInteger(m_chart_id, m_header_bg_name, OBJPROP_XDISTANCE, m_x_pos);
    ObjectSetInteger(m_chart_id, m_header_bg_name, OBJPROP_YDISTANCE, m_y_pos);
    ObjectSetInteger(m_chart_id, m_header_bg_name, OBJPROP_XSIZE, m_panel_width);
    ObjectSetInteger(m_chart_id, m_header_bg_name, OBJPROP_YSIZE, m_header_height);
    ObjectSetInteger(m_chart_id, m_header_bg_name, OBJPROP_BGCOLOR, C'30,30,40');
    ObjectSetInteger(m_chart_id, m_header_bg_name, OBJPROP_BORDER_COLOR, C'50,50,60');
    ObjectSetInteger(m_chart_id, m_header_bg_name, OBJPROP_BACK, false);
    ObjectSetInteger(m_chart_id, m_header_bg_name, OBJPROP_ZORDER, 999);

    // Header Elements
    CreateLabel(m_title_name, m_x_pos + 10, y + 6, " SIGMA V5.0 COMMAND CENTRE", clrWhite, 11);
    CreateLabel(m_status_name, m_x_pos + m_panel_width - 250, y + 6, "- ONLINE", clrLimeGreen, 11);
    CreateLabel(m_minimize_name, m_x_pos + m_panel_width - 30, y + 6, "[−]", clrLightGray, 10);
    
    if(m_is_minimized) { ChartRedraw(m_chart_id); return; }
    
    y += m_header_height + 5;
    
    // --- ACCOUNT SECTION ---
    int left_margin = 15;  // Unified left margin for all sections
    int right_account = m_x_pos + m_panel_width - 90;  // Position for Account#
    int right_demo = m_x_pos + m_panel_width - 40;      // Position for DEMO (short text)
    int right_time = m_x_pos + m_panel_width - 70;      // Position for Timestamp (longer text)
    
    CreateLabel(m_account_name_label, m_x_pos + left_margin, y, "", clrWhite, 9);
    CreateLabel(m_account_id_label, right_account, y, "", clrLightGray, 9);
    y += m_line_height;
    CreateLabel(m_broker_label, m_x_pos + left_margin, y, "", clrLightGray, 9);
    CreateLabel(m_account_type_label, right_demo, y, "", clrLimeGreen, 9);  // DEMO
    y += m_line_height;
    CreateLabel(m_symbol_label, m_x_pos + left_margin, y, "", clrLightGray, 9);
    CreateLabel(m_timestamp_label, right_time, y, "", clrLightGray, 9);  // Timestamp
    y += m_line_height;
    
    CreateDivider(m_divider1_name, y);
    y += m_line_height;
    
    // --- BALANCE SECTION ---
    string headers[] = {"EQUITY", "BALANCE", "MARGIN", "P&L", "DRAWDOWN"};
    int col_width = (m_panel_width - 30) / 5;  // Adjusted for margin
    for(int i = 0; i < 5; i++)
    {
        CreateLabel(m_balance_header_names[i], m_x_pos + left_margin + (i * col_width), y, headers[i], clrGray, 8);
        CreateLabel(m_balance_value_names[i], m_x_pos + left_margin + (i * col_width), y + m_line_height, "", clrWhite, 9);
    }
    y += 2 * m_line_height;
    
    CreateDivider(m_divider2_name, y);
    y += m_line_height;
    
    // --- SIGMA TIMELINE ---
    CreateLabel(m_timeline_header_name, m_x_pos + left_margin, y, "SIGMA TIMELINE", clrWhite, 9);
    y += m_line_height;
    
    string tf_names[] = {"M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"};
    int tf_width = (m_panel_width - 30) / TOTAL_TIMEFRAMES;
    for(int i = 0; i < TOTAL_TIMEFRAMES; i++)
    {
        CreateLabel(m_timeline_tf_names[i], m_x_pos + left_margin + (i * tf_width), y, tf_names[i], clrGray, 8);
        CreateLabel(m_timeline_indicator_names[i], m_x_pos + left_margin + (i * tf_width), y + m_line_height, "○", clrGray, 10);
    }
    y += 2 * m_line_height;
    
    CreateDivider(m_divider3_name, y);
    y += m_line_height;
    
    // --- ACTIVE ZONES ---
    CreateLabel(m_zones_header_name, m_x_pos + left_margin, y, "ACTIVE ZONES", clrWhite, 9);
    y += m_line_height;
    
    string zone_headers[] = {"TF", "ZONE", "STATUS", "DIR", "2ND BARRIER"};
    int zone_widths[] = {50, 90, 90, 70, 130};
    int zone_x = m_x_pos + left_margin;
    for(int i = 0; i < 5; i++)
    {
        CreateLabel(m_zones_col_headers[i], zone_x, y, zone_headers[i], clrGray, 8);
        zone_x += zone_widths[i];
    }
    y += m_line_height;
    
    for(int r = 0; r < MAX_ZONE_ROWS; r++)
    {
        zone_x = m_x_pos + left_margin;
        for(int c = 0; c < 5; c++)
        {
            CreateLabel(m_zones_data[r][c], zone_x, y, "", clrWhite, 9);
            zone_x += zone_widths[c];
        }
        y += m_line_height;
    }
    
    CreateDivider(m_divider4_name, y);
    y += m_line_height;
    
    // --- OPEN POSITIONS ---
    CreateLabel(m_positions_header_name, m_x_pos + left_margin, y, "OPEN POSITIONS", clrWhite, 9);
    y += m_line_height;
    
    string pos_headers[] = {"ZONE", "TF", "DIR", "LOTS", "ENTRY", "P&L"};
    int pos_widths[] = {80, 55, 60, 70, 100, 150};
    int pos_x = m_x_pos + left_margin;
    for(int i = 0; i < 6; i++)
    {
        CreateLabel(m_positions_col_headers[i], pos_x, y, pos_headers[i], clrGray, 8);
        pos_x += pos_widths[i];
    }
    y += m_line_height;
    
    for(int r = 0; r < MAX_POSITION_ROWS; r++)
    {
        pos_x = m_x_pos + left_margin;
        for(int c = 0; c < 6; c++)
        {
            CreateLabel(m_positions_data[r][c], pos_x, y, "--", clrGray, 9);  // Initialize with dashes
            pos_x += pos_widths[c];
        }
        y += m_line_height;
    }
    y += 5;
    CreateLabel(m_positions_summary_name, m_x_pos + left_margin, y, "", clrLightGray, 9);
    
    // Initial update
    UpdateAccountSection();
    UpdateBalanceSection();
    
    ChartRedraw(m_chart_id);
}

//+------------------------------------------------------------------+
//| UpdateAccountSection                                             |
//+------------------------------------------------------------------+
void CFeedbackPanel::UpdateAccountSection()
{
    string acc_name = AccountInfoString(ACCOUNT_NAME);
    long acc_num = AccountInfoInteger(ACCOUNT_LOGIN);
    string broker = AccountInfoString(ACCOUNT_COMPANY);
    ENUM_ACCOUNT_TRADE_MODE mode = (ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE);
    string acc_type = (mode == ACCOUNT_TRADE_MODE_DEMO) ? "DEMO" : "LIVE";
    
    ObjectSetString(m_chart_id, m_account_name_label, OBJPROP_TEXT, acc_name);
    ObjectSetString(m_chart_id, m_account_id_label, OBJPROP_TEXT, "#" + IntegerToString(acc_num));
    ObjectSetString(m_chart_id, m_broker_label, OBJPROP_TEXT, broker);
    ObjectSetString(m_chart_id, m_account_type_label, OBJPROP_TEXT, acc_type);
    ObjectSetInteger(m_chart_id, m_account_type_label, OBJPROP_COLOR, (mode == ACCOUNT_TRADE_MODE_DEMO) ? clrLimeGreen : clrOrangeRed);
    
    // Symbol on left, timestamp on right
    string symbol_date = _Symbol + "     " + TimeToString(TimeCurrent(), TIME_DATE);
    ObjectSetString(m_chart_id, m_symbol_label, OBJPROP_TEXT, symbol_date);
    
    string time_str = TimeToString(TimeCurrent(), TIME_SECONDS);
    ObjectSetString(m_chart_id, m_timestamp_label, OBJPROP_TEXT, time_str);
}

//+------------------------------------------------------------------+
//| UpdateBalanceSection                                             |
//+------------------------------------------------------------------+
void CFeedbackPanel::UpdateBalanceSection()
{
    double equity = AccountInfoDouble(ACCOUNT_EQUITY);
    double balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double margin_level = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
    
    // Calculate P&L
    double pnl = 0;
    for(int i = 0; i < PositionsTotal(); i++)
        if(PositionGetTicket(i) > 0) pnl += PositionGetDouble(POSITION_PROFIT);
    
    // Calculate drawdown
    double dd = (balance > 0) ? ((balance - equity) / balance) * 100.0 : 0;
    
    ObjectSetString(m_chart_id, m_balance_value_names[0], OBJPROP_TEXT, "$" + DoubleToString(equity, 2));
    ObjectSetString(m_chart_id, m_balance_value_names[1], OBJPROP_TEXT, "$" + DoubleToString(balance, 2));
    ObjectSetString(m_chart_id, m_balance_value_names[2], OBJPROP_TEXT, (margin_level > 0) ? DoubleToString(margin_level, 0) + "%" : "∞");
    
    string pnl_text = (pnl >= 0) ? "+$" + DoubleToString(pnl, 2) : "-$" + DoubleToString(MathAbs(pnl), 2);
    ObjectSetString(m_chart_id, m_balance_value_names[3], OBJPROP_TEXT, pnl_text);
    ObjectSetInteger(m_chart_id, m_balance_value_names[3], OBJPROP_COLOR, (pnl >= 0) ? clrLimeGreen : clrCrimson);
    
    ObjectSetString(m_chart_id, m_balance_value_names[4], OBJPROP_TEXT, StringFormat("%.1f%%", -dd));
    ObjectSetInteger(m_chart_id, m_balance_value_names[4], OBJPROP_COLOR, (dd <= 0) ? clrLimeGreen : clrCrimson);
}

//+------------------------------------------------------------------+
//| UpdateTimeline                                                    |
//+------------------------------------------------------------------+
void CFeedbackPanel::UpdateTimeline(const B2BZoneInfo &zones[], int zones_count)
{
    int tf_direction[TOTAL_TIMEFRAMES];
    ArrayInitialize(tf_direction, 0);  // 0 = none, 1 = bullish, 2 = bearish
    
    // Find latest zone direction for each TF
    for(int i = 0; i < zones_count; i++)
    {
        if(!zones[i].is_valid || zones[i].is_invalidated) continue;
        
        int tf_idx = TFEnumToIndex(zones[i].timeframe);
        if(tf_idx >= 0 && tf_idx < TOTAL_TIMEFRAMES)
        {
            if(zones[i].direction == DIRECTION_BULLISH)
                tf_direction[tf_idx] = 1;
            else if(zones[i].direction == DIRECTION_BEARISH)
                tf_direction[tf_idx] = 2;
        }
    }
    
    for(int i = 0; i < TOTAL_TIMEFRAMES; i++)
    {
        string indicator = "○";
        color clr = clrGray;
        
        if(tf_direction[i] == 1) { indicator = "●"; clr = clrLimeGreen; }  // BUY = Green circle
        else if(tf_direction[i] == 2) { indicator = "●"; clr = clrCrimson; }  // SELL = Red circle
        
        ObjectSetString(m_chart_id, m_timeline_indicator_names[i], OBJPROP_TEXT, indicator);
        ObjectSetInteger(m_chart_id, m_timeline_indicator_names[i], OBJPROP_COLOR, clr);
    }
}

//+------------------------------------------------------------------+
//| UpdateActiveZones                                                 |
//+------------------------------------------------------------------+
void CFeedbackPanel::UpdateActiveZones(const B2BZoneInfo &zones[], int zones_count)
{
    // Find latest valid zone per TF
    B2BZoneInfo latest_per_tf[TOTAL_TIMEFRAMES];
    bool has_zone[TOTAL_TIMEFRAMES];
    ArrayInitialize(has_zone, false);
    
    for(int i = 0; i < zones_count; i++)
    {
        if(!zones[i].is_valid || zones[i].is_invalidated) continue;
        
        int tf_idx = TFEnumToIndex(zones[i].timeframe);
        if(tf_idx >= 0 && tf_idx < TOTAL_TIMEFRAMES)
        {
            if(!has_zone[tf_idx] || zones[i].zone_created_time > latest_per_tf[tf_idx].zone_created_time)
            {
                latest_per_tf[tf_idx] = zones[i];
                has_zone[tf_idx] = true;
            }
        }
    }
    
    // Display zones (only those with data)
    int row = 0;
    for(int tf_idx = TOTAL_TIMEFRAMES - 1; tf_idx >= 0 && row < MAX_ZONE_ROWS; tf_idx--)
    {
        if(!has_zone[tf_idx]) continue;
        
        B2BZoneInfo zone = latest_per_tf[tf_idx];
        
        // Column 0: TF
        ObjectSetString(m_chart_id, m_zones_data[row][0], OBJPROP_TEXT, TFToString(zone.timeframe));
        ObjectSetInteger(m_chart_id, m_zones_data[row][0], OBJPROP_COLOR, clrWhite);
        
        // Column 1: Zone Display Number (V5.1.2: Clean sequential number)
        ObjectSetString(m_chart_id, m_zones_data[row][1], OBJPROP_TEXT, "#" + IntegerToString(zone.display_number));
        ObjectSetInteger(m_chart_id, m_zones_data[row][1], OBJPROP_COLOR, clrWhite);
        
        // Column 2: Status
        string status = "● NEW";
        color status_clr = clrWhite;
        if(zone.L2_touched) { status = "◒ L2"; status_clr = clrRed; }
        else if(zone.fifty_touched) { status = "◑ 50%"; status_clr = clrYellow; }
        else if(zone.L1_touched) { status = "◐ L1"; status_clr = clrLimeGreen; }
        ObjectSetString(m_chart_id, m_zones_data[row][2], OBJPROP_TEXT, status);
        ObjectSetInteger(m_chart_id, m_zones_data[row][2], OBJPROP_COLOR, status_clr);
        
        // Column 3: Direction
        string dir = (zone.direction == DIRECTION_BULLISH) ? "BUY" : "SELL";
        color dir_clr = (zone.direction == DIRECTION_BULLISH) ? clrSkyBlue : clrCrimson;
        ObjectSetString(m_chart_id, m_zones_data[row][3], OBJPROP_TEXT, dir);
        ObjectSetInteger(m_chart_id, m_zones_data[row][3], OBJPROP_COLOR, dir_clr);
        
        // Column 4: 2nd Barrier
        ObjectSetString(m_chart_id, m_zones_data[row][4], OBJPROP_TEXT, DoubleToString(zone.second_barrier_price, _Digits));
        ObjectSetInteger(m_chart_id, m_zones_data[row][4], OBJPROP_COLOR, clrLightGray);
        
        row++;
    }
    
    // Clear remaining rows
    for(; row < MAX_ZONE_ROWS; row++)
        for(int c = 0; c < 5; c++)
            ObjectSetString(m_chart_id, m_zones_data[row][c], OBJPROP_TEXT, "");
}

//+------------------------------------------------------------------+
//| UpdateOpenPositions                                               |
//+------------------------------------------------------------------+
void CFeedbackPanel::UpdateOpenPositions()
{
    int total = PositionsTotal();
    int displayed = 0;
    double total_lots = 0;
    double total_pnl = 0;
    int total_count = 0;
    
    // Track manual trades for consolidation
    double manual_buy_lots = 0, manual_buy_pnl = 0;
    int manual_buy_count = 0;
    double manual_sell_lots = 0, manual_sell_pnl = 0;
    int manual_sell_count = 0;
    
    // First pass: Display B2B zone trades & collect manual trades
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket == 0) continue;
        if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
        
        total_count++;
        double lots = PositionGetDouble(POSITION_VOLUME);
        double pnl = PositionGetDouble(POSITION_PROFIT);
        double entry = PositionGetDouble(POSITION_PRICE_OPEN);
        ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
        string comment = PositionGetString(POSITION_COMMENT);
        
        total_lots += lots;
        total_pnl += pnl;
        
        // Check if B2B zone trade
        int pos = StringFind(comment, "B2B_Z");
        if(pos >= 0 && displayed < MAX_POSITION_ROWS)
        {
            // B2B Zone trade - display individually
            string id_str = StringSubstr(comment, pos + 5);
            string zone_str = "#" + id_str;
            
            ObjectSetString(m_chart_id, m_positions_data[displayed][0], OBJPROP_TEXT, zone_str);
            ObjectSetInteger(m_chart_id, m_positions_data[displayed][0], OBJPROP_COLOR, clrWhite);
            ObjectSetString(m_chart_id, m_positions_data[displayed][1], OBJPROP_TEXT, "--");
            ObjectSetInteger(m_chart_id, m_positions_data[displayed][1], OBJPROP_COLOR, clrGray);
            
            string dir = (type == POSITION_TYPE_BUY) ? "BUY" : "SELL";
            color dir_clr = (type == POSITION_TYPE_BUY) ? clrSkyBlue : clrCrimson;
            ObjectSetString(m_chart_id, m_positions_data[displayed][2], OBJPROP_TEXT, dir);
            ObjectSetInteger(m_chart_id, m_positions_data[displayed][2], OBJPROP_COLOR, dir_clr);
            
            ObjectSetString(m_chart_id, m_positions_data[displayed][3], OBJPROP_TEXT, DoubleToString(lots, 2));
            ObjectSetInteger(m_chart_id, m_positions_data[displayed][3], OBJPROP_COLOR, clrWhite);
            
            ObjectSetString(m_chart_id, m_positions_data[displayed][4], OBJPROP_TEXT, DoubleToString(entry, _Digits));
            ObjectSetInteger(m_chart_id, m_positions_data[displayed][4], OBJPROP_COLOR, clrLightGray);
            
            string pnl_text = (pnl >= 0) ? "+$" + DoubleToString(pnl, 2) : "-$" + DoubleToString(MathAbs(pnl), 2);
            ObjectSetString(m_chart_id, m_positions_data[displayed][5], OBJPROP_TEXT, pnl_text);
            ObjectSetInteger(m_chart_id, m_positions_data[displayed][5], OBJPROP_COLOR, (pnl >= 0) ? clrLimeGreen : clrCrimson);
            
            displayed++;
        }
        else
        {
            // Manual trade - consolidate
            if(type == POSITION_TYPE_BUY)
            {
                manual_buy_lots += lots;
                manual_buy_pnl += pnl;
                manual_buy_count++;
            }
            else
            {
                manual_sell_lots += lots;
                manual_sell_pnl += pnl;
                manual_sell_count++;
            }
        }
    }
    
    // Display consolidated manual BUY trades
    if(manual_buy_count > 0 && displayed < MAX_POSITION_ROWS)
    {
        ObjectSetString(m_chart_id, m_positions_data[displayed][0], OBJPROP_TEXT, "MANUAL");
        ObjectSetInteger(m_chart_id, m_positions_data[displayed][0], OBJPROP_COLOR, clrGray);
        ObjectSetString(m_chart_id, m_positions_data[displayed][1], OBJPROP_TEXT, StringFormat("x%d", manual_buy_count));
        ObjectSetInteger(m_chart_id, m_positions_data[displayed][1], OBJPROP_COLOR, clrGray);
        ObjectSetString(m_chart_id, m_positions_data[displayed][2], OBJPROP_TEXT, "BUY");
        ObjectSetInteger(m_chart_id, m_positions_data[displayed][2], OBJPROP_COLOR, clrSkyBlue);
        ObjectSetString(m_chart_id, m_positions_data[displayed][3], OBJPROP_TEXT, DoubleToString(manual_buy_lots, 2));
        ObjectSetInteger(m_chart_id, m_positions_data[displayed][3], OBJPROP_COLOR, clrWhite);
        ObjectSetString(m_chart_id, m_positions_data[displayed][4], OBJPROP_TEXT, "---");
        ObjectSetInteger(m_chart_id, m_positions_data[displayed][4], OBJPROP_COLOR, clrGray);
        string pnl_text = (manual_buy_pnl >= 0) ? "+$" + DoubleToString(manual_buy_pnl, 2) : "-$" + DoubleToString(MathAbs(manual_buy_pnl), 2);
        ObjectSetString(m_chart_id, m_positions_data[displayed][5], OBJPROP_TEXT, pnl_text);
        ObjectSetInteger(m_chart_id, m_positions_data[displayed][5], OBJPROP_COLOR, (manual_buy_pnl >= 0) ? clrLimeGreen : clrCrimson);
        displayed++;
    }
    
    // Display consolidated manual SELL trades
    if(manual_sell_count > 0 && displayed < MAX_POSITION_ROWS)
    {
        ObjectSetString(m_chart_id, m_positions_data[displayed][0], OBJPROP_TEXT, "MANUAL");
        ObjectSetInteger(m_chart_id, m_positions_data[displayed][0], OBJPROP_COLOR, clrGray);
        ObjectSetString(m_chart_id, m_positions_data[displayed][1], OBJPROP_TEXT, StringFormat("x%d", manual_sell_count));
        ObjectSetInteger(m_chart_id, m_positions_data[displayed][1], OBJPROP_COLOR, clrGray);
        ObjectSetString(m_chart_id, m_positions_data[displayed][2], OBJPROP_TEXT, "SELL");
        ObjectSetInteger(m_chart_id, m_positions_data[displayed][2], OBJPROP_COLOR, clrCrimson);
        ObjectSetString(m_chart_id, m_positions_data[displayed][3], OBJPROP_TEXT, DoubleToString(manual_sell_lots, 2));
        ObjectSetInteger(m_chart_id, m_positions_data[displayed][3], OBJPROP_COLOR, clrWhite);
        ObjectSetString(m_chart_id, m_positions_data[displayed][4], OBJPROP_TEXT, "---");
        ObjectSetInteger(m_chart_id, m_positions_data[displayed][4], OBJPROP_COLOR, clrGray);
        string pnl_text = (manual_sell_pnl >= 0) ? "+$" + DoubleToString(manual_sell_pnl, 2) : "-$" + DoubleToString(MathAbs(manual_sell_pnl), 2);
        ObjectSetString(m_chart_id, m_positions_data[displayed][5], OBJPROP_TEXT, pnl_text);
        ObjectSetInteger(m_chart_id, m_positions_data[displayed][5], OBJPROP_COLOR, (manual_sell_pnl >= 0) ? clrLimeGreen : clrCrimson);
        displayed++;
    }
    
    // Clear remaining rows with dashes
    for(; displayed < MAX_POSITION_ROWS; displayed++)
        for(int c = 0; c < 6; c++)
        {
            ObjectSetString(m_chart_id, m_positions_data[displayed][c], OBJPROP_TEXT, "--");
            ObjectSetInteger(m_chart_id, m_positions_data[displayed][c], OBJPROP_COLOR, clrGray);
        }
    
    // Summary
    string pnl_sum = (total_pnl >= 0) ? "+$" + DoubleToString(total_pnl, 2) : "-$" + DoubleToString(MathAbs(total_pnl), 2);
    string summary = StringFormat("TOTAL: %d positions    LOTS: %.2f    FLOATING P&L: %s", total_count, total_lots, pnl_sum);
    ObjectSetString(m_chart_id, m_positions_summary_name, OBJPROP_TEXT, summary);
    ObjectSetInteger(m_chart_id, m_positions_summary_name, OBJPROP_COLOR, (total_pnl >= 0) ? clrLimeGreen : clrCrimson);
}

//+------------------------------------------------------------------+
//| Update - Main update function                                     |
//+------------------------------------------------------------------+
void CFeedbackPanel::Update(const B2BZoneInfo &zones[], int zones_count)
{
    if(m_is_minimized) return;
    
    UpdateAccountSection();
    UpdateBalanceSection();
    UpdateTimeline(zones, zones_count);
    UpdateActiveZones(zones, zones_count);
    UpdateOpenPositions();
    
    ChartRedraw(m_chart_id);
}

//+------------------------------------------------------------------+
//| ToggleMinimize                                                    |
//+------------------------------------------------------------------+
void CFeedbackPanel::ToggleMinimize()
{
    m_is_minimized = !m_is_minimized;
    ObjectSetString(m_chart_id, m_minimize_name, OBJPROP_TEXT, m_is_minimized ? "[+]" : "[−]");
    ObjectSetInteger(m_chart_id, m_background_name, OBJPROP_YSIZE, m_is_minimized ? m_header_height : m_full_height);
    SetAllElementsVisibility(!m_is_minimized);
    ChartRedraw(m_chart_id);
}

//+------------------------------------------------------------------+
//| SetAllElementsVisibility                                          |
//+------------------------------------------------------------------+
void CFeedbackPanel::SetAllElementsVisibility(bool visible)
{
    long periods = visible ? OBJ_ALL_PERIODS : OBJ_NO_PERIODS;
    
    // Account
    ObjectSetInteger(m_chart_id, m_account_name_label, OBJPROP_TIMEFRAMES, periods);
    ObjectSetInteger(m_chart_id, m_account_id_label, OBJPROP_TIMEFRAMES, periods);
    ObjectSetInteger(m_chart_id, m_broker_label, OBJPROP_TIMEFRAMES, periods);
    ObjectSetInteger(m_chart_id, m_account_type_label, OBJPROP_TIMEFRAMES, periods);
    ObjectSetInteger(m_chart_id, m_symbol_label, OBJPROP_TIMEFRAMES, periods);
    ObjectSetInteger(m_chart_id, m_timestamp_label, OBJPROP_TIMEFRAMES, periods);
    ObjectSetInteger(m_chart_id, m_divider1_name, OBJPROP_TIMEFRAMES, periods);
    
    // Balance
    for(int i = 0; i < 5; i++)
    {
        ObjectSetInteger(m_chart_id, m_balance_header_names[i], OBJPROP_TIMEFRAMES, periods);
        ObjectSetInteger(m_chart_id, m_balance_value_names[i], OBJPROP_TIMEFRAMES, periods);
    }
    ObjectSetInteger(m_chart_id, m_divider2_name, OBJPROP_TIMEFRAMES, periods);
    
    // Timeline
    ObjectSetInteger(m_chart_id, m_timeline_header_name, OBJPROP_TIMEFRAMES, periods);
    for(int i = 0; i < TOTAL_TIMEFRAMES; i++)
    {
        ObjectSetInteger(m_chart_id, m_timeline_tf_names[i], OBJPROP_TIMEFRAMES, periods);
        ObjectSetInteger(m_chart_id, m_timeline_indicator_names[i], OBJPROP_TIMEFRAMES, periods);
    }
    ObjectSetInteger(m_chart_id, m_divider3_name, OBJPROP_TIMEFRAMES, periods);
    
    // Zones
    ObjectSetInteger(m_chart_id, m_zones_header_name, OBJPROP_TIMEFRAMES, periods);
    for(int i = 0; i < 5; i++)
        ObjectSetInteger(m_chart_id, m_zones_col_headers[i], OBJPROP_TIMEFRAMES, periods);
    for(int r = 0; r < MAX_ZONE_ROWS; r++)
        for(int c = 0; c < 5; c++)
            ObjectSetInteger(m_chart_id, m_zones_data[r][c], OBJPROP_TIMEFRAMES, periods);
    ObjectSetInteger(m_chart_id, m_divider4_name, OBJPROP_TIMEFRAMES, periods);
    
    // Positions
    ObjectSetInteger(m_chart_id, m_positions_header_name, OBJPROP_TIMEFRAMES, periods);
    for(int i = 0; i < 6; i++)
        ObjectSetInteger(m_chart_id, m_positions_col_headers[i], OBJPROP_TIMEFRAMES, periods);
    for(int r = 0; r < MAX_POSITION_ROWS; r++)
        for(int c = 0; c < 6; c++)
            ObjectSetInteger(m_chart_id, m_positions_data[r][c], OBJPROP_TIMEFRAMES, periods);
    ObjectSetInteger(m_chart_id, m_positions_summary_name, OBJPROP_TIMEFRAMES, periods);
}

//+------------------------------------------------------------------+
//| HandleMinimizeClick                                               |
//+------------------------------------------------------------------+
bool CFeedbackPanel::HandleMinimizeClick(const int x, const int y)
{
    if(ObjectFind(m_chart_id, m_minimize_name) >= 0)
    {
        int btn_x = (int)ObjectGetInteger(m_chart_id, m_minimize_name, OBJPROP_XDISTANCE);
        int btn_y = (int)ObjectGetInteger(m_chart_id, m_minimize_name, OBJPROP_YDISTANCE);
        if(x >= btn_x - 10 && x <= btn_x + 25 && y >= btn_y - 5 && y <= btn_y + 20)
        {
            ToggleMinimize();
            return true;
        }
    }
    return false;
}

//+------------------------------------------------------------------+
//| Destroy                                                           |
//+------------------------------------------------------------------+
void CFeedbackPanel::Destroy()
{
    ObjectsDeleteAll(m_chart_id, m_panel_name);
    ChartRedraw(m_chart_id);
}

#endif // V50_FEEDBACKPANEL_MQH
