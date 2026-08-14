//+------------------------------------------------------------------+
//|                                             ZonePersistence.mqh |
//|                        Copyright 2025, SIGMA Systems             |
//|                                         https://www.asksigma.com |
//+------------------------------------------------------------------+
//| V5.0.1 - Zone Persistence Module                                 |
//| Saves and loads B2B zones to survive TF changes and EA restarts  |
//+------------------------------------------------------------------+
#property strict

#ifndef V50_ZONEPERSISTENCE_MQH
#define V50_ZONEPERSISTENCE_MQH

#include "../Data/Structures.mqh"
#include "../Common/Defines.mqh"

// V5.1.2: Extern reference to display number counter (defined in Sigma_V5.0.mq5)
extern int g_next_display_number;

//+------------------------------------------------------------------+
//| CZonePersistence Class                                           |
//| Manages saving/loading of zone states to file                    |
//+------------------------------------------------------------------+
class CZonePersistence
  {
private:
   string            m_filename;           // Persistence filename
   bool              m_initialized;
   datetime          m_ea_attach_time;     // When EA was attached (for live/historical detection)
   
   // File format version for compatibility
   int               m_file_version;
   
public:
                     CZonePersistence(void);
                    ~CZonePersistence(void);
   
   //=== Initialization ===
   bool              Initialize(string symbol = "");
   datetime          GetEAAttachTime() const { return m_ea_attach_time; }
   bool              IsInitialized() const { return m_initialized; }
   
   //=== Save/Load Operations ===
   bool              SaveZones(B2BZoneInfo &zones[], int zone_count);
   int               LoadZones(B2BZoneInfo &zones[]);
   
   // V5.0.1: TF-based save/load for dynamic arrays
   bool              SaveZonesFromBuffers(B2BZoneList &zone_buffers[], int &counts[]);
   int               LoadZonesToBuffers(B2BZoneList &zone_buffers[], int &counts[]);
   
   // V5.1: Merge loaded zones with existing zones (updates touch states)
   int               MergeLoadedZones(B2BZoneInfo &zones[], int &zone_count);
   
   //=== Utility ===
   bool              FileExists();
   bool              DeleteFile();
   
private:
   //=== Internal Helpers ===
   bool              WriteZoneToFile(int handle, const B2BZoneInfo &zone);
   bool              ReadZoneFromFile(int handle, B2BZoneInfo &zone);
  };

//+------------------------------------------------------------------+
//| Constructor                                                       |
//+------------------------------------------------------------------+
CZonePersistence::CZonePersistence(void)
  {
   m_filename = "";
   m_initialized = false;
   m_ea_attach_time = 0;
   m_file_version = 11; // V11: Added g_next_display_number persistence
  }

//+------------------------------------------------------------------+
//| Destructor                                                        |
//+------------------------------------------------------------------+
CZonePersistence::~CZonePersistence(void)
  {
  }

//+------------------------------------------------------------------+
//| Initialize                                                        |
//+------------------------------------------------------------------+
bool CZonePersistence::Initialize(string symbol = "")
  {
   if(symbol == "")
      symbol = _Symbol;
   
   // Create filename based on symbol
   m_filename = "sigma_zones_" + symbol + ".bin";
   m_ea_attach_time = TimeCurrent();
   m_initialized = true;
   
   Print("[ZonePersistence] Initialized. EA attach time: ", TimeToString(m_ea_attach_time));
   Print("[ZonePersistence] Persistence file: ", m_filename);
   
   return true;
  }

