"""Minimal Kite Connect Service for Portfolio Fetching

Essential service to fetch real portfolio from Zerodha Kite Connect.
Stripped down to only portfolio import functionality.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


class KitePortfolioService:
    """Minimal Kite Connect service for fetching portfolio data."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize with Kite Connect credentials."""
        self.config = config or {}
        self.api_key = self.config.get('api_key') or os.getenv('ZERODHA_API_KEY')
        self.api_secret = self.config.get('api_secret') or os.getenv('ZERODHA_API_SECRET')
        self.access_token = self.config.get('access_token') or os.getenv('ZERODHA_ACCESS_TOKEN')
        self.request_token = self.config.get('request_token') or os.getenv('ZERODHA_REQUEST_TOKEN')

        self.base_url = "https://api.kite.trade"
        self.session = None

    async def initialize(self):
        """Initialize HTTP session."""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def cleanup(self):
        """Cleanup HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def get_access_token(self, request_token: str = None) -> Optional[str]:
        """Get access token from request token."""
        if not request_token:
            request_token = self.request_token

        if not request_token or not self.api_key or not self.api_secret:
            logger.error("Missing required credentials for access token")
            return None

        try:
            checksum = f"{self.api_key}{request_token}{self.api_secret}"

            async with self.session.post(
                f"{self.base_url}/session/token",
                data={
                    "api_key": self.api_key,
                    "request_token": request_token,
                    "checksum": checksum
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data.get('data', {}).get('access_token')
                    return self.access_token
                else:
                    logger.error(f"Failed to get access token: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None

    async def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make authenticated request to Kite API."""
        if not self.access_token:
            if not await self.get_access_token():
                return None

        headers = {
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "X-Kite-Version": "3"
        }

        try:
            async with self.session.get(
                f"{self.base_url}{endpoint}",
                headers=headers,
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 403:
                    logger.error("Access token expired, attempting refresh")
                    self.access_token = None
                    return None
                else:
                    logger.error(f"API request failed: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error making request: {e}")
            return None

    async def get_portfolio_holdings(self) -> List[Dict]:
        """Get current portfolio holdings."""
        if not self.session:
            await self.initialize()

        data = await self._make_request("/portfolio/holdings")
        if data and data.get('status') == 'success':
            return data.get('data', [])
        return []

    async def get_portfolio_positions(self) -> Dict:
        """Get current portfolio positions."""
        if not self.session:
            await self.initialize()

        data = await self._make_request("/portfolio/positions")
        if data and data.get('status') == 'success':
            return data.get('data', {})
        return {}

    async def get_portfolio_holdings_and_positions(self) -> Dict[str, Any]:
        """Get complete portfolio data (holdings + positions)."""
        try:
            holdings = await self.get_portfolio_holdings()
            positions = await self.get_portfolio_positions()

            return {
                'holdings': holdings,
                'positions': positions,
                'total_holdings': len(holdings),
                'total_positions': len(positions.get('net', [])),
                'last_updated': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching portfolio data: {e}")
            return {
                'holdings': [],
                'positions': {},
                'error': str(e),
                'last_updated': datetime.utcnow().isoformat()
            }

    async def import_portfolio_to_paper_trading(self, portfolio_id: int) -> Dict[str, Any]:
        """Import real Kite portfolio into paper trading."""
        try:
            portfolio_data = await self.get_portfolio_holdings_and_positions()

            if portfolio_data.get('error'):
                return {
                    'success': False,
                    'message': f"Failed to fetch Kite portfolio: {portfolio_data['error']}"
                }

            # Process holdings for paper trading
            imported_holdings = []
            for holding in portfolio_data.get('holdings', []):
                imported_holdings.append({
                    'symbol': holding.get('tradingsymbol'),
                    'quantity': holding.get('quantity'),
                    'average_price': holding.get('average_price'),
                    'last_price': holding.get('last_price'),
                    'pnl': holding.get('pnl'),
                    'pnl_percentage': holding.get('pnl_percentage')
                })

            # Process positions
            imported_positions = []
            for position in portfolio_data.get('positions', {}).get('net', []):
                if position.get('quantity') != 0:  # Only include non-zero positions
                    imported_positions.append({
                        'symbol': position.get('tradingsymbol'),
                        'quantity': position.get('quantity'),
                        'average_price': position.get('average_price'),
                        'last_price': position.get('last_price'),
                        'pnl': position.get('pnl'),
                        'product': position.get('product')
                    })

            return {
                'success': True,
                'portfolio_id': portfolio_id,
                'imported_holdings': imported_holdings,
                'imported_positions': imported_positions,
                'summary': {
                    'total_holdings': len(imported_holdings),
                    'total_positions': len(imported_positions),
                    'import_date': datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error importing portfolio: {e}")
            return {
                'success': False,
                'message': f"Import failed: {str(e)}"
            }