//+------------------------------------------------------------------+
//|                                                ContextMapper.mqh |
//|                             Copyright 2026, Sigma Trading System |
//|                  V6.2: Structural Narrative Layer (3-Gate System) |
//+------------------------------------------------------------------+
#ifndef V50_CONTEXTMAPPER_MQH
#define V50_CONTEXTMAPPER_MQH

#include "../Data/Structures.mqh"

struct SessionBoundary
{
    ulong  mn1_high_id; double mn1_high_price;
    ulong  mn1_low_id;  double mn1_low_price;

    ulong  w1_high_id;  double w1_high_price;
    ulong  w1_low_id;   double w1_low_price;

    ulong  d1_high_id;  double d1_high_price;
    ulong  d1_low_id;   double d1_low_price;
    
    ulong  h4_high_id;  double h4_high_price;
    ulong  h4_low_id;   double h4_low_price;
    
    ulong  h1_high_id;  double h1_high_price;
    ulong  h1_low_id;   double h1_low_price;
    
    ulong  m30_high_id; double m30_high_price;
    ulong  m30_low_id;  double m30_low_price;
    
    SessionBoundary() 
    {
        mn1_high_id = 0; mn1_high_price = 0; mn1_low_id = 0; mn1_low_price = DBL_MAX;
        w1_high_id = 0;  w1_high_price = 0;  w1_low_id = 0;  w1_low_price = DBL_MAX;
        d1_high_id = 0;  d1_high_price = 0;  d1_low_id = 0;  d1_low_price = DBL_MAX;
        h4_high_id = 0;  h4_high_price = 0;  h4_low_id = 0;  h4_low_price = DBL_MAX;
        h1_high_id = 0;  h1_high_price = 0;  h1_low_id = 0;  h1_low_price = DBL_MAX;
        m30_high_id = 0; m30_high_price = 0; m30_low_id = 0; m30_low_price = DBL_MAX;
    }
};

class CContextMapper
{
private:
    datetime m_last_map_time;
    datetime m_last_intraday_bar;

    
    SessionBoundary m_monthly_map;
    SessionBoundary m_weekly_map;
    SessionBoundary m_intraday_map;
    
    SessionBoundary m_prev_monthly_map;
    SessionBoundary m_prev_weekly_map;
    SessionBoundary m_prev_intraday_map;

public:
                     CContextMapper();
                    ~CContextMapper();

    void             EvaluateContext(const B2BZoneInfo &zones[], int zone_count);
    
    // Gate 2: Spatial Queries
    double           GetTargetCoordinate(ENUM_SIGNAL_DIRECTION dir, double current_price) const;
    double           GetDistanceToWall(ENUM_SIGNAL_DIRECTION dir, double current_price) const;
    ulong            IsPathBlocked(ENUM_SIGNAL_DIRECTION dir, double current_price,
                                   ENUM_TIMEFRAMES scan_tf, const B2BZoneInfo &zones[],
                                   int zone_count, ulong siege_magnet_id = 0) const;
    
    // Gate 2: Structural Narrative Queries
    double           GetEpochPosition(ENUM_SIGNAL_DIRECTION dir, double current_price) const;
    bool             IsBreakout(ENUM_SIGNAL_DIRECTION dir, double current_price) const;
    double           GetIntradayPosition(double current_price) const;

private:
    datetime         GetMonthStart(datetime current_time) const;
    datetime         GetPrevMonthStart(datetime current_time) const;
    datetime         GetWeekStart(datetime current_time) const;
    datetime         GetPrevWeekStart(datetime current_time) const;
    datetime         GetDayStart(datetime current_time) const;
    datetime         GetPrevDayStart(datetime current_time) const;
    string           GetTFString(ENUM_TIMEFRAMES tf) const;
    
    SessionBoundary  FindTopographicalBoundary(const B2BZoneInfo &zones[], int zone_count, int max_tf_level, datetime start_time, datetime end_time) const;

    double           GetHighestResistance(const SessionBoundary &map) const;
    double           GetLowestSupport(const SessionBoundary &map) const;

