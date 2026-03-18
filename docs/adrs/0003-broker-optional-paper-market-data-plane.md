# ADR 0003: Broker-Optional Paper Market Data Plane

## Status

Accepted

## Context

Robo Trader is paper-trading-first. The active product needs live mark-to-market updates for open paper positions, but it should not force a paid broker market-data plan just to remain useful.

The previous runtime treated paper-mode market data as equivalent to Zerodha/Kite broker auth. That created the wrong dependency chain:

- paper trading was blocked when Zerodha auth was unavailable
- `market_data` capability implicitly meant `broker-backed quotes`
- the UI implied the broker was required just to see live paper P&L

This no longer fits the mission. Paper trading must stay useful without broker execution being enabled.

## Decision

Adopt a three-plane split:

- `QuoteStreamAdapter` provides live prices for paper-mode mark-to-market
- `BrokerAdapter` remains separate for future broker-backed execution and reconciliation
- `ResearchDataProvider` remains separate for discovery, earnings, and fundamental context

Default paper-mode quote streaming uses `Upstox Market Data Feed V3`.
Future broker execution remains separate and can continue to target Zerodha.

## Consequences

### Positive

- Paper-mode live P&L no longer depends on Zerodha Connect.
- Broker auth becomes optional in paper mode.
- Capability reporting can distinguish:
  - quote stream readiness
  - market data freshness
  - broker execution readiness
- The operator UI can truthfully show live paper marks even when the future broker is unauthenticated.

### Negative

- Quote provider and future execution broker are now different systems.
- Symbol normalization and instrument-key resolution become explicit application responsibilities.
- Runtime configuration must keep provider status, quote freshness, and broker readiness distinct.

## Implementation Notes

- `MarketDataService` owns subscriptions, cache freshness, and mark propagation.
- `UpstoxQuoteStreamAdapter` uses the official `upstox-python-sdk` `MarketDataStreamerV3`.
- Symbol-to-instrument-key resolution uses the official Upstox NSE BOD JSON instruments file.
- Claude Agent SDK remains event-driven and does not consume tick streams directly.