//+------------------------------------------------------------------+
//| SaveZones                                                         |
//| Saves all zones to binary file                                    |
//+------------------------------------------------------------------+
bool CZonePersistence::SaveZones(B2BZoneInfo &zones[], int zone_count)
  {
   if(!m_initialized)
     {
      Print("[ZonePersistence] ERROR: Not initialized");
      return false;
     }
   
   if(zone_count == 0)
     {
      Print("[ZonePersistence] No zones to save");
      return true;
     }
   
   int handle = FileOpen(m_filename, FILE_WRITE | FILE_BIN);  // Terminal-specific folder
   if(handle == INVALID_HANDLE)
     {
      Print("[ZonePersistence] ERROR: Cannot open file for writing: ", GetLastError());
      return false;
     }
   
   // Write header
   FileWriteInteger(handle, m_file_version, INT_VALUE);  // Version
   FileWriteInteger(handle, zone_count, INT_VALUE);       // Zone count
   FileWriteLong(handle, (long)m_ea_attach_time);         // EA attach time
   FileWriteInteger(handle, g_next_display_number, INT_VALUE); // V11: Persist display counter
   
   // Write each zone
   int saved_count = 0;
   for(int i = 0; i < zone_count; i++)
     {
      if(WriteZoneToFile(handle, zones[i]))
         saved_count++;
     }
   
   FileClose(handle);
   
   PrintFormat("[ZonePersistence] Saved %d zones to file", saved_count);
   return true;
  }

//+------------------------------------------------------------------+
//| LoadZones                                                         |
//| Loads zones from binary file, returns count loaded                |
//+------------------------------------------------------------------+
int CZonePersistence::LoadZones(B2BZoneInfo &zones[])
  {
   if(!m_initialized)
     {
      Print("[ZonePersistence] ERROR: Not initialized");
      return 0;
     }
   
   if(!FileExists())
     {
      Print("[ZonePersistence] No persistence file found, starting fresh");
      return 0;
     }
   
   int handle = FileOpen(m_filename, FILE_READ | FILE_BIN);  // Terminal-specific folder
   if(handle == INVALID_HANDLE)
     {
      Print("[ZonePersistence] ERROR: Cannot open file for reading: ", GetLastError());
      return 0;
     }
   
   // Read header
   int file_version = FileReadInteger(handle, INT_VALUE);
   int zone_count = FileReadInteger(handle, INT_VALUE);
   datetime saved_ea_time = (datetime)FileReadLong(handle);
   
   // V11: Read display counter
   if(file_version >= 11)
     {
      int saved_next_display = FileReadInteger(handle, INT_VALUE);
      if(saved_next_display > g_next_display_number)
         g_next_display_number = saved_next_display;
     }
   
   if(file_version != m_file_version)
     {
      PrintFormat("[ZonePersistence] WARNING: File version mismatch (file=%d, current=%d). Starting fresh.", 
                  file_version, m_file_version);
      FileClose(handle);
      DeleteFile();
      return 0;
     }
   
   // Resize array
   ArrayResize(zones, zone_count);
   
   // Read each zone
   int loaded_count = 0;
   for(int i = 0; i < zone_count; i++)
     {
      if(ReadZoneFromFile(handle, zones[i]))
         loaded_count++;
     }
   
   FileClose(handle);
   
   PrintFormat("[ZonePersistence] Loaded %d zones from file (saved at %s)", 
               loaded_count, TimeToString(saved_ea_time));
   
   return loaded_count;
  }

