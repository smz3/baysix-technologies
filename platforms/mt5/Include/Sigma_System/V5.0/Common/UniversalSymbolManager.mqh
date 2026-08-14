//+------------------------------------------------------------------+
//|                                        UniversalSymbolManager.mqh |
//|                             Copyright 2025, Sigma Trading System |
//+------------------------------------------------------------------+
//| V5.0 CLEAN SLATE - B2B ONLY                                      |
//| Universal Symbol Detection & Auto-Adjustment for multi-symbol    |
//+------------------------------------------------------------------+
#ifndef V50_UNIVERSALSYMBOLMANAGER_MQH
#define V50_UNIVERSALSYMBOLMANAGER_MQH

#property strict

//+------------------------------------------------------------------+
//| Symbol Type Classification                                       |
//+------------------------------------------------------------------+
enum ENUM_SYMBOL_TYPE
  {
   SYMBOL_FOREX_MAJOR,     // Major forex pairs (EURUSD, GBPUSD, etc.)
   SYMBOL_FOREX_JPY,       // JPY pairs (USDJPY, EURJPY, etc.)
   SYMBOL_FOREX_EXOTIC,    // Exotic pairs (USDZAR, USDMXN, etc.)
   SYMBOL_METAL,           // Precious metals (XAUUSD, XAGUSD)
   SYMBOL_CRYPTO,          // Cryptocurrencies (BTCUSD, ETHUSD)
   SYMBOL_INDEX,           // Stock indices (US30, DE30, etc.)
   SYMBOL_ENERGY,          // Energy commodities (CRUDE, BRENT)
   SYMBOL_UNKNOWN          // Unknown/unsupported symbol type
  };

//+------------------------------------------------------------------+
//| Symbol Information Structure                                     |
//+------------------------------------------------------------------+
struct SymbolInfo
  {
   string              symbol_name;        // Normalized symbol name
   ENUM_SYMBOL_TYPE    symbol_type;        // Detected symbol type
   double              pip_size;           // Pip size for this symbol
   double              tick_value;         // Tick value per lot
   double              tick_size;          // Minimum tick size
   double              pip_value_per_lot;  // Calculated pip value per lot
   double              point_size;         // Point size
   int                 digits;             // Number of decimal places
   double              min_lot;            // Minimum lot size
   double              max_lot;            // Maximum lot size
   double              lot_step;           // Lot step size
   bool                is_valid;           // Data validation flag
   datetime            last_update;        // Last update timestamp
   
   SymbolInfo()
     {
      symbol_name = "";
      symbol_type = SYMBOL_UNKNOWN;
      pip_size = 0.0;
      tick_value = 0.0;
      tick_size = 0.0;
      pip_value_per_lot = 0.0;
      point_size = 0.0;
      digits = 0;
      min_lot = 0.0;
      max_lot = 0.0;
      lot_step = 0.0;
      is_valid = false;
      last_update = 0;
     }
   
   SymbolInfo(const SymbolInfo &other)
     {
      symbol_name = other.symbol_name;
      symbol_type = other.symbol_type;
      pip_size = other.pip_size;
      tick_value = other.tick_value;
      tick_size = other.tick_size;
      pip_value_per_lot = other.pip_value_per_lot;
      point_size = other.point_size;
      digits = other.digits;
      min_lot = other.min_lot;
      max_lot = other.max_lot;
      lot_step = other.lot_step;
      is_valid = other.is_valid;
      last_update = other.last_update;
     }
  };

