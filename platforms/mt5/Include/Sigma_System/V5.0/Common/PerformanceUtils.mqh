//+------------------------------------------------------------------+
//|                                             PerformanceUtils.mqh |
//|                             Copyright 2025, Sigma Trading System |
//+------------------------------------------------------------------+
//| V5.0 CLEAN SLATE - B2B ONLY                                      |
//| Performance optimization: caching, batch processing, monitoring  |
//+------------------------------------------------------------------+
#ifndef V50_PERFORMANCEUTILS_MQH
#define V50_PERFORMANCEUTILS_MQH

#property strict

#include "../Common/Defines.mqh"
#include "../Data/Structures.mqh"

//+------------------------------------------------------------------+
//| Swing State Cache for O(1) Lookups                              |
//+------------------------------------------------------------------+
struct SwingStateCache
  {
   datetime          swing_times[100];
   int               swing_indices[100];
   ENUM_SWING_TYPE   swing_types[100];
   datetime          last_update_time;
   bool              is_dirty;
   int               cache_count;
   
   void Initialize()
     {
      ArrayInitialize(swing_times, 0);
      ArrayInitialize(swing_indices, -1);
      ArrayInitialize(swing_types, (ENUM_SWING_TYPE)SWING_NONE);
      last_update_time = 0;
      is_dirty = true;
      cache_count = 0;
     }
   
   int FindSwingIndex(datetime time, ENUM_SWING_TYPE type)
     {
      for(int i = 0; i < cache_count; i++)
        {
         if(swing_times[i] == time && swing_types[i] == type)
            return swing_indices[i];
        }
      return -1;
     }
   
   void AddToCache(datetime time, int buffer_index, ENUM_SWING_TYPE type)
     {
      if(cache_count < 100)
        {
         swing_times[cache_count] = time;
         swing_indices[cache_count] = buffer_index;
         swing_types[cache_count] = type;
         cache_count++;
        }
     }
   
   void MarkDirty()
     {
      is_dirty = true;
     }
   
   void Clear()
     {
      cache_count = 0;
      is_dirty = true;
     }
  };

//+------------------------------------------------------------------+
//| Batch Processing Utilities                                       |
//+------------------------------------------------------------------+
struct BatchProcessor
  {
   datetime          broken_swing_times[50];
   ENUM_SWING_TYPE   broken_swing_types[50];
   int               broken_count;
   
   void Initialize()
     {
      ArrayInitialize(broken_swing_times, 0);
      ArrayInitialize(broken_swing_types, (ENUM_SWING_TYPE)SWING_NONE);
      broken_count = 0;
     }
   
   void AddBrokenSwing(datetime time, ENUM_SWING_TYPE type)
     {
      if(broken_count < 50)
        {
         broken_swing_times[broken_count] = time;
         broken_swing_types[broken_count] = type;
         broken_count++;
        }
     }
   
   bool IsSwingBroken(datetime time, ENUM_SWING_TYPE type)
     {
      for(int i = 0; i < broken_count; i++)
        {
         if(broken_swing_times[i] == time && broken_swing_types[i] == type)
            return true;
        }
      return false;
     }
   
   void Clear()
     {
      broken_count = 0;
     }
  };

//+------------------------------------------------------------------+
//| Performance Monitor                                              |
//+------------------------------------------------------------------+
struct PerformanceMonitor
  {
   ulong             operation_count;
   ulong             start_time;
   ulong             total_time;
   
   void StartTiming()
     {
      start_time = GetMicrosecondCount();
     }
   
   void EndTiming()
     {
      if(start_time > 0)
        {
         total_time += GetMicrosecondCount() - start_time;
         operation_count++;
         start_time = 0;
        }
     }
   
   double GetAverageTime()
     {
      if(operation_count > 0)
         return (double)total_time / (double)operation_count;
      return 0.0;
     }
   
   void Reset()
     {
      operation_count = 0;
      total_time = 0;
      start_time = 0;
     }
  };

//+------------------------------------------------------------------+
//| Global Performance Objects                                       |
//+------------------------------------------------------------------+
SwingStateCache g_swing_cache[TOTAL_TIMEFRAMES];
BatchProcessor g_batch_processor;
PerformanceMonitor g_perf_monitor;

//+------------------------------------------------------------------+
//| Initialize all performance utilities                             |
//+------------------------------------------------------------------+
void InitializePerformanceUtils()
  {
   for(int i = 0; i < TOTAL_TIMEFRAMES; i++)
     {
      g_swing_cache[i].Initialize();
     }
   
   g_batch_processor.Initialize();
   g_perf_monitor.Reset();
  }

//+------------------------------------------------------------------+
//| Check if cache needs rebuilding                                  |
//+------------------------------------------------------------------+
bool ShouldRebuildCache(int tf_index)
  {
   if(tf_index < 0 || tf_index >= TOTAL_TIMEFRAMES)
      return false;
      
   return g_swing_cache[tf_index].is_dirty || 
          (TimeCurrent() - g_swing_cache[tf_index].last_update_time) > 300;
  }

#endif // V50_PERFORMANCEUTILS_MQH