//+------------------------------------------------------------------+
//| SaveZonesFromBuffers - V5.0.1 TF-based save                       |
//| Saves zones from all TF CCircularBuffer arrays to file            |
//+------------------------------------------------------------------+
bool CZonePersistence::SaveZonesFromBuffers(B2BZoneList &zone_buffers[], int &counts[])
  {
   if(!m_initialized)
     {
      Print("[ZonePersistence] ERROR: Not initialized");
      return false;
     }
   
   // Count total zones across all TFs
   int total_zones = 0;
   int buffers_count = ArraySize(zone_buffers);
   for(int tf_idx = 0; tf_idx < buffers_count; tf_idx++)
      total_zones += counts[tf_idx];
   
   if(total_zones == 0)
     {
      Print("[ZonePersistence] No zones to save");
      return true;
     }
   
   int handle = FileOpen(m_filename, FILE_WRITE | FILE_BIN);  // Terminal-specific folder
   if(handle == INVALID_HANDLE)
     {
      PrintFormat("[ZonePersistence] ERROR: Cannot create file %s", m_filename);
      return false;
     }
   
   // Write header: version, EA attach time, total zone count
   FileWriteInteger(handle, m_file_version, INT_VALUE);
   FileWriteLong(handle, (long)m_ea_attach_time);
   FileWriteInteger(handle, total_zones, INT_VALUE);
   FileWriteInteger(handle, g_next_display_number, INT_VALUE);  // V5.1.2: Counter for continuation
   
   // Write zones from each TF buffer
   int saved_count = 0;
   for(int tf_idx = 0; tf_idx < buffers_count; tf_idx++)
     {
      int tf_zone_count = counts[tf_idx];
      for(int i = 0; i < tf_zone_count; i++)
        {
         B2BZoneInfo zone = zone_buffers[tf_idx].items[i];
         WriteZoneToFile(handle, zone);
         saved_count++;
        }
     }
   
   FileClose(handle);
   
   PrintFormat("[ZonePersistence] Saved %d zones from %d TF buffers to file", 
               saved_count, ArraySize(zone_buffers));
   
   return true;
  }

//+------------------------------------------------------------------+
//| LoadZonesToBuffers - V5.0.1 TF-based load                         |
//| Loads zones from file into appropriate TF CCircularBuffer arrays  |
//+------------------------------------------------------------------+
int CZonePersistence::LoadZonesToBuffers(B2BZoneList &zone_buffers[], int &counts[])
  {
   if(!m_initialized)
     {
      Print("[ZonePersistence] ERROR: Not initialized");
      return 0;
     }
   
   if(!FileExists())
     {
      Print("[ZonePersistence] No persistence file found, starting fresh");
      return 0;
     }
   
   int handle = FileOpen(m_filename, FILE_READ | FILE_BIN);  // Terminal-specific folder
   if(handle == INVALID_HANDLE)
     {
      Print("[ZonePersistence] ERROR: Cannot open file for reading");
      return 0;
     }
   
   // Read header
   int file_version = FileReadInteger(handle, INT_VALUE);
   if(file_version != m_file_version)
     {
      PrintFormat("[ZonePersistence] Version mismatch: file=%d, expected=%d", file_version, m_file_version);
      FileClose(handle);
      return 0;
     }
   
   datetime saved_ea_time = (datetime)FileReadLong(handle);
   int zone_count = FileReadInteger(handle, INT_VALUE);
   int saved_next_display = FileReadInteger(handle, INT_VALUE);  // V5.1.2: Counter
   
   // V5.1.2: Restore the counter if it's higher than current (to ensure continuity)
   if(saved_next_display > g_next_display_number)
      g_next_display_number = saved_next_display;
   
   // Read zones and distribute to appropriate TF buffers
   int loaded_count = 0;
   for(int i = 0; i < zone_count && !FileIsEnding(handle); i++)
     {
      B2BZoneInfo zone;
      if(ReadZoneFromFile(handle, zone))
        {
         // Find the correct TF buffer for this zone
         int tf_idx = TFEnumToIndex(zone.timeframe);
         int buffers_count = ArraySize(zone_buffers);
         if(tf_idx >= 0 && tf_idx < buffers_count)
           {
            // Check if zone already exists in buffer (by zone_id)
            bool exists = false;
            int current_count = counts[tf_idx]; // ArraySize(zone_buffers[tf_idx]) should match counts[tf_idx]
            
            for(int k = 0; k < current_count && !exists; k++)
              {
               if(zone_buffers[tf_idx].items[k].zone_id == zone.zone_id)
                 {
                  // Update existing zone with loaded data
                  zone_buffers[tf_idx].items[k] = zone;
                  exists = true;
                 }
              }
            
            if(!exists)
              {
               // Add new zone to buffer using wrapper Add method or manual resize
               zone_buffers[tf_idx].Add(zone);
               counts[tf_idx]++;
              }
            
            loaded_count++;
           }
        }
     }
   
   FileClose(handle);
   
   PrintFormat("[ZonePersistence] Loaded %d zones into TF buffers (saved at %s)", 
               loaded_count, TimeToString(saved_ea_time));
   
   return loaded_count;
  }

