"""
Technical Indicators Service

Calculates technical indicators (RSI, MACD, Bollinger Bands, EMA, ATR) from historical OHLC data.
Uses real market data from Kite Connect.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from loguru import logger

from src.config import Config
from ..core.errors import TradingError, ErrorCategory, ErrorSeverity


class TechnicalIndicatorsService:
    """Service for calculating technical indicators from historical OHLC data."""

    def __init__(self, config: Config):
        self.config = config

    def calculate_rsi(self, closes: pd.Series, period: int = 14) -> float:
        """
        Calculate Relative Strength Index (RSI).

        Args:
            closes: Series of closing prices
            period: RSI period (default: 14)

        Returns:
            RSI value (0-100)
        """
        if len(closes) < period + 1:
            raise ValueError(f"Need at least {period + 1} data points for RSI calculation")

        delta = closes.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi.iloc[-1])

    def calculate_macd(
        self,
        closes: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, float]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        Args:
            closes: Series of closing prices
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line period (default: 9)

        Returns:
            Dict with 'macd', 'signal', and 'histogram' values
        """
        if len(closes) < slow_period + signal_period:
            raise ValueError(f"Need at least {slow_period + signal_period} data points for MACD")

        ema_fast = closes.ewm(span=fast_period, adjust=False).mean()
        ema_slow = closes.ewm(span=slow_period, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            "macd": float(macd_line.iloc[-1]),
            "signal": float(signal_line.iloc[-1]),
            "histogram": float(histogram.iloc[-1])
        }

    def calculate_bollinger_bands(
        self,
        closes: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, float]:
        """
        Calculate Bollinger Bands.

        Args:
            closes: Series of closing prices
            period: Moving average period (default: 20)
            std_dev: Standard deviation multiplier (default: 2.0)

        Returns:
            Dict with 'upper', 'middle', and 'lower' band values
        """
        if len(closes) < period:
            raise ValueError(f"Need at least {period} data points for Bollinger Bands")

        sma = closes.rolling(window=period).mean()
        std = closes.rolling(window=period).std()

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        return {
            "upper": float(upper_band.iloc[-1]),
            "middle": float(sma.iloc[-1]),
            "lower": float(lower_band.iloc[-1])
        }

    def calculate_ema(self, closes: pd.Series, period: int) -> float:
        """
        Calculate Exponential Moving Average (EMA).

        Args:
            closes: Series of closing prices
            period: EMA period

        Returns:
            EMA value
        """
        if len(closes) < period:
            raise ValueError(f"Need at least {period} data points for EMA")

        ema = closes.ewm(span=period, adjust=False).mean()
        return float(ema.iloc[-1])

    def calculate_atr(
        self,
        highs: pd.Series,
        lows: pd.Series,
        closes: pd.Series,
        period: int = 14
    ) -> float:
        """
        Calculate Average True Range (ATR).

        Args:
            highs: Series of high prices
            lows: Series of low prices
            closes: Series of closing prices
            period: ATR period (default: 14)

        Returns:
            ATR value
        """
        if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
            raise ValueError(f"Need at least {period + 1} data points for ATR")

        # Calculate True Range
        tr1 = highs - lows
        tr2 = abs(highs - closes.shift())
        tr3 = abs(lows - closes.shift())

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Calculate ATR as moving average of True Range
        atr = true_range.rolling(window=period).mean()

        return float(atr.iloc[-1])

    def calculate_all_indicators(
        self,
        historical_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate all technical indicators from historical OHLC data.

        Args:
            historical_data: List of OHLC dictionaries with keys: date, open, high, low, close, volume

        Returns:
            Dict with all calculated indicators
        """
        if not historical_data or len(historical_data) < 30:
            raise ValueError("Need at least 30 data points for indicator calculations")

        # Convert to DataFrame
        df = pd.DataFrame(historical_data)
        df['date'] = pd.to_datetime(df['date'])

        # Ensure columns exist
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # Sort by date
        df = df.sort_values('date')

        # Extract series
        closes = df['close']
        highs = df['high']
        lows = df['low']
        opens = df['open']

        indicators = {}

        try:
            # RSI (14 period)
            indicators['rsi'] = self.calculate_rsi(closes, period=14)
        except Exception as e:
            logger.warning(f"Failed to calculate RSI: {e}")
            indicators['rsi'] = None

        try:
            # MACD
            macd_result = self.calculate_macd(closes)
            indicators['macd'] = macd_result['macd']
            indicators['macd_signal'] = macd_result['signal']
            indicators['macd_histogram'] = macd_result['histogram']
        except Exception as e:
            logger.warning(f"Failed to calculate MACD: {e}")
            indicators['macd'] = None
            indicators['macd_signal'] = None
            indicators['macd_histogram'] = None

        try:
            # Bollinger Bands
            bb_result = self.calculate_bollinger_bands(closes)
            indicators['bollinger_upper'] = bb_result['upper']
            indicators['bollinger_middle'] = bb_result['middle']
            indicators['bollinger_lower'] = bb_result['lower']
        except Exception as e:
            logger.warning(f"Failed to calculate Bollinger Bands: {e}")
            indicators['bollinger_upper'] = None
            indicators['bollinger_middle'] = None
            indicators['bollinger_lower'] = None

        try:
            # EMA 9 and 21
            indicators['ema_9'] = self.calculate_ema(closes, period=9)
            indicators['ema_21'] = self.calculate_ema(closes, period=21)
        except Exception as e:
            logger.warning(f"Failed to calculate EMA: {e}")
            indicators['ema_9'] = None
            indicators['ema_21'] = None

        try:
            # ATR
            indicators['atr'] = self.calculate_atr(highs, lows, closes, period=14)
        except Exception as e:
            logger.warning(f"Failed to calculate ATR: {e}")
            indicators['atr'] = None

        # Add current price
        indicators['current_price'] = float(closes.iloc[-1])

        return indicators

