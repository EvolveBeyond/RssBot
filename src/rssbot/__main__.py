"""
RssBot Platform Entry Point

This allows running the platform directly with:
python -m rssbot

The core platform logic is centralized here instead of scattered 
across service directories.
"""
import asyncio
import os
import uvicorn
from .core.controller import create_platform_app


async def main():
    """Main entry point for the RssBot platform"""
    print("🚀 Starting RssBot Hybrid Microservices Platform")
    print("📍 Core location: src/rssbot/")
    
    # Create the platform app
    app = await create_platform_app()
    
    # Get configuration
    port = int(os.getenv("CONTROLLER_SERVICE_PORT", 8004))
    host = os.getenv("HOST", "0.0.0.0")
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    # Configure uvicorn
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level=log_level
    )
    
    # Start the server
    server = uvicorn.Server(config)
    print(f"🌟 Platform running on http://{host}:{port}")
    print(f"📊 Health check: http://{host}:{port}/health")
    print(f"🔧 Admin API: http://{host}:{port}/services")
    
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())