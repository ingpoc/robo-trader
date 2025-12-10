#!/usr/bin/env python
"""Test server startup without orchestrator"""

import asyncio
import os
from src.web.app import app
from uvicorn import Config, Server

async def main():
    print("Starting server without orchestrator...")

    # Set environment to skip orchestrator
    os.environ["SKIP_ORCHESTRATOR"] = "true"

    config = Config(
        app=app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
        access_log=False
    )
    server = Server(config)

    print("Server config created, starting...")
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())