    string FormatStackedTFStr(ulong zone_id, double price, string prefix) const
    {
        if(zone_id == 0) return prefix + "-" + "VACUUM";
        return StringFormat("%s-#%04d (%.5f)", prefix, zone_id % 10000, price);
    }
    
    string BuildMapString(const SessionBoundary &map, bool is_high, int max_tf_level) const
    {
        string out = "";
        if(max_tf_level <= 0)
        {
            if(is_high) out += FormatStackedTFStr(map.mn1_high_id, map.mn1_high_price, "MN1") + " | ";
            else        out += FormatStackedTFStr(map.mn1_low_id, map.mn1_low_price, "MN1") + " | ";
        }
        if(max_tf_level <= 1)
        {
            if(is_high) out += FormatStackedTFStr(map.w1_high_id, map.w1_high_price, "W1") + " | ";
            else        out += FormatStackedTFStr(map.w1_low_id, map.w1_low_price, "W1") + " | ";
        }
        if(max_tf_level <= 2)
        {
            if(is_high) out += FormatStackedTFStr(map.d1_high_id, map.d1_high_price, "D1") + " | ";
            else        out += FormatStackedTFStr(map.d1_low_id, map.d1_low_price, "D1") + " | ";
        }
        if(max_tf_level <= 3)
        {
            if(is_high) out += FormatStackedTFStr(map.h4_high_id, map.h4_high_price, "H4") + " | ";
            else        out += FormatStackedTFStr(map.h4_low_id, map.h4_low_price, "H4") + " | ";
        }
        if(max_tf_level <= 4)
        {
            if(is_high) out += FormatStackedTFStr(map.h1_high_id, map.h1_high_price, "H1") + " | ";
            else        out += FormatStackedTFStr(map.h1_low_id, map.h1_low_price, "H1") + " | ";
            
            if(is_high) out += FormatStackedTFStr(map.m30_high_id, map.m30_high_price, "M30");
            else        out += FormatStackedTFStr(map.m30_low_id, map.m30_low_price, "M30");
        }
        return out;
    }
};

//+------------------------------------------------------------------+
//| Constructor / Destructor                                         |
//+------------------------------------------------------------------+
CContextMapper::CContextMapper() : m_last_map_time(0), m_last_intraday_bar(0) {}
CContextMapper::~CContextMapper() {}

//+------------------------------------------------------------------+
//| EvaluateContext - Stacked Radar Scanner                          |
//+------------------------------------------------------------------+
void CContextMapper::EvaluateContext(const B2BZoneInfo &zones[], int zone_count)
{
    datetime current_time = TimeCurrent();
    datetime current_day = GetDayStart(current_time);
    
    if(current_day > m_last_map_time || m_last_map_time == 0)
    {
        datetime month_start = GetMonthStart(current_time);
        datetime prev_month_start = GetPrevMonthStart(current_time);
        datetime week_start = GetWeekStart(current_time);
        datetime prev_week_start = GetPrevWeekStart(current_time);
        
        m_monthly_map      = FindTopographicalBoundary(zones, zone_count, 0, month_start, 0);
        m_prev_monthly_map = FindTopographicalBoundary(zones, zone_count, 0, prev_month_start, month_start);
        m_weekly_map      = FindTopographicalBoundary(zones, zone_count, 1, week_start, 0);
        m_prev_weekly_map = FindTopographicalBoundary(zones, zone_count, 1, prev_week_start, week_start);
        
        Print("");
        Print("=========================================================================================");
        Print(">>>                      SAMTC CONTEXT MAPPER (STACKED RADAR V6.3)                   <<<");
        Print("=========================================================================================");
        PrintFormat("[MONTH] PREV H: %s", BuildMapString(m_prev_monthly_map, true, 0));
        PrintFormat("[MONTH] CUR  H: %s", BuildMapString(m_monthly_map, true, 0));
        PrintFormat("[MONTH] PREV L: %s", BuildMapString(m_prev_monthly_map, false, 0));
        PrintFormat("[MONTH] CUR  L: %s", BuildMapString(m_monthly_map, false, 0));
        Print("-----------------------------------------------------------------------------------------");
        PrintFormat("[WEEK]  PREV H: %s", BuildMapString(m_prev_weekly_map, true, 1));
        PrintFormat("[WEEK]  CUR  H: %s", BuildMapString(m_weekly_map, true, 1));
        PrintFormat("[WEEK]  PREV L: %s", BuildMapString(m_prev_weekly_map, false, 1));
        PrintFormat("[WEEK]  CUR  L: %s", BuildMapString(m_weekly_map, false, 1));
        
        m_last_map_time = current_day;
    }
    
    datetime current_m1_bar = iTime(_Symbol, PERIOD_M1, 0);
    if(current_m1_bar != m_last_intraday_bar)
    {
        datetime day_start = GetDayStart(current_time);
        datetime prev_day_start = GetPrevDayStart(current_time);
        m_intraday_map      = FindTopographicalBoundary(zones, zone_count, 4, day_start, 0);
        m_prev_intraday_map = FindTopographicalBoundary(zones, zone_count, 4, prev_day_start, day_start);
        m_last_intraday_bar = current_m1_bar;
    }
}

