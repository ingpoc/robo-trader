# Celery Tasks for Robo Trader Job Queue
# Distributed background job processing

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from celery import Celery
from celery.schedules import crontab
import redis
import aiohttp

# Create Celery app
app = Celery('robo_trader')
app.config_from_object('celeryconfig')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis client for caching
redis_client = redis.Redis(host='redis-cache', port=6379, db=0, decode_responses=True)


# Portfolio Tasks
@app.task(name='tasks.portfolio_tasks.calculate_pnl', queue='portfolio')
def calculate_portfolio_pnl(portfolio_id: str, as_of: str = None) -> Dict[str, Any]:
    """Calculate portfolio P&L for given date."""
    try:
        logger.info(f"Calculating P&L for portfolio {portfolio_id}")

        # Call portfolio service
        result = asyncio.run(_call_service('portfolio-service', '8001', f'/calculate-pnl/{portfolio_id}'))

        # Cache result
        cache_key = f"portfolio:pnl:{portfolio_id}:{as_of or 'latest'}"
        redis_client.setex(cache_key, 300, json.dumps(result))  # Cache for 5 minutes

        return result
    except Exception as e:
        logger.error(f"Failed to calculate P&L: {e}")
        raise


@app.task(name='tasks.portfolio_tasks.check_rebalancing', queue='portfolio')
def check_portfolio_rebalancing() -> Dict[str, Any]:
    """Check if portfolio needs rebalancing."""
    try:
        logger.info("Checking portfolio rebalancing needs")

        # Call portfolio service
        result = asyncio.run(_call_service('portfolio-service', '8001', '/check-rebalancing'))

        return result
    except Exception as e:
        logger.error(f"Failed to check rebalancing: {e}")
        raise


# Risk Management Tasks
@app.task(name='tasks.risk_tasks.monitor_limits', queue='risk')
def monitor_risk_limits() -> Dict[str, Any]:
    """Monitor risk limits and send alerts if breached."""
    try:
        logger.info("Monitoring risk limits")

        # Call risk service
        result = asyncio.run(_call_service('risk-service', '8002', '/monitor-limits'))

        # Check for breaches and send alerts
        breaches = result.get('breaches', [])
        if breaches:
            asyncio.run(_send_alerts(breaches))

        return result
    except Exception as e:
        logger.error(f"Failed to monitor risk limits: {e}")
        raise


