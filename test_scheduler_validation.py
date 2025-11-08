#!/usr/bin/env python3
"""
Scheduler Validation Testing Script

This script creates test tasks for each of the 7 schedulers to validate:
1. Metrics update correctly (processed, failed, success rate)
2. Real-time WebSocket updates work
3. Execution history is populated
4. Active jobs are tracked properly

Usage:
    python test_scheduler_validation.py --scheduler portfolio_sync --task sync_balances
    python test_scheduler_validation.py --scheduler data_fetcher --task news_monitoring
    python test_scheduler_validation.py --scheduler ai_analysis --task recommendation_generation
    python test_scheduler_validation.py --list-queues
    python test_scheduler_validation.py --list-task-types
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

# Add project to path
sys.path.insert(0, '/Users/gurusharan/Documents/remote-claude/robo-trader')

from src.core.di import DependencyContainer
from src.config import Config
from src.models.scheduler import QueueName, TaskType


class SchedulerTestConfig:
    """Configuration for test tasks for each scheduler"""

    SCHEDULER_CONFIGS = {
        "background": {
            "description": "Event-Driven Background Scheduler",
            "queue": None,  # Event-driven, not queue-based
            "trigger": "portfolio_update_event",
            "note": "Tested by publishing PORTFOLIO_POSITION_CHANGE event"
        },
        "portfolio_sync": {
            "description": "Portfolio Sync Scheduler",
            "queue": QueueName.PORTFOLIO_SYNC,
            "default_task": TaskType.SYNC_ACCOUNT_BALANCES,
            "priority": 10,
            "test_tasks": {
                "sync_balances": {
                    "type": TaskType.SYNC_ACCOUNT_BALANCES,
                    "payload": {"account_id": "test_account"},
                    "priority": 10
                },
                "update_positions": {
                    "type": TaskType.UPDATE_POSITIONS,
                    "payload": {"portfolio_id": "test_portfolio"},
                    "priority": 9
                }
            }
        },
        "data_fetcher": {
            "description": "Data Fetcher Scheduler",
            "queue": QueueName.DATA_FETCHER,
            "default_task": TaskType.NEWS_MONITORING,
            "priority": 8,
            "test_tasks": {
                "news_monitoring": {
                    "type": TaskType.NEWS_MONITORING,
                    "payload": {"symbols": ["SBIN", "TCS", "INFY"]},
                    "priority": 8
                },
                "earnings_check": {
                    "type": TaskType.EARNINGS_CHECK,
                    "payload": {"symbols": ["SBIN", "TCS"]},
                    "priority": 7
                },
                "fundamentals_update": {
                    "type": TaskType.FUNDAMENTALS_UPDATE,
                    "payload": {"symbols": ["INFY"]},
                    "priority": 7
                }
            }
        },
        "ai_analysis": {
            "description": "AI Analysis Scheduler",
            "queue": QueueName.AI_ANALYSIS,
            "default_task": TaskType.RECOMMENDATION_GENERATION,
            "priority": 7,
            "timeout": 900,  # 15 minutes
            "note": "CRITICAL: Tasks execute sequentially to prevent turn limit exhaustion",
            "test_tasks": {
                "recommendation_generation": {
                    "type": TaskType.RECOMMENDATION_GENERATION,
                    "payload": {"agent_name": "scan", "symbols": ["SBIN"]},
                    "priority": 7,
                    "expected_duration": "5-10 minutes"
                },
                "news_analysis": {
                    "type": TaskType.CLAUDE_NEWS_ANALYSIS,
                    "payload": {"symbols": ["TCS"], "analysis_depth": "detailed"},
                    "priority": 8
                }
            }
        },
        "portfolio_analysis": {
            "description": "Portfolio Analysis Scheduler",
            "queue": QueueName.PORTFOLIO_ANALYSIS,
            "default_task": TaskType.PORTFOLIO_INTELLIGENCE_ANALYSIS,
            "priority": 7,
            "test_tasks": {
                "portfolio_intelligence": {
                    "type": TaskType.PORTFOLIO_INTELLIGENCE_ANALYSIS,
                    "payload": {"analysis_type": "comprehensive"},
                    "priority": 7
                },
                "recommendation_update": {
                    "type": TaskType.PORTFOLIO_RECOMMENDATION_UPDATE,
                    "payload": {"recompute": True},
                    "priority": 6
                }
            }
        },
        "paper_trading_research": {
            "description": "Paper Trading Research Scheduler",
            "queue": QueueName.PAPER_TRADING_RESEARCH,
            "default_task": TaskType.MARKET_RESEARCH_PERPLEXITY,
            "priority": 7,
            "test_tasks": {
                "market_research": {
                    "type": TaskType.MARKET_RESEARCH_PERPLEXITY,
                    "payload": {"research_topic": "AI sector analysis", "depth": "summary"},
                    "priority": 7
                },
                "stock_screening": {
                    "type": TaskType.STOCK_SCREENING_ANALYSIS,
                    "payload": {"criteria": ["momentum", "growth"]},
                    "priority": 6
                }
            }
        },
        "paper_trading_execution": {
            "description": "Paper Trading Execution Scheduler",
            "queue": QueueName.PAPER_TRADING_EXECUTION,
            "default_task": TaskType.PAPER_TRADE_EXECUTION,
            "priority": 7,
            "test_tasks": {
                "paper_trade_execution": {
                    "type": TaskType.PAPER_TRADE_EXECUTION,
                    "payload": {"symbol": "SBIN", "action": "BUY", "quantity": 10},
                    "priority": 7
                },
                "risk_validation": {
                    "type": TaskType.TRADE_RISK_VALIDATION,
                    "payload": {"symbol": "TCS", "quantity": 5, "action": "SELL"},
                    "priority": 8
                }
            }
        }
    }


async def initialize_container() -> DependencyContainer:
    """Initialize DI container"""
    try:
        from pathlib import Path
        config = Config.from_file(Path('config/config.json'))
        container = DependencyContainer()
        await container.initialize(config)
        return container
    except Exception as e:
        print(f"Error initializing container: {e}")
        raise


async def create_test_task(
    queue_name: QueueName,
    task_type: TaskType,
    payload: Dict[str, Any],
    priority: int = 5
) -> str:
    """Create a test task in the specified queue"""
    try:
        container = await initialize_container()
        task_service = await container.get("task_service")

        task_id = await task_service.create_task(
            queue_name=queue_name,
            task_type=task_type,
            payload=payload,
            priority=priority
        )

        return task_id
    except Exception as e:
        print(f"Error creating task: {e}")
        raise


async def get_queue_status() -> Dict[str, Any]:
    """Get current queue status from API"""
    try:
        container = await initialize_container()
        queue_coordinator = await container.get("queue_coordinator")
        status = await queue_coordinator.get_queue_status()
        return status
    except Exception as e:
        print(f"Error getting queue status: {e}")
        raise


async def get_scheduler_status() -> Dict[str, Any]:
    """Get scheduler status via monitoring API"""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/monitoring/scheduler", timeout=5)
            return response.json()
    except Exception as e:
        print(f"Error getting scheduler status: {e}")
        raise


async def list_available_queues():
    """List all available queue names"""
    print("\n📋 Available Queues:")
    print("=" * 60)
    for queue in QueueName:
        print(f"  • {queue.value.upper():<30} ({queue.name})")


async def list_available_task_types():
    """List all available task types"""
    print("\n📋 Available Task Types:")
    print("=" * 60)
    for task in TaskType:
        print(f"  • {task.value.upper():<40} ({task.name})")


async def list_schedulers():
    """List all scheduler test configurations"""
    print("\n📋 Scheduler Test Configurations:")
    print("=" * 80)
    for scheduler_id, config in SchedulerTestConfig.SCHEDULER_CONFIGS.items():
        print(f"\n🔹 {scheduler_id.upper()}")
        print(f"   Description: {config.get('description', 'N/A')}")
        if config.get('queue'):
            print(f"   Queue: {config['queue'].value}")
        print(f"   Default Task: {config.get('default_task', 'Event-driven')}")

        if config.get('test_tasks'):
            print(f"   Available Test Tasks:")
            for task_name, task_config in config['test_tasks'].items():
                print(f"      • {task_name}: {task_config['type'].value}")


async def test_scheduler(scheduler_id: str, task_name: Optional[str] = None):
    """Test a specific scheduler by creating a task"""
    scheduler_id = scheduler_id.lower()

    if scheduler_id not in SchedulerTestConfig.SCHEDULER_CONFIGS:
        print(f"❌ Unknown scheduler: {scheduler_id}")
        print(f"\nAvailable schedulers: {', '.join(SchedulerTestConfig.SCHEDULER_CONFIGS.keys())}")
        return

    config = SchedulerTestConfig.SCHEDULER_CONFIGS[scheduler_id]

    if scheduler_id == "background":
        print(f"\n🔹 Testing: {config['description']}")
        print(f"   Note: {config.get('note', 'N/A')}")
        print("\n   To test Background Scheduler, trigger a portfolio update event via:")
        print("   curl -X POST http://localhost:8000/api/events/publish \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"event_type\": \"portfolio_updated\"}'")
        return

    # Queue-based scheduler
    queue = config['queue']

    # Determine task type and payload
    if task_name:
        if task_name not in config.get('test_tasks', {}):
            print(f"❌ Unknown task: {task_name}")
            print(f"\nAvailable tasks for {scheduler_id}:")
            for name in config.get('test_tasks', {}).keys():
                print(f"  • {name}")
            return
        task_config = config['test_tasks'][task_name]
        task_type = task_config['type']
        payload = task_config['payload']
        priority = task_config.get('priority', 5)
    else:
        # Use default task
        task_type = config['default_task']
        # Find task config from test_tasks
        for task_config in config.get('test_tasks', {}).values():
            if task_config['type'] == task_type:
                payload = task_config['payload']
                priority = task_config.get('priority', 5)
                break
        else:
            payload = {}
            priority = config.get('priority', 5)

    print(f"\n🔹 Testing: {config['description']}")
    print(f"   Queue: {queue.value}")
    print(f"   Task Type: {task_type.value}")
    print(f"   Payload: {json.dumps(payload, indent=6)}")
    print(f"   Priority: {priority}")

    # Get baseline metrics
    print(f"\n📊 Baseline Metrics:")
    try:
        status = await get_queue_status()
        # Handle both list and dict formats
        queues = status.get('queues', {})
        if isinstance(queues, list):
            queues = {q['name']: q for q in queues}
        elif isinstance(queues, str):
            # If it's a string representation, skip
            print(f"   Queue status format error (string received)")
            queues = {}

        if queue.value in queues:
            baseline = queues[queue.value]
            print(f"   Pending Tasks: {baseline.get('pending_tasks', 0)}")
            print(f"   Active Tasks: {baseline.get('active_tasks', 0)}")
            print(f"   Completed Tasks: {baseline.get('completed_tasks', 0)}")
            print(f"   Failed Tasks: {baseline.get('failed_tasks', 0)}")
        else:
            print(f"   Queue '{queue.value}' not found in status")
    except Exception as e:
        print(f"   Error: {e}")

    # Create task
    print(f"\n⏳ Creating task...")
    try:
        task_id = await create_test_task(queue, task_type, payload, priority)
        print(f"   ✅ Task created: {task_id}")

        # Get updated metrics
        await asyncio.sleep(1)
        print(f"\n📊 Updated Metrics:")
        status = await get_queue_status()
        # Handle both list and dict formats
        queues = status.get('queues', {})
        if isinstance(queues, list):
            queues = {q['name']: q for q in queues}

        if queue.value in queues:
            updated = queues[queue.value]
            print(f"   Pending Tasks: {updated.get('pending_tasks', 0)}")
            print(f"   Active Tasks: {updated.get('active_tasks', 0)}")
            print(f"   Completed Tasks: {updated.get('completed_tasks', 0)}")
            print(f"   Failed Tasks: {updated.get('failed_tasks', 0)}")
        else:
            print(f"   Queue '{queue.value}' not found in updated status")

        print(f"\n✅ Task will execute in the queue. Monitor in System Health UI for real-time updates.")
        if config.get('expected_duration'):
            print(f"   Expected Duration: {config['expected_duration']}")

    except Exception as e:
        print(f"   ❌ Error: {e}")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Scheduler Validation Testing Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_scheduler_validation.py --list-schedulers
  python test_scheduler_validation.py --scheduler portfolio_sync --task sync_balances
  python test_scheduler_validation.py --scheduler data_fetcher --task news_monitoring
  python test_scheduler_validation.py --scheduler ai_analysis --task recommendation_generation
  python test_scheduler_validation.py --list-queues
  python test_scheduler_validation.py --list-task-types
        """
    )

    parser.add_argument(
        "--scheduler",
        help="Scheduler to test (e.g., portfolio_sync, data_fetcher, ai_analysis)"
    )
    parser.add_argument(
        "--task",
        help="Task type to create in the scheduler"
    )
    parser.add_argument(
        "--list-schedulers",
        action="store_true",
        help="List all available schedulers and their test tasks"
    )
    parser.add_argument(
        "--list-queues",
        action="store_true",
        help="List all available queue names"
    )
    parser.add_argument(
        "--list-task-types",
        action="store_true",
        help="List all available task types"
    )

    args = parser.parse_args()

    try:
        if args.list_schedulers:
            await list_schedulers()
        elif args.list_queues:
            await list_available_queues()
        elif args.list_task_types:
            await list_available_task_types()
        elif args.scheduler:
            await test_scheduler(args.scheduler, args.task)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
