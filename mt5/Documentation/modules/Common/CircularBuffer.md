# CircularBuffer.mqh

## Purpose
A generic, fixed-size circular (ring) buffer template. When the buffer is full, adding a new element automatically overwrites the oldest one. Used to store swing points and raw breakouts per timeframe with a guaranteed memory ceiling — no unbounded array growth even in long backtests.

## Layer
Common

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CCircularBuffer<T>` | Template Class | Fixed-size FIFO ring buffer for any type T |
| `Initialize(int size)` | Method | Allocate internal array of `size` elements |
| `Add(const T &value)` | Method | Append element; overwrites oldest if full |
| `Get(int public_index)` | Method | Read element by public index (0 = oldest) |
| `Count()` | Method | Current number of stored elements |
| `Clear()` | Method | Reset buffer to empty state |

## Inputs / Outputs
- **Generic type `T`**: Used with `SwingPointInfo` and `RawBreakoutInfo` structs
- **`Add`**: No return value; modifies internal state
- **`Get`**: Returns element at public index; index 0 = oldest (chronological order)

## Dependencies
None — pure generic data structure with no project-specific includes.

## Python Equivalent
`collections.deque(maxlen=N)` in Python. In sigma-crypto, swing points and breakouts are stored in pandas DataFrames or plain Python lists with manual pruning; there is no explicit circular buffer class.

## Notes
- **Index semantics**: Public index 0 is the oldest element (FIFO/chronological). This is intentional — detection algorithms scan from oldest to newest.
- **Template instantiation**: The EA uses `CCircularBuffer<SwingPointInfo>` and `CCircularBuffer<RawBreakoutInfo>` — one per timeframe per detector.
- **Memory**: Buffer size is set at `Initialize()` time and does not change. Over-allocation wastes memory; under-allocation drops old data silently.