//+------------------------------------------------------------------+
//| Universal Symbol Manager Class                                   |
//+------------------------------------------------------------------+
class CUniversalSymbolManager
  {
private:
   SymbolInfo          m_symbol_cache[];
   int                 m_cache_size;
   datetime            m_last_cleanup;
   
   // Classification
   ENUM_SYMBOL_TYPE    DetectSymbolType(const string &symbol);
   bool                IsForexMajor(const string &symbol);
   bool                IsForexJPY(const string &symbol);
   bool                IsForexExotic(const string &symbol);
   bool                IsMetal(const string &symbol);
   bool                IsCrypto(const string &symbol);
   bool                IsIndex(const string &symbol);
   bool                IsEnergy(const string &symbol);
   
   // Analysis
   double              GetSymbolPipSize(const string &symbol, ENUM_SYMBOL_TYPE type);
   double              CalculatePipValuePerLot(const string &symbol);
   bool                ValidateSymbolData(const string &symbol);
   string              NormalizeSymbolName(const string &symbol);
   
   // Cache
   int                 FindSymbolInCache(const string &symbol);
   bool                AddToCache(const SymbolInfo &info);
   void                CleanupCache();
   bool                IsCacheValid(const SymbolInfo &info);

public:
                       CUniversalSymbolManager();
                      ~CUniversalSymbolManager();
   
   bool                Initialize();
   bool                AnalyzeSymbol(const string &symbol);
   SymbolInfo          GetSymbolInfo(const string &symbol);
   
   // Position Sizing
   double              GetPipValuePerLot(const string &symbol);
   double              CalculateOptimalLotSize(const string &symbol, double risk_amount, double stop_loss_pips);
   
   // Conversion
   double              ConvertPipsToPrice(const string &symbol, double pips);
   double              ConvertPriceToPips(const string &symbol, double price_distance);
   
   // Market Info
   double              GetRealTimeSpread(const string &symbol);
   
   // Validation
   bool                IsSymbolSupported(const string &symbol);
   string              GetSymbolTypeString(ENUM_SYMBOL_TYPE type);
  };

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CUniversalSymbolManager::CUniversalSymbolManager()
  {
   m_cache_size = 0;
   m_last_cleanup = 0;
   ArrayResize(m_symbol_cache, 50);
  }

//+------------------------------------------------------------------+
//| Destructor                                                       |
//+------------------------------------------------------------------+
CUniversalSymbolManager::~CUniversalSymbolManager()
  {
   ArrayFree(m_symbol_cache);
  }

//+------------------------------------------------------------------+
//| Initialize                                                       |
//+------------------------------------------------------------------+
bool CUniversalSymbolManager::Initialize()
  {
   CleanupCache();
   return true;
  }

//+------------------------------------------------------------------+
//| DetectSymbolType                                                 |
//+------------------------------------------------------------------+
ENUM_SYMBOL_TYPE CUniversalSymbolManager::DetectSymbolType(const string &symbol)
  {
   string normalized = NormalizeSymbolName(symbol);
   
   if(IsForexJPY(normalized))    return SYMBOL_FOREX_JPY;
   if(IsForexMajor(normalized))  return SYMBOL_FOREX_MAJOR;
   if(IsMetal(normalized))       return SYMBOL_METAL;
   if(IsCrypto(normalized))      return SYMBOL_CRYPTO;
   if(IsIndex(normalized))       return SYMBOL_INDEX;
   if(IsEnergy(normalized))      return SYMBOL_ENERGY;
   if(IsForexExotic(normalized)) return SYMBOL_FOREX_EXOTIC;
   
   return SYMBOL_UNKNOWN;
  }

