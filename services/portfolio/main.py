"""
Portfolio Service
Manages portfolio holdings, transactions, and P&L calculations
Emits portfolio change events to RabbitMQ
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services.shared import EventBus, Event, EventType
from services.shared.database import (
    check_db_health,
    close_db_pool,
    execute_query,
    execute_update,
    get_db_pool,
)
from services.shared.models import HealthCheck

# ============================================================================
# CONFIGURATION
# ============================================================================

logger = logging.getLogger(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "portfolio")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8001))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/robo_trader")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost//")

# ============================================================================
# MODELS
# ============================================================================


class Holding(BaseModel):
    """Portfolio holding"""

    symbol: str
    quantity: int
    avg_price: float
    current_value: float
    pnl: float
    pnl_percentage: float


class Transaction(BaseModel):
    """Transaction"""

    symbol: str
    quantity: int
    price: float
    transaction_type: str  # BUY or SELL
    order_id: Optional[str] = None


class PortfolioSnapshot(BaseModel):
    """Portfolio snapshot"""

    snapshot_date: str
    total_value: float
    cash_balance: float
    invested_amount: float
    pnl: float
    pnl_percentage: float


# ============================================================================
# GLOBAL STATE
# ============================================================================

event_bus: EventBus = None
db_pool = None


# ============================================================================
# FASTAPI APP
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifecycle management"""
    # Startup
    global event_bus, db_pool

    logger.info(f"🚀 Starting {SERVICE_NAME} service...")

    try:
        # Initialize database pool
        db_pool = await get_db_pool(DATABASE_URL)

        # Verify database connection
        db_healthy = await check_db_health(db_pool)
        if not db_healthy:
            raise Exception("Database health check failed")

        # Initialize event bus
        event_bus = EventBus(RABBITMQ_URL)
        await event_bus.connect()

        logger.info(f"✅ {SERVICE_NAME} service started")

    except Exception as e:
        logger.error(f"❌ Failed to start {SERVICE_NAME}: {e}")
        raise

    yield

    # Shutdown
    logger.info(f"🛑 Shutting down {SERVICE_NAME} service...")

    try:
        if event_bus:
            await event_bus.disconnect()

        if db_pool:
            await close_db_pool()

        logger.info(f"✅ {SERVICE_NAME} service stopped")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title=f"{SERVICE_NAME} API",
    description="Portfolio management and holdings tracking",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    checks = {}

    # Check database
    if db_pool:
        checks["database"] = "healthy" if await check_db_health(db_pool) else "unhealthy"
    else:
        checks["database"] = "not initialized"

    # Check event bus
    if event_bus:
        checks["event_bus"] = "healthy" if await event_bus.health_check() else "unhealthy"
    else:
        checks["event_bus"] = "not initialized"

    return HealthCheck(
        status="healthy",
        service=SERVICE_NAME,
        checks=checks,
    )


@app.get("/holdings", response_model=List[Holding])
async def get_holdings():
    """Get all holdings"""
    try:
        query = """
            SELECT symbol, quantity, avg_price, current_value, pnl, pnl_percentage
            FROM holdings
            WHERE quantity > 0
            ORDER BY symbol
        """
        rows = await execute_query(db_pool, query)

        holdings = [
            Holding(
                symbol=row["symbol"],
                quantity=row["quantity"],
                avg_price=row["avg_price"],
                current_value=row["current_value"],
                pnl=row["pnl"],
                pnl_percentage=row["pnl_percentage"],
            )
            for row in rows
        ]

        logger.debug(f"Retrieved {len(holdings)} holdings")
        return holdings

    except Exception as e:
        logger.error(f"Failed to get holdings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/holdings/{symbol}", response_model=Holding)
