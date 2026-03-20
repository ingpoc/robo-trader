# Robo Trader - Project Overview

## Purpose
Claude-powered autonomous paper trading system that brings AI intelligence to retail trading.

## Vision
Transform trading from manual analysis to collaborative intelligence where Claude AI acts as expert trading partner:
- Monthly AI analysis of user's real portfolio for keep/sell recommendations
- Fully autonomous paper trading with ₹1L to test if Claude can be trusted with real money
- Claude handles all research, trading, and strategy evolution

## Key Features
- Multi-Agent Architecture (Portfolio Analyzer, Technical Analyst, Risk Manager, etc.)
- Claude Agent SDK integration (no direct API calls)
- Coordinator-based monolithic architecture
- Event-driven communication via EventBus
- Three-queue system: PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS
- Safety-first with multi-layer guardrails
- Modern React/TypeScript web UI with WebSocket

## Current Status
Production Ready (90% complete)
- Core architecture complete
- Advanced services complete
- AI & intelligence complete
- Final polish remaining (10%)
