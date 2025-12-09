"""
Controller Service - Lightweight wrapper for the core platform

This service now simply wraps the core controller logic located in:
src/rssbot/core/controller.py

The heavy lifting is done by the core platform, this service just
provides the entry point and port configuration.
"""
import os
import sys
import uvicorn
from pathlib import Path

# Add src to path for core imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from rssbot.core.controller import create_platform_app


# Create the app using the core platform
app = None


async def get_app():
    """Get the FastAPI app instance"""
    global app
    if app is None:
        print("🚀 Creating platform app using core controller...")
        app = await create_platform_app()
        print("✅ Platform app created successfully")
    return app


if __name__ == "__main__":
    import asyncio
    
    async def start_server():
        """Start the controller service"""
        # Get the platform app
        platform_app = await get_app()
        
        # Configure and start uvicorn
        port = int(os.getenv("CONTROLLER_SERVICE_PORT", 8004))
        config = uvicorn.Config(
            app=platform_app,
            host="0.0.0.0", 
            port=port,
            log_level=os.getenv("LOG_LEVEL", "info").lower()
        )
        
        server = uvicorn.Server(config)
        print(f"🌟 Starting RssBot Platform Controller on port {port}")
        print(f"🔗 Core logic location: src/rssbot/core/controller.py")
        await server.serve()
    
    # Run the server
    asyncio.run(start_server())