//+------------------------------------------------------------------+
//| FindTopographicalBoundary - Stacked Per-TF Scanner               |
//+------------------------------------------------------------------+
SessionBoundary CContextMapper::FindTopographicalBoundary(const B2BZoneInfo &zones[], int zone_count, int max_tf_level, datetime start_time, datetime end_time) const
{
    SessionBoundary bounds;
    for(int i=0; i<zone_count; i++)
    {
        if(!zones[i].IsValid()) continue;
        
        bool tf_allowed = false;
        if(max_tf_level <= 0 && zones[i].timeframe == PERIOD_MN1) tf_allowed = true;
        if(max_tf_level <= 1 && zones[i].timeframe == PERIOD_W1)  tf_allowed = true;
        if(max_tf_level <= 2 && zones[i].timeframe == PERIOD_D1)  tf_allowed = true;
        if(max_tf_level <= 3 && zones[i].timeframe == PERIOD_H4)  tf_allowed = true;
        if(max_tf_level <= 4 && (zones[i].timeframe == PERIOD_H1 || zones[i].timeframe == PERIOD_M30)) tf_allowed = true;
        
        if(!tf_allowed) continue;
        if(zones[i].zone_created_time < start_time) continue; 
        if(end_time > 0 && zones[i].zone_created_time >= end_time) continue;
        
        if(zones[i].direction == DIRECTION_BEARISH) 
        {
            if(zones[i].timeframe == PERIOD_MN1 && zones[i].L1_price > bounds.mn1_high_price) { bounds.mn1_high_price = zones[i].L1_price; bounds.mn1_high_id = zones[i].zone_id; }
            if(zones[i].timeframe == PERIOD_W1  && zones[i].L1_price > bounds.w1_high_price)  { bounds.w1_high_price = zones[i].L1_price;  bounds.w1_high_id = zones[i].zone_id; }
            if(zones[i].timeframe == PERIOD_D1  && zones[i].L1_price > bounds.d1_high_price)  { bounds.d1_high_price = zones[i].L1_price;  bounds.d1_high_id = zones[i].zone_id; }
            if(zones[i].timeframe == PERIOD_H4  && zones[i].L1_price > bounds.h4_high_price)  { bounds.h4_high_price = zones[i].L1_price;  bounds.h4_high_id = zones[i].zone_id; }
            if(zones[i].timeframe == PERIOD_H1  && zones[i].L1_price > bounds.h1_high_price)  { bounds.h1_high_price = zones[i].L1_price;  bounds.h1_high_id = zones[i].zone_id; }
            if(zones[i].timeframe == PERIOD_M30 && zones[i].L1_price > bounds.m30_high_price) { bounds.m30_high_price = zones[i].L1_price; bounds.m30_high_id = zones[i].zone_id; }
        }
        else 
        {
            if(zones[i].timeframe == PERIOD_MN1 && zones[i].L1_price < bounds.mn1_low_price) { bounds.mn1_low_price = zones[i].L1_price; bounds.mn1_low_id = zones[i].zone_id; }
            if(zones[i].timeframe == PERIOD_W1  && zones[i].L1_price < bounds.w1_low_price)  { bounds.w1_low_price = zones[i].L1_price;  bounds.w1_low_id = zones[i].zone_id; }
            if(zones[i].timeframe == PERIOD_D1  && zones[i].L1_price < bounds.d1_low_price)  { bounds.d1_low_price = zones[i].L1_price;  bounds.d1_low_id = zones[i].zone_id; }
            if(zones[i].timeframe == PERIOD_H4  && zones[i].L1_price < bounds.h4_low_price)  { bounds.h4_low_price = zones[i].L1_price;  bounds.h4_low_id = zones[i].zone_id; }
            if(zones[i].timeframe == PERIOD_H1  && zones[i].L1_price < bounds.h1_low_price)  { bounds.h1_low_price = zones[i].L1_price;  bounds.h1_low_id = zones[i].zone_id; }
            if(zones[i].timeframe == PERIOD_M30 && zones[i].L1_price < bounds.m30_low_price) { bounds.m30_low_price = zones[i].L1_price; bounds.m30_low_id = zones[i].zone_id; }
        }
    }
    return bounds;
}

