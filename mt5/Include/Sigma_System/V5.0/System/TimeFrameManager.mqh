//+------------------------------------------------------------------+
//|                                             TimeFrameManager.mqh |
//|                             Copyright 2025, Sigma Trading System |
//+------------------------------------------------------------------+
//| V5.0 CLEAN SLATE - B2B ONLY                                      |
//| Manages timeframe pairs and new bar detection                    |
//+------------------------------------------------------------------+
#ifndef V50_TIMEFRAMEMANAGER_MQH
#define V50_TIMEFRAMEMANAGER_MQH

#property strict

#include "../Common/Defines.mqh"

//+------------------------------------------------------------------+
//| S_TimeFramePair Structure (moved here from Structures.mqh)       |
//+------------------------------------------------------------------+
struct S_TimeFramePair
  {
   ENUM_TIMEFRAMES   primary_tf;
   ENUM_TIMEFRAMES   secondary_tf;
  };

//+------------------------------------------------------------------+
//| Global Timeframes Array                                          |
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES g_timeframes[TOTAL_TIMEFRAMES] = {
   PERIOD_M1, PERIOD_M5, PERIOD_M15, PERIOD_M30, PERIOD_H1,
   PERIOD_H4, PERIOD_D1, PERIOD_W1, PERIOD_MN1
};

//+------------------------------------------------------------------+
//| CTimeFrameManager Class                                          |
//| Manages all time-related logic for the EA.                       |
//+------------------------------------------------------------------+
class CTimeFrameManager
  {
private:
   S_TimeFramePair   m_tf_pairs[8];             // 8 TF pairs
   datetime          m_last_bar_time[10];       // Last bar time for each TF
   ENUM_TIMEFRAMES   m_unique_tfs[9];           // 9 unique timeframes

public:
                     CTimeFrameManager(void);

   bool              IsNewBar(const ENUM_TIMEFRAMES timeframe);
   S_TimeFramePair   GetTimeFramePair(int index);
   int               TotalPairs();
   ENUM_TIMEFRAMES   GetSecondaryTimeFrame(ENUM_TIMEFRAMES primary_tf);
   ENUM_TIMEFRAMES   GetPrimaryTimeFrame(ENUM_TIMEFRAMES secondary_tf);
   bool              IsPrimaryTimeFrame(ENUM_TIMEFRAMES tf);
   int               TimeFrameToIndex(const ENUM_TIMEFRAMES timeframe);

private:
   void              InitializeTimeFramePairs();
  };

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CTimeFrameManager::CTimeFrameManager(void)
  {
   InitializeTimeFramePairs();
   ArrayInitialize(m_last_bar_time, 0);
   m_unique_tfs[0] = PERIOD_M1;
   m_unique_tfs[1] = PERIOD_M5;
   m_unique_tfs[2] = PERIOD_M15;
   m_unique_tfs[3] = PERIOD_M30;
   m_unique_tfs[4] = PERIOD_H1;
   m_unique_tfs[5] = PERIOD_H4;
   m_unique_tfs[6] = PERIOD_D1;
   m_unique_tfs[7] = PERIOD_W1;
   m_unique_tfs[8] = PERIOD_MN1;
  }

//+------------------------------------------------------------------+
//| InitializeTimeFramePairs                                         |
//+------------------------------------------------------------------+
void CTimeFrameManager::InitializeTimeFramePairs()
  {
   m_tf_pairs[0].primary_tf = PERIOD_MN1; m_tf_pairs[0].secondary_tf = PERIOD_W1;
   m_tf_pairs[1].primary_tf = PERIOD_W1;  m_tf_pairs[1].secondary_tf = PERIOD_D1;
   m_tf_pairs[2].primary_tf = PERIOD_D1;  m_tf_pairs[2].secondary_tf = PERIOD_H4;
   m_tf_pairs[3].primary_tf = PERIOD_H4;  m_tf_pairs[3].secondary_tf = PERIOD_H1;
   m_tf_pairs[4].primary_tf = PERIOD_H1;  m_tf_pairs[4].secondary_tf = PERIOD_M30;
   m_tf_pairs[5].primary_tf = PERIOD_M30; m_tf_pairs[5].secondary_tf = PERIOD_M15;
   m_tf_pairs[6].primary_tf = PERIOD_M15; m_tf_pairs[6].secondary_tf = PERIOD_M5;
   m_tf_pairs[7].primary_tf = PERIOD_M5;  m_tf_pairs[7].secondary_tf = PERIOD_M1;
  }

//+------------------------------------------------------------------+
//| IsNewBar                                                         |
//+------------------------------------------------------------------+
bool CTimeFrameManager::IsNewBar(const ENUM_TIMEFRAMES timeframe)
  {
   int index = TimeFrameToIndex(timeframe);
   if(index < 0) 
      return false;

   datetime current_bar_time = iTime(_Symbol, timeframe, 0);

   if(current_bar_time > m_last_bar_time[index])
     {
      m_last_bar_time[index] = current_bar_time;
      return true;
     }

   return false;
  }

//+------------------------------------------------------------------+
//| TimeFrameToIndex                                                 |
//+------------------------------------------------------------------+
int CTimeFrameManager::TimeFrameToIndex(const ENUM_TIMEFRAMES timeframe)
  {
   for(int i = 0; i < ArraySize(m_unique_tfs); i++)
     {
      if(m_unique_tfs[i] == timeframe)
         return i;
     }
   return -1;
  }

//+------------------------------------------------------------------+
//| GetTimeFramePair                                                 |
//+------------------------------------------------------------------+
S_TimeFramePair CTimeFrameManager::GetTimeFramePair(int index)
  {
   if(index < 0 || index >= ArraySize(m_tf_pairs))
     {
      S_TimeFramePair empty_pair;
      empty_pair.primary_tf = PERIOD_CURRENT;
      empty_pair.secondary_tf = PERIOD_CURRENT;
      return empty_pair;
     }
   return m_tf_pairs[index];
  }

//+------------------------------------------------------------------+
//| TotalPairs                                                       |
//+------------------------------------------------------------------+
int CTimeFrameManager::TotalPairs()
  {
   return ArraySize(m_tf_pairs);
  }

//+------------------------------------------------------------------+
//| GetSecondaryTimeFrame                                            |
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES CTimeFrameManager::GetSecondaryTimeFrame(ENUM_TIMEFRAMES primary_tf)
  {
   for(int i = 0; i < ArraySize(m_tf_pairs); i++)
     {
      if(m_tf_pairs[i].primary_tf == primary_tf)
        {
         return m_tf_pairs[i].secondary_tf;
        }
     }
   return PERIOD_CURRENT;
  }

//+------------------------------------------------------------------+
//| GetPrimaryTimeFrame                                              |
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES CTimeFrameManager::GetPrimaryTimeFrame(ENUM_TIMEFRAMES secondary_tf)
  {
   for(int i = 0; i < ArraySize(m_tf_pairs); i++)
     {
      if(m_tf_pairs[i].secondary_tf == secondary_tf)
        {
         return m_tf_pairs[i].primary_tf;
        }
     }
   return PERIOD_CURRENT;
  }

//+------------------------------------------------------------------+
//| IsPrimaryTimeFrame                                               |
//+------------------------------------------------------------------+
bool CTimeFrameManager::IsPrimaryTimeFrame(ENUM_TIMEFRAMES tf)
  {
   for(int i = 0; i < ArraySize(m_tf_pairs); i++)
     {
      if(m_tf_pairs[i].primary_tf == tf)
        {
         return true;
        }
     }
   return false;
  }

#endif // V50_TIMEFRAMEMANAGER_MQH