//+------------------------------------------------------------------+
//| WriteZoneToFile                                                   |
//| Writes a single zone to binary file                               |
//+------------------------------------------------------------------+
bool CZonePersistence::WriteZoneToFile(int handle, const B2BZoneInfo &zone)
  {
   // Zone identification
   FileWriteLong(handle, (long)zone.zone_id);
   FileWriteInteger(handle, zone.display_number, INT_VALUE);  // V5.1.2: Sequential display number
   FileWriteInteger(handle, (int)zone.timeframe, INT_VALUE);
   FileWriteInteger(handle, (int)zone.direction, INT_VALUE);
   
   // Zone boundaries
   FileWriteDouble(handle, zone.L1_price);
   FileWriteDouble(handle, zone.L2_price);
   FileWriteDouble(handle, zone.fifty_percent);
   
   // Pattern components
   FileWriteDouble(handle, zone.first_barrier_price);
   FileWriteLong(handle, (long)zone.first_barrier_time);
   FileWriteDouble(handle, zone.second_barrier_price);
   FileWriteLong(handle, (long)zone.second_barrier_time);
   FileWriteDouble(handle, zone.swing_between_price);
   FileWriteLong(handle, (long)zone.swing_between_time);
   
   // Touch tracking (T1/T2/T3)
   FileWriteInteger(handle, zone.L1_touched ? 1 : 0, CHAR_VALUE);
   FileWriteInteger(handle, zone.fifty_touched ? 1 : 0, CHAR_VALUE);
   FileWriteInteger(handle, zone.L2_touched ? 1 : 0, CHAR_VALUE);
   
   // Trade signal tracking
   FileWriteInteger(handle, zone.L1_traded ? 1 : 0, CHAR_VALUE);
   FileWriteInteger(handle, zone.fifty_traded ? 1 : 0, CHAR_VALUE);
   FileWriteInteger(handle, zone.L2_traded ? 1 : 0, CHAR_VALUE);
   
   // Status
   FileWriteInteger(handle, zone.is_valid ? 1 : 0, CHAR_VALUE);
   FileWriteInteger(handle, zone.is_invalidated ? 1 : 0, CHAR_VALUE);
   FileWriteLong(handle, (long)zone.zone_created_time);
   FileWriteLong(handle, (long)zone.invalidation_time);
   
   // Parent tracking
   FileWriteInteger(handle, zone.has_narrative_parent ? 1 : 0, CHAR_VALUE);
   FileWriteInteger(handle, zone.has_control_parent ? 1 : 0, CHAR_VALUE);
   FileWriteLong(handle, (long)zone.parent_zone_id);
   FileWriteInteger(handle, (int)zone.parent_tf, INT_VALUE);
   FileWriteInteger(handle, zone.is_parent_touched ? 1 : 0, CHAR_VALUE);
   FileWriteLong(handle, (long)zone.parent_touched_time);
   FileWriteInteger(handle, zone.parent_touch_depth, INT_VALUE);
   
   // Touch times
   FileWriteLong(handle, (long)zone.L1_touch_time);
   FileWriteLong(handle, (long)zone.fifty_touch_time);
   FileWriteLong(handle, (long)zone.L2_touch_time);
   FileWriteInteger(handle, zone.touch_count, INT_VALUE);
   
   // Trade outcome
   FileWriteInteger(handle, zone.was_traded ? 1 : 0, CHAR_VALUE);
   
   // V15: Market Context & Stride Physics
   FileWriteDouble(handle, zone.atr_at_creation);
   FileWriteInteger(handle, (int)zone.narrative_direction, INT_VALUE);
   FileWriteString(handle, zone.session_created);
   FileWriteInteger(handle, zone.conflicting_zones, INT_VALUE);
   
   // Touch Bar Indices
   FileWriteInteger(handle, zone.created_bar_index, INT_VALUE);
   FileWriteInteger(handle, zone.L1_touch_bar, INT_VALUE);
   FileWriteInteger(handle, zone.fifty_touch_bar, INT_VALUE);
   FileWriteInteger(handle, zone.L2_touch_bar, INT_VALUE);
   
   return true;
  }