//+------------------------------------------------------------------+
//| Helper: Get the absolute highest resistance from a SessionBoundary|
//+------------------------------------------------------------------+
double CContextMapper::GetHighestResistance(const SessionBoundary &map) const
{
    double h = 0;
    if(map.mn1_high_price > h) h = map.mn1_high_price;
    if(map.w1_high_price > h)  h = map.w1_high_price;
    if(map.d1_high_price > h)  h = map.d1_high_price;
    if(map.h4_high_price > h)  h = map.h4_high_price;
    if(map.h1_high_price > h)  h = map.h1_high_price;
    if(map.m30_high_price > h) h = map.m30_high_price;
    return h;
}

//+------------------------------------------------------------------+
//| Helper: Get the absolute lowest support from a SessionBoundary   |
//+------------------------------------------------------------------+
double CContextMapper::GetLowestSupport(const SessionBoundary &map) const
{
    double l = DBL_MAX;
    if(map.mn1_low_price < l) l = map.mn1_low_price;
    if(map.w1_low_price < l)  l = map.w1_low_price;
    if(map.d1_low_price < l)  l = map.d1_low_price;
    if(map.h4_low_price < l)  l = map.h4_low_price;
    if(map.h1_low_price < l)  l = map.h1_low_price;
    if(map.m30_low_price < l) l = map.m30_low_price;
    return l;
}

//+------------------------------------------------------------------+
//| GetEpochPosition: Where is price in the monthly range? (0.0-1.0)|
//+------------------------------------------------------------------+
double CContextMapper::GetEpochPosition(ENUM_SIGNAL_DIRECTION dir, double current_price) const
{
    double ceiling = GetHighestResistance(m_monthly_map);
    double floor = GetLowestSupport(m_monthly_map);
    
    // Fallback to weekly if monthly is vacuum
    if(ceiling == 0.0) ceiling = GetHighestResistance(m_weekly_map);
    if(floor == DBL_MAX) floor = GetLowestSupport(m_weekly_map);
    
    // Fallback to intraday
    if(ceiling == 0.0) ceiling = GetHighestResistance(m_intraday_map);
    if(floor == DBL_MAX) floor = GetLowestSupport(m_intraday_map);
    
    if(ceiling == 0.0 || floor == DBL_MAX || ceiling <= floor) return 0.5;
    
    double range = ceiling - floor;
    double position = (current_price - floor) / range;
    
    if(position < 0.0) position = 0.0;
    if(position > 1.0) position = 1.0;
    
    return position;
}

//+------------------------------------------------------------------+
//| GetIntradayPosition: Price position in today's range (0.0-1.0)  |
//| Uses today + yesterday H1/M30 walls                             |
//+------------------------------------------------------------------+
double CContextMapper::GetIntradayPosition(double current_price) const
{
    double ceiling = GetHighestResistance(m_intraday_map);
    double floor = GetLowestSupport(m_intraday_map);
    
    // Extend with yesterday's walls for fuller picture
    double prev_ceiling = GetHighestResistance(m_prev_intraday_map);
    double prev_floor = GetLowestSupport(m_prev_intraday_map);
    
    if(prev_ceiling > ceiling) ceiling = prev_ceiling;
    if(prev_floor < floor) floor = prev_floor;
    
    if(ceiling == 0.0 || floor == DBL_MAX || ceiling <= floor) return 0.5;
    
    double range = ceiling - floor;
    double position = (current_price - floor) / range;
    
    if(position < 0.0) position = 0.0;
    if(position > 1.0) position = 1.0;
    
    return position;
}

