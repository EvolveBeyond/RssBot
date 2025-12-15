"""
Evox Orchestrator - Service discovery and management
"""
import os
import importlib
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI
import uvicorn
from src.rssbot.core.controller import create_platform_app as create_rssbot_app


class Orchestrator:
    """Evox service orchestrator"""
    
    def __init__(self):
        self.services: Dict[str, Any] = {}
        self.app: Optional[FastAPI] = None
    
    async def initialize(self):
        """Initialize the orchestrator with RssBot platform app"""
        try:
            self.app = await create_rssbot_app()
            print("✅ Evox orchestrator initialized with RssBot platform")
        except Exception as e:
            print(f"⚠️  Failed to initialize RssBot platform: {e}")
            # Fallback to minimal app
            self.app = FastAPI(title="Evox Orchestrator")
            self._setup_routes()
    
    def _setup_routes(self):
        """Setup orchestrator routes"""
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "orchestrator": "running"}
        
        @self.app.get("/services")
        async def list_services():
            return {"services": list(self.services.keys())}
    
    def discover_services(self, services_dir: str = "services"):
        """Discover services in the services directory"""
        services_path = Path(services_dir)
        if not services_path.exists():
            print(f"Services directory {services_dir} not found")
            return
        
        for service_dir in services_path.iterdir():
            if service_dir.is_dir() and not service_dir.name.startswith('.'):
                self._load_service(service_dir)
    
    def _load_service(self, service_dir: Path):
        """Load a service from its directory"""
        service_name = service_dir.name
        main_file = service_dir / "main.py"
        
        if not main_file.exists():
            print(f"Service {service_name} has no main.py file")
            return
        
        try:
            # Add services directory to path
            services_parent = str(service_dir.parent)
            if services_parent not in os.sys.path:
                os.sys.path.insert(0, services_parent)
            
            # Import service module
            module_name = f"services.{service_name}.main"
            service_module = importlib.import_module(module_name)
            
            # Store service info
            self.services[service_name] = {
                "module": service_module,
                "path": str(service_dir)
            }
            
            print(f"✅ Loaded service: {service_name}")
            
        except Exception as e:
            print(f"❌ Failed to load service {service_name}: {e}")
    
    async def run(self, port: int = 8000, dev: bool = False):
        """Run the orchestrator"""
        await self.initialize()
        self.discover_services()
        
        if dev:
            uvicorn.run(
                self.app,
                host="0.0.0.0",
                port=port,
                reload=True,
                log_level="debug"
            )
        else:
            uvicorn.run(
                self.app,
                host="0.0.0.0",
                port=port,
                log_level="info"
            )


# Global orchestrator instance
orchestrator = Orchestrator()