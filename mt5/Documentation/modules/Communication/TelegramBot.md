# TelegramBot.mqh

## Purpose
Placeholder stub for future Telegram notification integration. All methods exist in the interface but contain no implementation — they are no-ops. The file was scaffolded in V5.0 to reserve the architectural slot so future Telegram logic can be added without touching any other module.

## Layer
Communication

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CTelegramBot` | Class | Empty Telegram notification interface |
| `Initialize()` | Method | Setup (no-op — returns true) |
| `SendMessage(text)` | Method | Send text message (no-op) |
| `SendTradeAlert(zone, signal)` | Method | Send trade alert with zone details (no-op) |

## Inputs / Outputs
- All methods accept parameters but do nothing with them
- All return `true` (success) by convention so callers don't need conditional logic when Telegram is added later

## Dependencies
None.

## Python Equivalent
No equivalent in sigma-crypto. Telegram notifications in the Python stack would use the `python-telegram-bot` library or a webhook. The sigma-quant dashboard handles real-time visualization instead.

## Notes
- **Status: Placeholder** — do not build Telegram logic here until the bot token, chat ID, and notification policy are decided
- When implementing, use MT5's `WebRequest()` function (requires enabling URL whitelist in MT5 Options → Expert Advisors → Allow WebRequest)
- Suggested future alerts: trade opened, trade closed (with P&L), zone invalidated, daily loss limit hit
- Adding real implementation here requires no changes to any other module — `OrderManager` and `TrailingStopManager` already call `SendTradeAlert()` and `SendMessage()` respectively