//+------------------------------------------------------------------+
//| IsBreakout: Has price broken ALL epoch walls in this direction?  |
//+------------------------------------------------------------------+
bool CContextMapper::IsBreakout(ENUM_SIGNAL_DIRECTION dir, double current_price) const
{
    if(dir == DIRECTION_BULLISH)
    {
        double monthly_ceiling = GetHighestResistance(m_monthly_map);
        double prev_monthly_ceiling = GetHighestResistance(m_prev_monthly_map);
        
        if(monthly_ceiling == 0.0 && prev_monthly_ceiling == 0.0) return true;
        if(monthly_ceiling > 0.0 && current_price <= monthly_ceiling) return false;
        if(prev_monthly_ceiling > 0.0 && current_price <= prev_monthly_ceiling) return false;
        return true;
    }
    else
    {
        double monthly_floor = GetLowestSupport(m_monthly_map);
        double prev_monthly_floor = GetLowestSupport(m_prev_monthly_map);
        
        if(monthly_floor == DBL_MAX && prev_monthly_floor == DBL_MAX) return true;
        if(monthly_floor < DBL_MAX && current_price >= monthly_floor) return false;
        if(prev_monthly_floor < DBL_MAX && current_price >= prev_monthly_floor) return false;
        return true;
    }
}

//+------------------------------------------------------------------+
//| GetTargetCoordinate: Nearest Wall in Direction                   |
//+------------------------------------------------------------------+
double CContextMapper::GetTargetCoordinate(ENUM_SIGNAL_DIRECTION dir, double current_price) const
{
    double target = (dir == DIRECTION_BULLISH) ? DBL_MAX : 0.0;
    
    if(dir == DIRECTION_BULLISH)
    {
        if(m_monthly_map.mn1_high_price > current_price && m_monthly_map.mn1_high_price < target) target = m_monthly_map.mn1_high_price;
        if(m_monthly_map.w1_high_price > current_price  && m_monthly_map.w1_high_price < target)  target = m_monthly_map.w1_high_price;
        if(m_monthly_map.d1_high_price > current_price  && m_monthly_map.d1_high_price < target)  target = m_monthly_map.d1_high_price;
        if(m_weekly_map.h4_high_price > current_price    && m_weekly_map.h4_high_price < target)   target = m_weekly_map.h4_high_price;
        if(m_intraday_map.h1_high_price > current_price  && m_intraday_map.h1_high_price < target) target = m_intraday_map.h1_high_price;
        if(m_intraday_map.m30_high_price > current_price && m_intraday_map.m30_high_price < target) target = m_intraday_map.m30_high_price;
        if(target == DBL_MAX) target = 0.0;
    }
    else if(dir == DIRECTION_BEARISH)
    {
        if(m_monthly_map.mn1_low_price < current_price && m_monthly_map.mn1_low_price != DBL_MAX && m_monthly_map.mn1_low_price > target) target = m_monthly_map.mn1_low_price;
        if(m_monthly_map.w1_low_price < current_price  && m_monthly_map.w1_low_price != DBL_MAX  && m_monthly_map.w1_low_price > target)  target = m_monthly_map.w1_low_price;
        if(m_monthly_map.d1_low_price < current_price  && m_monthly_map.d1_low_price != DBL_MAX  && m_monthly_map.d1_low_price > target)  target = m_monthly_map.d1_low_price;
        if(m_weekly_map.h4_low_price < current_price    && m_weekly_map.h4_low_price != DBL_MAX   && m_weekly_map.h4_low_price > target)   target = m_weekly_map.h4_low_price;
        if(m_intraday_map.h1_low_price < current_price  && m_intraday_map.h1_low_price != DBL_MAX && m_intraday_map.h1_low_price > target) target = m_intraday_map.h1_low_price;
        if(m_intraday_map.m30_low_price < current_price && m_intraday_map.m30_low_price != DBL_MAX && m_intraday_map.m30_low_price > target) target = m_intraday_map.m30_low_price;
    }
    
    return target;
}