@app.task(name='tasks.risk_tasks.update_stop_losses', queue='risk')
def update_stop_losses(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update stop loss orders based on market data."""
    try:
        logger.info("Updating stop loss orders")

        # Call risk service with market data
        result = asyncio.run(_call_service('risk-service', '8002', '/update-stop-losses',
                                         method='POST', data=market_data))

        return result
    except Exception as e:
        logger.error(f"Failed to update stop losses: {e}")
        raise


# Analytics Tasks
@app.task(name='tasks.analytics_tasks.screen_stocks', queue='analytics')
def screen_stocks(criteria: Dict[str, Any]) -> Dict[str, Any]:
    """Screen stocks based on given criteria."""
    try:
        logger.info(f"Screening stocks with criteria: {criteria}")

        # Call analytics service
        result = asyncio.run(_call_service('analytics-service', '8004', '/screen-stocks',
                                         method='POST', data=criteria))

        # Cache results
        cache_key = f"analytics:screening:{hash(json.dumps(criteria, sort_keys=True))}"
        redis_client.setex(cache_key, 1800, json.dumps(result))  # Cache for 30 minutes

        return result
    except Exception as e:
        logger.error(f"Failed to screen stocks: {e}")
        raise


@app.task(name='tasks.analytics_tasks.calculate_indicators', queue='analytics')
def calculate_technical_indicators(symbol: str, timeframe: str = '1D') -> Dict[str, Any]:
    """Calculate technical indicators for a symbol."""
    try:
        logger.info(f"Calculating indicators for {symbol} on {timeframe}")

        # Call analytics service
        result = asyncio.run(_call_service('analytics-service', '8004',
                                         f'/indicators/{symbol}?timeframe={timeframe}'))

        # Cache results
        cache_key = f"analytics:indicators:{symbol}:{timeframe}"
        redis_client.setex(cache_key, 600, json.dumps(result))  # Cache for 10 minutes

        return result
    except Exception as e:
        logger.error(f"Failed to calculate indicators: {e}")
        raise


# Market Data Tasks
@app.task(name='tasks.market_data_tasks.sync_market_data', queue='market_data')
def sync_market_data() -> Dict[str, Any]:
    """Sync latest market data from external sources."""
    try:
        logger.info("Syncing market data")

        # This would typically call external APIs
        # For now, simulate the sync
        result = {
            'status': 'success',
            'symbols_updated': 100,
            'last_sync': datetime.now(timezone.utc).isoformat()
        }

        # Publish market data update event
        asyncio.run(_publish_event('market.price_update', {
            'source': 'sync_job',
            'timestamp': result['last_sync']
        }))

        return result
    except Exception as e:
        logger.error(f"Failed to sync market data: {e}")
        raise


@app.task(name='tasks.market_data_tasks.process_price_alerts', queue='critical')
def process_price_alerts(price_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process price alerts and trigger notifications."""
    try:
        logger.info("Processing price alerts")

        # Check cached alert rules
        alert_rules = redis_client.get('alert_rules')
        if alert_rules:
            rules = json.loads(alert_rules)
            triggered_alerts = []

            for rule in rules:
                if _check_alert_condition(rule, price_data):
                    triggered_alerts.append(rule)

            if triggered_alerts:
                # Send notifications
                asyncio.run(_send_notifications(triggered_alerts))

        return {'alerts_processed': len(triggered_alerts) if 'triggered_alerts' in locals() else 0}
    except Exception as e:
        logger.error(f"Failed to process price alerts: {e}")
        raise


# Learning Tasks
@app.task(name='tasks.learning_tasks.update_patterns', queue='analytics')
def update_learning_patterns(new_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update learning patterns with new market data."""
    try:
        logger.info("Updating learning patterns")

        # Call learning service
        result = asyncio.run(_call_service('learning-service', '8005', '/update-patterns',
                                         method='POST', data=new_data))

        return result
    except Exception as e:
        logger.error(f"Failed to update learning patterns: {e}")
        raise


# Helper functions
async def _call_service(service_name: str, port: str, endpoint: str,
                       method: str = 'GET', data: Dict = None) -> Dict[str, Any]:
    """Call a service endpoint."""
    url = f"http://{service_name}:{port}{endpoint}"

    async with aiohttp.ClientSession() as session:
        if method == 'GET':
            async with session.get(url) as response:
                return await response.json()
        elif method == 'POST':
            async with session.post(url, json=data) as response:
                return await response.json()


async def _publish_event(event_type: str, data: Dict[str, Any]) -> None:
    """Publish event to event bus."""
    event_data = {
        'id': f"job_{datetime.now(timezone.utc).timestamp()}",
        'type': event_type,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'source': 'job-queue-service',
        'data': data
    }

    await _call_service('event-bus', '8000', '/publish',
                       method='POST', data=event_data)


async def _send_alerts(alerts: List[Dict[str, Any]]) -> None:
    """Send risk alerts."""
    for alert in alerts:
        await _call_service('safety-layer', '8006', '/send-alert',
                           method='POST', data=alert)


async def _send_notifications(notifications: List[Dict[str, Any]]) -> None:
    """Send notifications."""
    for notification in notifications:
        await _call_service('safety-layer', '8006', '/send-notification',
                           method='POST', data=notification)


def _check_alert_condition(rule: Dict[str, Any], price_data: Dict[str, Any]) -> bool:
    """Check if alert condition is met."""
    # Simple price alert logic
    symbol = rule.get('symbol')
    threshold = rule.get('threshold')
    condition = rule.get('condition', 'above')

    if symbol in price_data:
        current_price = price_data[symbol]
        if condition == 'above' and current_price > threshold:
            return True
        elif condition == 'below' and current_price < threshold:
            return True

    return False


if __name__ == '__main__':
    app.start()