//+------------------------------------------------------------------+
//| ReadZoneFromFile                                                  |
//| Reads a single zone from binary file                              |
//+------------------------------------------------------------------+
bool CZonePersistence::ReadZoneFromFile(int handle, B2BZoneInfo &zone)
  {
   zone.Reset();
   
   // Zone identification
   zone.zone_id = (ulong)FileReadLong(handle);
   zone.display_number = FileReadInteger(handle, INT_VALUE);  // V5.1.2: Sequential display number
   zone.timeframe = (ENUM_TIMEFRAMES)FileReadInteger(handle, INT_VALUE);
   zone.direction = (ENUM_SIGNAL_DIRECTION)FileReadInteger(handle, INT_VALUE);
   
   // Zone boundaries
   zone.L1_price = FileReadDouble(handle);
   zone.L2_price = FileReadDouble(handle);
   zone.fifty_percent = FileReadDouble(handle);
   
   // Pattern components
   zone.first_barrier_price = FileReadDouble(handle);
   zone.first_barrier_time = (datetime)FileReadLong(handle);
   zone.second_barrier_price = FileReadDouble(handle);
   zone.second_barrier_time = (datetime)FileReadLong(handle);
   zone.swing_between_price = FileReadDouble(handle);
   zone.swing_between_time = (datetime)FileReadLong(handle);
   
   // Touch tracking
   zone.L1_touched = FileReadInteger(handle, CHAR_VALUE) == 1;
   zone.fifty_touched = FileReadInteger(handle, CHAR_VALUE) == 1;
   zone.L2_touched = FileReadInteger(handle, CHAR_VALUE) == 1;
   
   // Trade signal tracking
   zone.L1_traded = FileReadInteger(handle, CHAR_VALUE) == 1;
   zone.fifty_traded = FileReadInteger(handle, CHAR_VALUE) == 1;
   zone.L2_traded = FileReadInteger(handle, CHAR_VALUE) == 1;
   
   // Status
   zone.is_valid = FileReadInteger(handle, CHAR_VALUE) == 1;
   zone.is_invalidated = FileReadInteger(handle, CHAR_VALUE) == 1;
   zone.zone_created_time = (datetime)FileReadLong(handle);
   zone.invalidation_time = (datetime)FileReadLong(handle);
   
   // Parent tracking
   zone.has_narrative_parent = FileReadInteger(handle, CHAR_VALUE) == 1;
   zone.has_control_parent = FileReadInteger(handle, CHAR_VALUE) == 1;
   zone.parent_zone_id = (ulong)FileReadLong(handle);
   zone.parent_tf = (ENUM_TIMEFRAMES)FileReadInteger(handle, INT_VALUE);
   zone.is_parent_touched = FileReadInteger(handle, CHAR_VALUE) == 1;
   zone.parent_touched_time = (datetime)FileReadLong(handle);
   zone.parent_touch_depth = FileReadInteger(handle, INT_VALUE);
   
   // Touch times
   zone.L1_touch_time = (datetime)FileReadLong(handle);
   zone.fifty_touch_time = (datetime)FileReadLong(handle);
   zone.L2_touch_time = (datetime)FileReadLong(handle);
   zone.touch_count = FileReadInteger(handle, INT_VALUE);
   
   // Trade outcome
   zone.was_traded = FileReadInteger(handle, CHAR_VALUE) == 1;
   
   // V15: Market Context & Stride Physics
   zone.atr_at_creation = FileReadDouble(handle);
   zone.narrative_direction = (ENUM_SIGNAL_DIRECTION)FileReadInteger(handle, INT_VALUE);
   zone.session_created = FileReadString(handle);
   zone.conflicting_zones = FileReadInteger(handle, INT_VALUE);
   
   // Touch Bar Indices
   zone.created_bar_index = FileReadInteger(handle, INT_VALUE);
   zone.L1_touch_bar = FileReadInteger(handle, INT_VALUE);
   zone.fifty_touch_bar = FileReadInteger(handle, INT_VALUE);
   zone.L2_touch_bar = FileReadInteger(handle, INT_VALUE);
   
   return true;
  }