double CContextMapper::GetDistanceToWall(ENUM_SIGNAL_DIRECTION dir, double current_price) const
{
    double target = GetTargetCoordinate(dir, current_price);
    if(target == 0.0 || target == DBL_MAX) return DBL_MAX;
    return MathMax(MathAbs(target - current_price), 0.0);
}

//+------------------------------------------------------------------+
//| IsPathBlocked - Spatial Roadblock Query                          |
//+------------------------------------------------------------------+
ulong CContextMapper::IsPathBlocked(ENUM_SIGNAL_DIRECTION dir, double current_price,
                                     ENUM_TIMEFRAMES scan_tf, const B2BZoneInfo &zones[],
                                     int zone_count, ulong siege_magnet_id) const
{
    if(scan_tf == PERIOD_MN1) return 0;
    
    bool check_mn1 = true;
    bool check_w1 = (scan_tf == PERIOD_D1 || scan_tf == PERIOD_H4 || scan_tf == PERIOD_H1 || scan_tf == PERIOD_M30);
    bool check_d1 = (scan_tf == PERIOD_H4 || scan_tf == PERIOD_H1 || scan_tf == PERIOD_M30);
    
    for(int i=0; i<zone_count; i++)
    {
        if(!zones[i].IsValid()) continue;
        if(zones[i].direction == dir) continue;
        
        bool tf_match = false;
        if(check_mn1 && zones[i].timeframe == PERIOD_MN1) tf_match = true;
        if(check_w1  && zones[i].timeframe == PERIOD_W1)  tf_match = true;
        if(check_d1  && zones[i].timeframe == PERIOD_D1)  tf_match = true;
        if(!tf_match) continue;
        
        if(zones[i].L2_touched) continue;
        
        double high = MathMax(zones[i].L1_price, zones[i].L2_price);
        double low = MathMin(zones[i].L1_price, zones[i].L2_price);
        
        if(current_price <= high && current_price >= low)
        {
            if(siege_magnet_id > 0 && zones[i].zone_id == siege_magnet_id) continue; 
            return zones[i].zone_id;
        }
    }
    return 0;
}

//+------------------------------------------------------------------+
//| Time Utility Functions                                           |
//+------------------------------------------------------------------+
datetime CContextMapper::GetMonthStart(datetime time) const
{
    MqlDateTime dt;
    TimeToStruct(time, dt);
    dt.day = 1; dt.hour = 0; dt.min = 0; dt.sec = 0;
    return StructToTime(dt);
}

datetime CContextMapper::GetPrevMonthStart(datetime time) const
{
    MqlDateTime dt;
    TimeToStruct(time, dt);
    dt.day = 1; dt.hour = 0; dt.min = 0; dt.sec = 0;
    if(dt.mon == 1) { dt.mon = 12; dt.year -= 1; }
    else { dt.mon -= 1; }
    return StructToTime(dt);
}

datetime CContextMapper::GetWeekStart(datetime time) const
{
    MqlDateTime dt;
    TimeToStruct(time, dt);
    int days_since_monday = dt.day_of_week - 1;
    if(days_since_monday < 0) days_since_monday = 6;
    datetime day_start = GetDayStart(time);
    return day_start - (days_since_monday * 86400);
}

datetime CContextMapper::GetPrevWeekStart(datetime time) const { return GetWeekStart(time) - (7 * 86400); }
datetime CContextMapper::GetDayStart(datetime time) const { return time - (time % 86400); }
datetime CContextMapper::GetPrevDayStart(datetime time) const { return GetDayStart(time) - 86400; }

string CContextMapper::GetTFString(ENUM_TIMEFRAMES tf) const
{
    if(tf == PERIOD_MN1) return "MN1";
    if(tf == PERIOD_W1) return "W1";
    if(tf == PERIOD_D1) return "D1";
    if(tf == PERIOD_H4) return "H4";
    if(tf == PERIOD_H1) return "H1";
    if(tf == PERIOD_M30) return "M30";
    return "UKN";
}

#endif // V50_CONTEXTMAPPER_MQH
