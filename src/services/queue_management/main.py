"""Queue Management Service - Main entry point."""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.config import Config
from ...core.logging_config import setup_logging
from ...core.event_bus import initialize_event_bus, EventBus
from ...stores.scheduler_task_store import SchedulerTaskStore
from ...services.scheduler.task_service import SchedulerTaskService

from .core.queue_orchestration_layer import QueueOrchestrationLayer
from .core.task_scheduling_engine import TaskSchedulingEngine
from .core.queue_monitoring import QueueMonitoring
from .api.routes import create_router
from .config.service_config import QueueManagementConfig

# Setup logging
logger = logging.getLogger(__name__)


class QueueManagementService:
    """Main Queue Management Service class."""

    def __init__(self, config: Config):
        """Initialize the service."""
        self.config = config
        self.app: Optional[FastAPI] = None
        self.orchestration_layer: Optional[QueueOrchestrationLayer] = None
        self.scheduling_engine: Optional[TaskSchedulingEngine] = None
        self.monitoring: Optional[QueueMonitoring] = None
        self.task_service: Optional[SchedulerTaskService] = None
        self.event_bus: Optional[EventBus] = None

        # Service configuration
        self.service_config = QueueManagementConfig()

        # Shutdown event
        self.shutdown_event = asyncio.Event()

    async def initialize(self) -> None:
        """Initialize all service components."""
        logger.info("Initializing Queue Management Service...")

        try:
            # Initialize event bus
            self.event_bus = await initialize_event_bus(self.config)

            # Initialize database components
            task_store = SchedulerTaskStore(self.config)
            await task_store.initialize()
            self.task_service = SchedulerTaskService(task_store)

            # Initialize core components
            self.orchestration_layer = QueueOrchestrationLayer(
                task_service=self.task_service,
                event_bus=self.event_bus,
                config=self.service_config
            )

            self.scheduling_engine = TaskSchedulingEngine(
                task_service=self.task_service,
                event_bus=self.event_bus,
                config=self.service_config
            )

            self.monitoring = QueueMonitoring(
                orchestration_layer=self.orchestration_layer,
                scheduling_engine=self.scheduling_engine,
                config=self.service_config
            )

            # Initialize orchestration layer
            await self.orchestration_layer.initialize()

            # Initialize scheduling engine
            await self.scheduling_engine.initialize()

            # Initialize monitoring
            await self.monitoring.initialize()

            logger.info("Queue Management Service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Queue Management Service: {e}")
            raise

    async def start(self) -> None:
        """Start the service."""
        logger.info("Starting Queue Management Service...")

        try:
            # Start orchestration layer
            await self.orchestration_layer.start()

            # Start scheduling engine
            await self.scheduling_engine.start()

            # Start monitoring
            await self.monitoring.start()

            logger.info("Queue Management Service started successfully")

        except Exception as e:
            logger.error(f"Failed to start Queue Management Service: {e}")
            raise

    async def stop(self) -> None:
        """Stop the service."""
        logger.info("Stopping Queue Management Service...")

        try:
            # Stop monitoring
            if self.monitoring:
                await self.monitoring.stop()

            # Stop scheduling engine
            if self.scheduling_engine:
                await self.scheduling_engine.stop()

            # Stop orchestration layer
            if self.orchestration_layer:
                await self.orchestration_layer.stop()

            logger.info("Queue Management Service stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping Queue Management Service: {e}")

    def create_fastapi_app(self) -> FastAPI:
        """Create FastAPI application."""
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await self.initialize()
            await self.start()
            yield
            # Shutdown
            await self.stop()

        self.app = FastAPI(
            title="Queue Management Service",
            description="Advanced task scheduling and orchestration service",
            version="1.0.0",
            lifespan=lifespan
        )

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add routes
        router = create_router(
            orchestration_layer=self.orchestration_layer,
            scheduling_engine=self.scheduling_engine,
            monitoring=self.monitoring
        )
        self.app.include_router(router, prefix="/api/v1")

        # Health check endpoint
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            try:
                health_status = await self.monitoring.health_check() if self.monitoring else {"status": "initializing"}
                return {
                    "status": "healthy",
                    "service": "queue_management",
                    "components": health_status
                }
            except Exception as e:
                raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

        return self.app

    async def run_server(self, host: str = "0.0.0.0", port: int = 8001) -> None:
        """Run the FastAPI server."""
        app = self.create_fastapi_app()

        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Configure uvicorn
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)

        try:
            logger.info(f"Starting Queue Management Service server on {host}:{port}")
            await server.serve()
        except asyncio.CancelledError:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            await self.stop()


async def main():
    """Main entry point."""
    # Setup logging
    setup_logging()

    # Load configuration
    config = Config()

    # Create and run service
    service = QueueManagementService(config)

    try:
        await service.run_server()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())