//+------------------------------------------------------------------+
//| FileExists                                                        |
//+------------------------------------------------------------------+
bool CZonePersistence::FileExists()
  {
   int handle = FileOpen(m_filename, FILE_READ | FILE_BIN);  // Terminal-specific folder
   if(handle == INVALID_HANDLE)
      return false;
   
   FileClose(handle);
   return true;
  }

//+------------------------------------------------------------------+
//| DeleteFile                                                        |
//+------------------------------------------------------------------+
bool CZonePersistence::DeleteFile()
  {
   return FileDelete(m_filename);  // V5.0.1: Delete from terminal-specific folder
  }

//+------------------------------------------------------------------+
//| MergeLoadedZones - Load and merge with existing zones             |
//| V5.1: Consolidated from B2BPersistence                            |
//+------------------------------------------------------------------+
int CZonePersistence::MergeLoadedZones(B2BZoneInfo &zones[], int &zone_count)
  {
   if(!m_initialized)
     {
      Initialize(_Symbol);
     }
   
   B2BZoneInfo loaded_zones[];
   int loaded_count = LoadZones(loaded_zones);
   
   if(loaded_count == 0)
      return 0;
   
   int merged_count = 0;
   int updated_count = 0;
   int added_count = 0;
   int original_count = zone_count;
   
   bool matched[];
   ArrayResize(matched, original_count);
   ArrayInitialize(matched, false);
   
   for(int i = 0; i < loaded_count; i++)
     {
      int existing_idx = -1;
      
      for(int j = 0; j < original_count; j++)
        {
         if(matched[j])
            continue;
         
         if(zones[j].zone_id == loaded_zones[i].zone_id)
           {
            existing_idx = j;
            break;
           }
        }
      
      if(existing_idx >= 0)
        {
         matched[existing_idx] = true;
         
         // Preserve touch states from loaded zones
         zones[existing_idx].L1_touched = loaded_zones[i].L1_touched;
         zones[existing_idx].fifty_touched = loaded_zones[i].fifty_touched;
         zones[existing_idx].L2_touched = loaded_zones[i].L2_touched;
         zones[existing_idx].L1_traded = loaded_zones[i].L1_traded;
         zones[existing_idx].fifty_traded = loaded_zones[i].fifty_traded;
         zones[existing_idx].L2_traded = loaded_zones[i].L2_traded;
         zones[existing_idx].L1_touch_time = loaded_zones[i].L1_touch_time;
         zones[existing_idx].fifty_touch_time = loaded_zones[i].fifty_touch_time;
         zones[existing_idx].L2_touch_time = loaded_zones[i].L2_touch_time;
         zones[existing_idx].touch_count = loaded_zones[i].touch_count;
         zones[existing_idx].was_traded = loaded_zones[i].was_traded;
         zones[existing_idx].is_parent_touched = loaded_zones[i].is_parent_touched;
         zones[existing_idx].parent_touched_time = loaded_zones[i].parent_touched_time;
         zones[existing_idx].parent_touch_depth = loaded_zones[i].parent_touch_depth;
         updated_count++;
        }
      else
        {
         // Add new zones that weren't in current session
         if(loaded_zones[i].is_valid && !loaded_zones[i].is_invalidated)
           {
            ArrayResize(zones, zone_count + 1);
            zones[zone_count] = loaded_zones[i];
            zone_count++;
            added_count++;
           }
        }
      
      merged_count++;
     }
   
   PrintFormat("[ZonePersistence] Merged %d zones (updated=%d, added=%d)", 
               merged_count, updated_count, added_count);
   
   return merged_count;
  }

#endif // V50_ZONEPERSISTENCE_MQH
