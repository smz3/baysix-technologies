//+------------------------------------------------------------------+
//|                                               CircularBuffer.mqh |
//|                        Copyright 2025, SIGMA Systems Engineering |
//|                                        sigmatrading.ai@gmail.com |
//+------------------------------------------------------------------+
//| V5.0 CLEAN SLATE - B2B ONLY                                      |
//| Generic circular buffer for swing points and breakouts           |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, SIGMA Systems Engineering"
#property link      "sigmatrading.ai@gmail.com"
#property version   "5.00"
#property strict

//+------------------------------------------------------------------+
//| CCircularBuffer Class                                            |
//| A template-based, fixed-size circular buffer for storing any     |
//| data type. Automatically overwrites the oldest element when full.|
//+------------------------------------------------------------------+
template<typename T>
class CCircularBuffer
  {
private:
   T                 m_buffer[];         // The internal array holding the data
   int               m_max_size;         // The maximum number of elements
   int               m_head_index;       // Pointer to the last added element
   bool              m_is_full;          // Flag indicating if buffer has wrapped

   //--- Converts a public index (0=oldest) to a private array index
   int               ToRealIndex(int public_index) const
     {
      if(public_index < 0 || public_index >= Count())
        {
         return -1;
        }

      if(!m_is_full)
        {
         return public_index;
        }

      // Full: 0 maps to (Head + 1) % MaxSize (FIFO/Chronological behavior)
      int oldest_index = (m_head_index + 1) % m_max_size;
      int real_index = (oldest_index + public_index) % m_max_size;
      return real_index;
     }

public:
   //--- Constructor
                     CCircularBuffer(void)
     {
      m_max_size = 0;
      m_head_index = -1;
      m_is_full = false;
     }

   //--- Initializes the buffer with a specific size
   void              Initialize(int size)
     {
      if(size <= 0) return;
      m_max_size = size;
      ArrayResize(m_buffer, m_max_size);
      Clear();
     }

   //--- Clears the buffer
   void Clear(void)
     {
      m_head_index = -1;
      m_is_full = false;
     }

   //--- Adds a new element to the buffer
   void              Add(const T &value)
     {
      if(m_max_size == 0) return;

      if(m_head_index + 1 >= m_max_size)
        {
         m_head_index = 0;
         m_is_full = true;
        }
      else
        {
         m_head_index++;
        }

      m_buffer[m_head_index] = value;
     }

   //--- Gets an element by its public index (0 is the oldest)
   T                 Get(int public_index) const
     {
      int real_index = ToRealIndex(public_index);
      if(real_index != -1)
        {
         return m_buffer[real_index];
        }
      T empty_value;
      return empty_value;
     }

   //--- Updates an element at a specific public index
   void Update(int public_index, const T &value)
     {
      int real_index = ToRealIndex(public_index);
      if(real_index != -1)
        {
         m_buffer[real_index] = value;
        }
     }

   //--- Returns the current number of elements in the buffer
   int               Count(void) const
     {
      if(m_is_full)
        {
         return m_max_size;
        }
      return m_head_index + 1;
     }

   //--- Returns the maximum size (capacity) of the buffer
   int               Capacity(void)
     {
      return m_max_size;
     }

   //--- Batch update multiple elements
   void BatchUpdate(int &public_indices[], T &values[], int count)
     {
      for(int i = 0; i < count; i++)
        {
         Update(public_indices[i], values[i]);
        }
     }
  };
