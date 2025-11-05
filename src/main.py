"""
Robo Trader Main Entry Point

Starts the autonomous trading system.
"""

import asyncio
import argparse
import os
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

# Load .env file first to get default LOG_LEVEL
load_dotenv()

from src.config import load_config
from .core.di import initialize_container, cleanup_container
from .core.orchestrator import RoboTraderOrchestrator


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Robo Trader - Autonomous Trading System")
    parser.add_argument("--config", type=Path, default=None, help="Path to config file")
    parser.add_argument("--command", choices=["scan", "screen", "monitor", "interactive", "web"],
                       default="interactive", help="Command to run")
    parser.add_argument("--env", choices=["paper", "live"], help="Override environment mode")
    parser.add_argument("--host", default="0.0.0.0", help="Web server host")
    parser.add_argument("--port", type=int, default=8000, help="Web server port")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       default=None, help="Set logging level (overrides .env config)")

    args = parser.parse_args()

    # Determine log level with proper priority:
    # 1. Command-line flag (highest priority)
    # 2. .env file LOG_LEVEL
    # 3. Default to INFO (lowest priority)
    if args.log_level is not None:
        # CLI flag provided - highest priority
        log_level = args.log_level
    else:
        # Use .env file or default to INFO
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Set environment variable for web app (inherited by uvicorn subprocess)
    os.environ["LOG_LEVEL"] = log_level

    # Load configuration
    config = load_config(args.config)

    # Override environment if specified
    if args.env:
        config.environment = args.env
        logger.info(f"Environment overridden to {args.env} mode")

    logger.info(f"Starting Robo Trader in {config.environment} mode")
    logger.info(f"Logging level: {log_level}")

    if args.command == "web":
        # Start web server (this will run its own event loop)
        from .web.app import run_web_server
        logger.info(f"Starting web server on {args.host}:{args.port}")
        run_web_server()
        return  # Exit here, uvicorn handles the event loop

    # For CLI commands, run async main
    asyncio.run(async_main(args, config))


async def async_main(args, config):
    """Async main for CLI commands."""
    # Initialize DI container
    container = await initialize_container(config)

    try:
        # Get orchestrator from container
        orchestrator = await container.get_orchestrator()

        if args.command == "scan":
            await run_portfolio_scan(orchestrator)
        elif args.command == "screen":
            await run_market_screening(orchestrator)
        elif args.command == "monitor":
            await run_monitoring(orchestrator)
        elif args.command == "interactive":
            await run_interactive(orchestrator)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await cleanup_container()


async def run_portfolio_scan(orchestrator: RoboTraderOrchestrator):
    """Run portfolio scan."""
    logger.info("Running portfolio scan...")
    await orchestrator.start_session()
    await orchestrator.run_portfolio_scan()


async def run_market_screening(orchestrator: RoboTraderOrchestrator):
    """Run market screening."""
    logger.info("Running market screening...")
    await orchestrator.start_session()
    await orchestrator.run_market_screening()


async def run_monitoring(orchestrator: RoboTraderOrchestrator):
    """Run market monitoring."""
    logger.info("Starting market monitoring...")
    await orchestrator.start_session()

    # In a real implementation, this would run continuously
    # For demo, just run once
    await orchestrator.process_query("Monitor market for alerts")


async def run_interactive(orchestrator: RoboTraderOrchestrator):
    """Run interactive mode."""
    logger.info("Starting interactive mode...")
    await orchestrator.start_session()

    print("Robo Trader Interactive Mode")
    print("Commands: scan, screen, monitor, quit")
    print("-" * 40)

    while True:
        try:
            command = input("robo-trader> ").strip().lower()

            if command == "quit":
                break
            elif command == "scan":
                await orchestrator.run_portfolio_scan()
            elif command == "screen":
                await orchestrator.run_market_screening()
            elif command == "monitor":
                await run_monitoring(orchestrator)
            else:
                # Treat as general query
                responses = await orchestrator.process_query(command)
                for response in responses:
                    print(response)

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"Error: {e}")


if __name__ == "__main__":
    main()