async def get_holding(symbol: str):
    """Get specific holding"""
    try:
        query = """
            SELECT symbol, quantity, avg_price, current_value, pnl, pnl_percentage
            FROM holdings
            WHERE symbol = $1
        """
        row = await execute_query(db_pool, query, symbol.upper())

        if not row:
            raise HTTPException(status_code=404, detail=f"Holding {symbol} not found")

        row = row[0]
        return Holding(
            symbol=row["symbol"],
            quantity=row["quantity"],
            avg_price=row["avg_price"],
            current_value=row["current_value"],
            pnl=row["pnl"],
            pnl_percentage=row["pnl_percentage"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get holding {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/holdings", response_model=Holding)
async def add_or_update_holding(holding: Holding):
    """Add or update a holding"""
    try:
        # Upsert holding
        query = """
            INSERT INTO holdings (symbol, quantity, avg_price, current_value, pnl, pnl_percentage)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (symbol) DO UPDATE SET
                quantity = $2,
                avg_price = $3,
                current_value = $4,
                pnl = $5,
                pnl_percentage = $6,
                updated_at = NOW()
            RETURNING symbol, quantity, avg_price, current_value, pnl, pnl_percentage
        """
        result = await execute_update(
            db_pool,
            query,
            holding.symbol.upper(),
            holding.quantity,
            holding.avg_price,
            holding.current_value,
            holding.pnl,
            holding.pnl_percentage,
        )

        # Emit event
        event = Event(
            event_type=EventType.PORTFOLIO_POSITION_CHANGE,
            data={
                "symbol": holding.symbol.upper(),
                "quantity": holding.quantity,
                "current_value": holding.current_value,
                "pnl": holding.pnl,
            },
            source=SERVICE_NAME,
        )
        await event_bus.publish(event)

        logger.info(f"✅ Updated holding: {holding.symbol}")
        return holding

    except Exception as e:
        logger.error(f"Failed to update holding {holding.symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transactions", response_model=dict)
async def add_transaction(transaction: Transaction):
    """Record a transaction"""
    try:
        query = """
            INSERT INTO transactions (symbol, quantity, price, transaction_type, order_id)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """
        result = await execute_update(
            db_pool,
            query,
            transaction.symbol.upper(),
            transaction.quantity,
            transaction.price,
            transaction.transaction_type,
            transaction.order_id,
        )

        logger.info(f"✅ Recorded {transaction.transaction_type} transaction for {transaction.symbol}")
        return {"status": "recorded", "symbol": transaction.symbol}

    except Exception as e:
        logger.error(f"Failed to record transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/portfolio/summary", response_model=dict)
async def get_portfolio_summary():
    """Get portfolio summary"""
    try:
        query = """
            SELECT
                COUNT(*) as total_holdings,
                SUM(current_value) as total_value,
                SUM(pnl) as total_pnl,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_positions
            FROM holdings
            WHERE quantity > 0
        """
        row = (await execute_query(db_pool, query))[0]

        return {
            "total_holdings": row["total_holdings"] or 0,
            "total_value": float(row["total_value"] or 0),
            "total_pnl": float(row["total_pnl"] or 0),
            "winning_positions": row["winning_positions"] or 0,
        }

    except Exception as e:
        logger.error(f"Failed to get portfolio summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/portfolio/snapshot", response_model=PortfolioSnapshot)
async def get_latest_snapshot():
    """Get latest portfolio snapshot"""
    try:
        query = """
            SELECT snapshot_date, total_value, cash_balance, invested_amount, pnl, pnl_percentage
            FROM portfolio_snapshots
            ORDER BY snapshot_date DESC
            LIMIT 1
        """
        row = await execute_query(db_pool, query)

        if not row:
            raise HTTPException(status_code=404, detail="No portfolio snapshot found")

        row = row[0]
        return PortfolioSnapshot(
            snapshot_date=str(row["snapshot_date"]),
            total_value=float(row["total_value"]),
            cash_balance=float(row["cash_balance"]),
            invested_amount=float(row["invested_amount"]),
            pnl=float(row["pnl"]),
            pnl_percentage=float(row["pnl_percentage"]),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get portfolio snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/portfolio/snapshot", response_model=dict)
async def create_snapshot(snapshot: PortfolioSnapshot):
    """Create a portfolio snapshot"""
    try:
        query = """
            INSERT INTO portfolio_snapshots (
                snapshot_date, total_value, cash_balance, invested_amount, pnl, pnl_percentage
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (snapshot_date) DO UPDATE SET
                total_value = $2,
                cash_balance = $3,
                invested_amount = $4,
                pnl = $5,
                pnl_percentage = $6
        """
        await execute_update(
            db_pool,
            query,
            snapshot.snapshot_date,
            snapshot.total_value,
            snapshot.cash_balance,
            snapshot.invested_amount,
            snapshot.pnl,
            snapshot.pnl_percentage,
        )

        # Emit event
        event = Event(
            event_type=EventType.PORTFOLIO_SNAPSHOT,
            data={
                "snapshot_date": snapshot.snapshot_date,
                "total_value": snapshot.total_value,
                "pnl": snapshot.pnl,
            },
            source=SERVICE_NAME,
        )
        await event_bus.publish(event)

        logger.info(f"✅ Created portfolio snapshot for {snapshot.snapshot_date}")
        return {"status": "created", "snapshot_date": snapshot.snapshot_date}

    except Exception as e:
        logger.error(f"Failed to create portfolio snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/portfolio-scan", response_model=dict)
async def portfolio_scan():
    """
    Trigger portfolio scan and load holdings from CSV as fallback.
    Returns portfolio data with source indicating where data came from.
    """
    try:
        import csv
        from pathlib import Path
        import aiofiles

        logger.info("Portfolio scan triggered - loading CSV data")

        # Find and load holdings CSV
        holdings_dir = Path("/app/holdings")
        if not holdings_dir.exists():
            logger.warning(f"Holdings directory not found: {holdings_dir}")
            return {
                "source": "empty",
                "portfolio": {
                    "holdings": [],
                    "cash": {"currency": "INR", "free": 0.0, "margin": 0.0},
                    "exposure_total": 0.0,
                },
                "analytics": {}
            }

        # Find most recent CSV file
        csv_files = sorted(
            holdings_dir.glob("*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if not csv_files:
            logger.warning("No CSV files found in holdings directory")
            return {
                "source": "empty",
                "portfolio": {
                    "holdings": [],
                    "cash": {"currency": "INR", "free": 0.0, "margin": 0.0},
                    "exposure_total": 0.0,
                },
                "analytics": {}
            }

        csv_path = csv_files[0]
        logger.info(f"Loading holdings from {csv_path.name}")

        # Load CSV asynchronously
        holdings = []
        async with aiofiles.open(csv_path, mode='r', encoding='utf-8-sig') as f:
            content = await f.read()
            reader = csv.DictReader(content.splitlines())

            for row in reader:
                symbol = row.get("Instrument", "").strip().strip('"')
                if not symbol:
                    continue

                try:
                    qty = int(float(row.get("Qty.", 0)))
                    avg_cost = float(row.get("Avg. cost", 0))
                    ltp = float(row.get("LTP", 0))
                    invested = float(row.get("Invested", 0))
                    current_value = float(row.get("Cur. val", 0))
                    pnl = float(row.get("P&L", 0))
                    pnl_pct = float(row.get("Net chg.", 0))

                    holdings.append({
                        "symbol": symbol,
                        "quantity": qty,
                        "avg_price": avg_cost,
                        "current_value": current_value,
                        "pnl": pnl,
                        "pnl_percentage": pnl_pct,
                        "ltp": ltp,
                        "invested": invested,
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse holding {symbol}: {e}")
                    continue

        # Calculate portfolio totals
        total_invested = sum(h["invested"] for h in holdings)
        total_current = sum(h["current_value"] for h in holdings)
        total_pnl = sum(h["pnl"] for h in holdings)
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

        logger.info(f"✅ Loaded {len(holdings)} holdings from CSV, total value: ₹{total_current:,.2f}")

        return {
            "source": "csv_fallback",
            "portfolio": {
                "holdings": holdings,
                "cash": {"currency": "INR", "free": 0.0, "margin": 0.0},
                "total_invested": total_invested,
                "total_current": total_current,
                "total_pnl": total_pnl,
                "exposure_total": total_current,
                "as_of": datetime.utcnow().isoformat(),
            },
            "analytics": {
                "portfolio_value": total_current,
                "cash_available": 0.0,
                "total_pnl": total_pnl,
                "total_pnl_percentage": total_pnl_pct,
                "positions_count": len(holdings),
            }
        }

    except Exception as e:
        logger.error(f"Portfolio scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Portfolio scan failed: {str(e)}")


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return {
        "error": exc.detail,
        "code": str(exc.status_code),
        "service": SERVICE_NAME,
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": "Internal server error",
        "code": "500",
        "service": SERVICE_NAME,
    }


if __name__ == "__main__":
    import uvicorn

    # Setup logging
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=SERVICE_PORT,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