//+------------------------------------------------------------------+
//| IsForexMajor                                                     |
//+------------------------------------------------------------------+
bool CUniversalSymbolManager::IsForexMajor(const string &symbol)
  {
   string majors[] = {"EURUSD", "GBPUSD", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
                      "EURGBP", "EURAUD", "EURCHF", "GBPCHF", "AUDCHF", "GBPAUD",
                      "AUDCAD", "GBPCAD", "AUDNZD", "GBPNZD", "EURNZD", "EURCAD"};
   
   for(int i = 0; i < ArraySize(majors); i++)
     {
      if(StringFind(symbol, majors[i]) >= 0)
         return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| IsForexJPY                                                       |
//+------------------------------------------------------------------+
bool CUniversalSymbolManager::IsForexJPY(const string &symbol)
  {
   return (StringFind(symbol, "JPY") >= 0);
  }

//+------------------------------------------------------------------+
//| IsForexExotic                                                    |
//+------------------------------------------------------------------+
bool CUniversalSymbolManager::IsForexExotic(const string &symbol)
  {
   string exotics[] = {"ZAR", "MXN", "TRY", "PLN", "HUF", "CZK", "SEK", "NOK", "DKK"};
   
   for(int i = 0; i < ArraySize(exotics); i++)
     {
      if(StringFind(symbol, exotics[i]) >= 0)
         return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| IsMetal                                                          |
//+------------------------------------------------------------------+
bool CUniversalSymbolManager::IsMetal(const string &symbol)
  {
   string metals[] = {"XAU", "GOLD", "XAG", "SILVER", "XPD", "XPT"};
   
   for(int i = 0; i < ArraySize(metals); i++)
     {
      if(StringFind(symbol, metals[i]) >= 0)
         return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| IsCrypto                                                         |
//+------------------------------------------------------------------+
bool CUniversalSymbolManager::IsCrypto(const string &symbol)
  {
   string cryptos[] = {"BTC", "ETH", "LTC", "XRP", "ADA", "DOT", "LINK"};
   
   for(int i = 0; i < ArraySize(cryptos); i++)
     {
      if(StringFind(symbol, cryptos[i]) >= 0)
         return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| IsIndex                                                          |
//+------------------------------------------------------------------+
bool CUniversalSymbolManager::IsIndex(const string &symbol)
  {
   string indices[] = {"US30", "SPX500", "NAS100", "DE30", "UK100", "FR40", "JP225"};
   
   for(int i = 0; i < ArraySize(indices); i++)
     {
      if(StringFind(symbol, indices[i]) >= 0)
         return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| IsEnergy                                                         |
//+------------------------------------------------------------------+
bool CUniversalSymbolManager::IsEnergy(const string &symbol)
  {
   string energy[] = {"CRUDE", "BRENT", "WTI", "NGAS", "OIL"};
   
   for(int i = 0; i < ArraySize(energy); i++)
     {
      if(StringFind(symbol, energy[i]) >= 0)
         return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| GetSymbolPipSize                                                 |
//+------------------------------------------------------------------+
double CUniversalSymbolManager::GetSymbolPipSize(const string &symbol, ENUM_SYMBOL_TYPE type)
  {
   switch(type)
     {
      case SYMBOL_FOREX_MAJOR:
      case SYMBOL_FOREX_EXOTIC:
         return 0.0001;
         
      case SYMBOL_FOREX_JPY:
         return 0.01;
         
      case SYMBOL_METAL:
         if(StringFind(symbol, "XAU") >= 0 || StringFind(symbol, "GOLD") >= 0)
            return 0.1;
         else if(StringFind(symbol, "XAG") >= 0 || StringFind(symbol, "SILVER") >= 0)
            return 0.001;
         else
            return 0.01;
            
      case SYMBOL_CRYPTO:
         return 1.0;
         
      case SYMBOL_INDEX:
      case SYMBOL_ENERGY:
         return 0.01;
         
      default:
         return 0.0;
     }
  }

//+------------------------------------------------------------------+
//| CalculatePipValuePerLot                                          |
//+------------------------------------------------------------------+
double CUniversalSymbolManager::CalculatePipValuePerLot(const string &symbol)
  {
   double tick_value = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   
   if(tick_value <= 0.0 || tick_size <= 0.0)
      return 0.0;
   
   ENUM_SYMBOL_TYPE type = DetectSymbolType(symbol);
   double pip_size = GetSymbolPipSize(symbol, type);
   
   double pip_value_per_lot = (tick_value / tick_size) * pip_size;
   
   if(pip_value_per_lot <= 0.0 || pip_value_per_lot > 10000.0)
      pip_value_per_lot = MathMax(0.1, MathMin(pip_value_per_lot, 1000.0));
   
   return pip_value_per_lot;
  }

//+------------------------------------------------------------------+
//| AnalyzeSymbol                                                    |
//+------------------------------------------------------------------+
bool CUniversalSymbolManager::AnalyzeSymbol(const string &symbol)
  {
   int cache_index = FindSymbolInCache(symbol);
   if(cache_index >= 0 && IsCacheValid(m_symbol_cache[cache_index]))
      return true;
   
   SymbolInfo info;
   info.symbol_name = NormalizeSymbolName(symbol);
   info.symbol_type = DetectSymbolType(symbol);
   info.pip_size = GetSymbolPipSize(symbol, info.symbol_type);
   info.tick_value = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   info.tick_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   info.point_size = SymbolInfoDouble(symbol, SYMBOL_POINT);
   info.digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   info.min_lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   info.max_lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   info.lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   info.pip_value_per_lot = CalculatePipValuePerLot(symbol);
   info.is_valid = ValidateSymbolData(symbol);
   info.last_update = TimeCurrent();
   
   return AddToCache(info);
  }

//+------------------------------------------------------------------+
//| GetSymbolInfo                                                    |
//+------------------------------------------------------------------+
SymbolInfo CUniversalSymbolManager::GetSymbolInfo(const string &symbol)
  {
   SymbolInfo empty_info;
   
   if(!AnalyzeSymbol(symbol))
      return empty_info;
   
   int cache_index = FindSymbolInCache(symbol);
   if(cache_index >= 0)
      return m_symbol_cache[cache_index];
   
   return empty_info;
  }

//+------------------------------------------------------------------+
//| GetPipValuePerLot                                                |
//+------------------------------------------------------------------+
double CUniversalSymbolManager::GetPipValuePerLot(const string &symbol)
  {
   SymbolInfo info = GetSymbolInfo(symbol);
   if(info.is_valid)
      return info.pip_value_per_lot;
   
   return 0.0;
  }

//+------------------------------------------------------------------+
//| CalculateOptimalLotSize                                          |
//+------------------------------------------------------------------+
double CUniversalSymbolManager::CalculateOptimalLotSize(const string &symbol, double risk_amount, double stop_loss_pips)
  {
   if(risk_amount <= 0.0 || stop_loss_pips <= 0.0)
      return 0.0;
   
   double pip_value = GetPipValuePerLot(symbol);
   if(pip_value <= 0.0)
      return 0.0;
   
   double lot_size = risk_amount / (stop_loss_pips * pip_value);
   
   SymbolInfo info = GetSymbolInfo(symbol);
   if(info.is_valid)
     {
      lot_size = MathMax(lot_size, info.min_lot);
      lot_size = MathMin(lot_size, info.max_lot);
      
      if(info.lot_step > 0.0)
         lot_size = MathRound(lot_size / info.lot_step) * info.lot_step;
     }
   
   return lot_size;
  }

//+------------------------------------------------------------------+
//| ConvertPipsToPrice                                               |
//+------------------------------------------------------------------+
double CUniversalSymbolManager::ConvertPipsToPrice(const string &symbol, double pips)
  {
   SymbolInfo info = GetSymbolInfo(symbol);
   if(info.is_valid)
      return pips * info.pip_size;
   
   return 0.0;
  }

//+------------------------------------------------------------------+
//| ConvertPriceToPips                                               |
//+------------------------------------------------------------------+
double CUniversalSymbolManager::ConvertPriceToPips(const string &symbol, double price_distance)
  {
   SymbolInfo info = GetSymbolInfo(symbol);
   if(info.is_valid && info.pip_size > 0.0)
      return price_distance / info.pip_size;
   
   return 0.0;
  }

//+------------------------------------------------------------------+
//| GetRealTimeSpread                                                |
//+------------------------------------------------------------------+
double CUniversalSymbolManager::GetRealTimeSpread(const string &symbol)
  {
   int spread_points = (int)SymbolInfoInteger(symbol, SYMBOL_SPREAD);
   double point_size = SymbolInfoDouble(symbol, SYMBOL_POINT);
   
   return spread_points * point_size;
  }

//+------------------------------------------------------------------+
//| NormalizeSymbolName                                              |
//+------------------------------------------------------------------+
string CUniversalSymbolManager::NormalizeSymbolName(const string &symbol)
  {
   string normalized = symbol;
   
   StringReplace(normalized, ".m", "");
   StringReplace(normalized, ".raw", "");
   StringReplace(normalized, ".ecn", "");
   StringReplace(normalized, ".pro", "");
   StringReplace(normalized, "_", "");
   StringReplace(normalized, "-", "");
   StringToUpper(normalized);
   
   return normalized;
  }

//+------------------------------------------------------------------+
//| ValidateSymbolData                                               |
//+------------------------------------------------------------------+
bool CUniversalSymbolManager::ValidateSymbolData(const string &symbol)
  {
   double tick_value = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   
   return (tick_value > 0.0 && tick_size > 0.0 && point > 0.0);
  }

//+------------------------------------------------------------------+
//| FindSymbolInCache                                                |
//+------------------------------------------------------------------+
int CUniversalSymbolManager::FindSymbolInCache(const string &symbol)
  {
   string normalized = NormalizeSymbolName(symbol);
   
   for(int i = 0; i < m_cache_size; i++)
     {
      if(m_symbol_cache[i].symbol_name == normalized)
         return i;
     }
   return -1;
  }

//+------------------------------------------------------------------+
//| AddToCache                                                       |
//+------------------------------------------------------------------+
bool CUniversalSymbolManager::AddToCache(const SymbolInfo &info)
  {
   if(m_cache_size >= ArraySize(m_symbol_cache))
      ArrayResize(m_symbol_cache, ArraySize(m_symbol_cache) + 20);
   
   int index = FindSymbolInCache(info.symbol_name);
   if(index >= 0)
     {
      m_symbol_cache[index] = info;
     }
   else
     {
      m_symbol_cache[m_cache_size] = info;
      m_cache_size++;
     }
   
   return true;
  }

//+------------------------------------------------------------------+
//| IsCacheValid                                                     |
//+------------------------------------------------------------------+
bool CUniversalSymbolManager::IsCacheValid(const SymbolInfo &info)
  {
   return (TimeCurrent() - info.last_update < 3600);
  }

//+------------------------------------------------------------------+
//| CleanupCache                                                     |
//+------------------------------------------------------------------+
void CUniversalSymbolManager::CleanupCache()
  {
   if(TimeCurrent() - m_last_cleanup < 1800)
      return;
      
   int valid_count = 0;
   SymbolInfo temp_cache[];
   ArrayResize(temp_cache, m_cache_size);
   
   for(int i = 0; i < m_cache_size; i++)
     {
      if(IsCacheValid(m_symbol_cache[i]))
        {
         temp_cache[valid_count] = m_symbol_cache[i];
         valid_count++;
        }
     }
   
   ArrayResize(m_symbol_cache, valid_count);
   for(int i = 0; i < valid_count; i++)
      m_symbol_cache[i] = temp_cache[i];
   
   m_cache_size = valid_count;
   m_last_cleanup = TimeCurrent();
  }

//+------------------------------------------------------------------+
//| IsSymbolSupported                                                |
//+------------------------------------------------------------------+
bool CUniversalSymbolManager::IsSymbolSupported(const string &symbol)
  {
   return (DetectSymbolType(symbol) != SYMBOL_UNKNOWN);
  }

//+------------------------------------------------------------------+
//| GetSymbolTypeString                                              |
//+------------------------------------------------------------------+
string CUniversalSymbolManager::GetSymbolTypeString(ENUM_SYMBOL_TYPE type)
  {
   switch(type)
     {
      case SYMBOL_FOREX_MAJOR:  return "Forex Major";
      case SYMBOL_FOREX_JPY:    return "Forex JPY";
      case SYMBOL_FOREX_EXOTIC: return "Forex Exotic";
      case SYMBOL_METAL:        return "Metal";
      case SYMBOL_CRYPTO:       return "Cryptocurrency";
      case SYMBOL_INDEX:        return "Index";
      case SYMBOL_ENERGY:       return "Energy";
      default:                  return "Unknown";
     }
  }

#endif // V50_UNIVERSALSYMBOLMANAGER_MQH
