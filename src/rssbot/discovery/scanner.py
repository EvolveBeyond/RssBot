"""
Service Scanner - Auto-discovers services in the services/ folder
"""
import os
import sys
import importlib
import inspect
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..core.config import get_config
from ..core.exceptions import DiscoveryError


@dataclass
class ServiceInfo:
    """Information about a discovered service"""
    name: str
    display_name: str
    description: Optional[str]
    port: int
    has_router: bool
    router_path: Optional[str]
    main_path: str
    folder_path: str


class ServiceScanner:
    """Scans services/ folder for available services"""
    
    def __init__(self, services_root: str = None):
        self.config = get_config()
        
        # Default to services/ folder in project root
        if services_root is None:
            # Find project root (where pyproject.toml exists)
            current_dir = Path(__file__).parent
            while current_dir.parent != current_dir:
                if (current_dir / "pyproject.toml").exists():
                    services_root = str(current_dir / "services")
                    break
                current_dir = current_dir.parent
            else:
                raise DiscoveryError("Could not find project root with pyproject.toml")
        
        self.services_root = Path(services_root)
        
        if not self.services_root.exists():
            raise DiscoveryError(f"Services directory not found: {self.services_root}")
    
    def discover_services(self) -> List[ServiceInfo]:
        """
        Scan services/ folder and discover all available services.
        
        Returns:
            List of discovered services with metadata
        """
        services = []
        
        print(f"🔍 Scanning for services in: {self.services_root}")
        
        # Iterate through all subdirectories in services/
        for service_dir in self.services_root.iterdir():
            if not service_dir.is_dir():
                continue
            
            # Skip hidden directories and __pycache__
            if service_dir.name.startswith('.') or service_dir.name == '__pycache__':
                continue
            
            try:
                service_info = self._analyze_service(service_dir)
                if service_info:
                    services.append(service_info)
                    print(f"✅ Found service: {service_info.name}")
            except Exception as e:
                print(f"⚠️  Warning: Could not analyze service {service_dir.name}: {e}")
        
        print(f"🎯 Discovered {len(services)} services total")
        return services
    
    def _analyze_service(self, service_dir: Path) -> Optional[ServiceInfo]:
        """
        Analyze a single service directory to extract metadata.
        
        Args:
            service_dir: Path to service directory
            
        Returns:
            ServiceInfo if valid service found, None otherwise
        """
        service_name = service_dir.name
        
        # Check for main.py (required)
        main_file = service_dir / "main.py"
        if not main_file.exists():
            return None
        
        # Check for router.py (optional but preferred)
        router_file = service_dir / "router.py"
        has_router = router_file.exists()
        
        # Get service metadata
        display_name = self._extract_display_name(main_file, service_name)
        description = self._extract_description(main_file)
        port = self._extract_port(main_file, service_name)
        
        # Build import paths
        router_path = None
        if has_router:
            # Build relative import path: services.service_name.router
            router_path = f"services.{service_name}.router"
        
        main_path = f"services.{service_name}.main"
        
        return ServiceInfo(
            name=service_name,
            display_name=display_name,
            description=description,
            port=port,
            has_router=has_router,
            router_path=router_path,
            main_path=main_path,
            folder_path=str(service_dir)
        )
    
    def _extract_display_name(self, main_file: Path, service_name: str) -> str:
        """Extract display name from service main.py"""
        try:
            content = main_file.read_text()
            
            # Look for FastAPI title
            for line in content.split('\n'):
                if 'title=' in line and '"' in line:
                    # Extract text between quotes
                    start = line.find('"') + 1
                    end = line.find('"', start)
                    if start > 0 and end > start:
                        return line[start:end]
            
            # Fallback: convert service_name to display name
            return service_name.replace('_', ' ').title()
            
        except Exception:
            return service_name.replace('_', ' ').title()
    
    def _extract_description(self, main_file: Path) -> Optional[str]:
        """Extract description from service main.py"""
        try:
            content = main_file.read_text()
            
            # Look for FastAPI description
            for line in content.split('\n'):
                if 'description=' in line and '"' in line:
                    # Extract text between quotes
                    start = line.find('"') + 1
                    end = line.find('"', start)
                    if start > 0 and end > start:
                        return line[start:end]
            
            # Look for docstring at top of file
            lines = content.split('\n')
            in_docstring = False
            docstring_lines = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('"""') or line.startswith("'''"):
                    if in_docstring:
                        break  # End of docstring
                    in_docstring = True
                    # Remove opening quotes
                    line = line[3:].strip()
                    if line:
                        docstring_lines.append(line)
                elif in_docstring:
                    if line:
                        docstring_lines.append(line)
                elif line and not line.startswith('#'):
                    break  # Hit non-comment code
            
            if docstring_lines:
                return ' '.join(docstring_lines)
            
        except Exception:
            pass
        
        return None
    
    def _extract_port(self, main_file: Path, service_name: str) -> int:
        """Extract port number from service main.py or use default"""
        try:
            content = main_file.read_text()
            
            # Look for port assignment
            for line in content.split('\n'):
                if 'port =' in line or 'getenv(' in line:
                    # Try to extract port number
                    if service_name.upper() in line:
                        # Found service-specific port config
                        return self.config.get_service_port(service_name)
            
        except Exception:
            pass
        
        # Use config default
        return self.config.get_service_port(service_name)
    
    def validate_service(self, service_info: ServiceInfo) -> Dict[str, Any]:
        """
        Validate a service by trying to import its modules.
        
        Args:
            service_info: Service information to validate
            
        Returns:
            Validation results with status and details
        """
        results = {
            "valid": False,
            "has_main": False,
            "has_router": False,
            "router_callable": False,
            "errors": []
        }
        
        try:
            # Add services directory to path if needed
            services_parent = str(self.services_root.parent)
            if services_parent not in sys.path:
                sys.path.insert(0, services_parent)
            
            # Test main.py import
            try:
                main_module = importlib.import_module(service_info.main_path)
                results["has_main"] = True
                
                # Check for FastAPI app
                if hasattr(main_module, 'app'):
                    results["has_app"] = True
                
            except ImportError as e:
                results["errors"].append(f"Cannot import main: {e}")
            
            # Test router.py import if it exists
            if service_info.has_router and service_info.router_path:
                try:
                    router_module = importlib.import_module(service_info.router_path)
                    results["has_router"] = True
                    
                    # Check for router object
                    if hasattr(router_module, 'router'):
                        results["router_callable"] = True
                    
                    # Check for required functions
                    if hasattr(router_module, 'initialize_service'):
                        results["has_init"] = True
                    
                except ImportError as e:
                    results["errors"].append(f"Cannot import router: {e}")
            
            # Service is valid if main exists and no critical errors
            results["valid"] = results["has_main"] and len(results["errors"]) == 0
            
        except Exception as e:
            results["errors"].append(f"Validation failed: {e}")
        
        return results