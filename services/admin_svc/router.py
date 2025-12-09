"""
Admin Service Router - Service registry management and live dashboard
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.rssbot.core.security import verify_service_token
from src.rssbot.core.exceptions import ServiceError
from src.rssbot.models.service_registry import RegisteredService, ConnectionMethod
from src.rssbot.discovery import ServiceRegistryManager, ServiceScanner


# Pydantic models for API
class ServiceUpdateRequest(BaseModel):
    connection_method: Optional[ConnectionMethod] = None
    rest_url: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class ServiceStatusResponse(BaseModel):
    name: str
    display_name: str
    status: str
    connection_method: str
    health_status: str
    last_check: Optional[datetime]
    is_active: bool


# Create the router
router = APIRouter(
    tags=["admin"],
    responses={404: {"description": "Not found"}},
)

# Service state
_registry_manager: Optional[ServiceRegistryManager] = None


async def initialize_service():
    """Initialize the admin service"""
    global _registry_manager
    _registry_manager = ServiceRegistryManager()
    print("Admin service initialized successfully")


def register_with_controller(controller_app):
    """Register this service with the controller app"""
    controller_app.include_router(router, prefix="/admin", tags=["admin"])
    print("Admin service router registered with controller at /admin")


def set_registry_manager(registry: ServiceRegistryManager):
    """Set the registry manager (injected by controller)"""
    global _registry_manager
    _registry_manager = registry


# HTML Templates
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RSS Bot Admin Dashboard</title>
    <script src="https://unpkg.com/htmx.org@1.9.6"></script>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: 600; }
        .status-healthy { color: #28a745; font-weight: bold; }
        .status-degraded { color: #ffc107; font-weight: bold; }
        .status-down { color: #dc3545; font-weight: bold; }
        .status-unknown { color: #6c757d; font-weight: bold; }
        .method-router { background: #e3f2fd; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; }
        .method-rest { background: #f3e5f5; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; }
        .method-disabled { background: #ffebee; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; }
        button { background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        button.secondary { background: #6c757d; }
        button.danger { background: #dc3545; }
        .btn-group { display: flex; gap: 8px; }
        .controls { margin-bottom: 20px; }
        .loading { opacity: 0.7; }
        select { padding: 6px; border: 1px solid #ddd; border-radius: 4px; }
        input { padding: 6px; border: 1px solid #ddd; border-radius: 4px; width: 200px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
        .stat-label { color: #6c757d; }
        .auto-refresh { float: right; }
        #refresh-indicator { color: #28a745; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 RSS Bot Admin Dashboard</h1>
            <p>Service Registry Management & Monitoring</p>
            <div class="auto-refresh">
                <label>
                    <input type="checkbox" id="auto-refresh" checked> Auto-refresh (30s)
                </label>
                <span id="refresh-indicator"></span>
            </div>
        </div>
        
        <div class="stats" id="stats" hx-get="/admin/stats" hx-trigger="load, every 30s">
            <!-- Stats will be loaded here -->
        </div>
        
        <div class="card">
            <div class="controls">
                <div class="btn-group">
                    <button 
                        hx-post="/admin/services/rescan" 
                        hx-target="#services-table" 
                        hx-indicator="#loading">
                        🔄 Rescan All Services Now
                    </button>
                    <button 
                        hx-get="/admin/services" 
                        hx-target="#services-table">
                        📊 Refresh Table
                    </button>
                    <span id="loading" class="htmx-indicator">⏳ Processing...</span>
                </div>
            </div>
            
            <div id="services-table" 
                 hx-get="/admin/services" 
                 hx-trigger="load, every 30s[document.getElementById('auto-refresh').checked]">
                <!-- Services table will be loaded here -->
            </div>
        </div>
        
        <div class="card">
            <h3>💡 Quick Actions</h3>
            <div class="btn-group">
                <button onclick="toggleAllServices(true)">✅ Enable All Services</button>
                <button onclick="toggleAllServices(false)" class="secondary">⏸️ Disable All Services</button>
                <button onclick="forceHealthCheck()" class="secondary">🩺 Force Health Check</button>
            </div>
        </div>
    </div>

    <script>
        // Auto-refresh indicator
        setInterval(() => {
            if (document.getElementById('auto-refresh').checked) {
                const indicator = document.getElementById('refresh-indicator');
                indicator.textContent = '🔄';
                setTimeout(() => indicator.textContent = '', 1000);
            }
        }, 30000);

        // Service control functions
        function updateService(serviceName, field, value) {
            htmx.ajax('POST', `/admin/services/${serviceName}/${field}`, {
                values: { value: value },
                target: '#services-table'
            });
        }

        function toggleAllServices(enable) {
            htmx.ajax('POST', '/admin/services/bulk-update', {
                values: { is_active: enable },
                target: '#services-table'
            });
        }

        function forceHealthCheck() {
            htmx.ajax('POST', '/admin/health-check', {
                target: '#services-table'
            });
        }

        // Add loading states
        document.addEventListener('htmx:beforeRequest', (e) => {
            e.target.classList.add('loading');
        });
        document.addEventListener('htmx:afterRequest', (e) => {
            e.target.classList.remove('loading');
        });
    </script>
</body>
</html>
"""


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "admin_svc"}


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    return {
        "status": "ready",
        "service": "admin_svc",
        "features": ["service_registry", "live_dashboard", "htmx_ui"]
    }


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard():
    """Serve the main admin dashboard"""
    return DASHBOARD_HTML


@router.get("/stats")
async def get_stats():
    """Get system statistics for dashboard"""
    if not _registry_manager:
        return {"error": "Registry not initialized"}
    
    services = await _registry_manager.get_active_services()
    
    total_services = len(services)
    healthy_services = sum(1 for s in services if s.health_status == "healthy")
    router_services = sum(1 for s in services if s.connection_method == ConnectionMethod.ROUTER)
    rest_services = sum(1 for s in services if s.connection_method == ConnectionMethod.REST)
    
    return f"""
    <div class="stat-card">
        <div class="stat-number">{total_services}</div>
        <div class="stat-label">Total Services</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{healthy_services}</div>
        <div class="stat-label">Healthy Services</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{router_services}</div>
        <div class="stat-label">Router Mode</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{rest_services}</div>
        <div class="stat-label">REST Mode</div>
    </div>
    """


@router.get("/services")
async def get_services_table():
    """Get services table HTML"""
    if not _registry_manager:
        return "<p>Registry not initialized</p>"
    
    services = await _registry_manager.get_active_services()
    
    if not services:
        return "<p>No services found. Run a rescan to discover services.</p>"
    
    # Generate table HTML
    rows = []
    for service in services:
        status_class = f"status-{service.health_status}"
        method_class = f"method-{service.connection_method.value}"
        
        last_check = service.last_health_check.strftime("%H:%M:%S") if service.last_health_check else "Never"
        
        rows.append(f"""
        <tr>
            <td><strong>{service.display_name}</strong><br><small>{service.name}</small></td>
            <td><span class="{status_class}">{service.health_status.upper()}</span></td>
            <td>
                <select onchange="updateService('{service.name}', 'method', this.value)">
                    <option value="router" {'selected' if service.connection_method == ConnectionMethod.ROUTER else ''}>Router</option>
                    <option value="rest" {'selected' if service.connection_method == ConnectionMethod.REST else ''}>REST</option>
                    <option value="disabled" {'selected' if service.connection_method == ConnectionMethod.DISABLED else ''}>Disabled</option>
                </select>
            </td>
            <td>{service.rest_url or 'N/A'}</td>
            <td>{last_check}</td>
            <td>
                <input type="checkbox" {'checked' if service.is_active else ''} 
                       onchange="updateService('{service.name}', 'active', this.checked)">
            </td>
            <td>
                <div class="btn-group">
                    <button onclick="updateService('{service.name}', 'health-check', true)" class="secondary">🩺</button>
                </div>
            </td>
        </tr>
        """)
    
    table_html = f"""
    <table>
        <thead>
            <tr>
                <th>Service</th>
                <th>Health</th>
                <th>Method</th>
                <th>REST URL</th>
                <th>Last Check</th>
                <th>Active</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
    <p><small>Last updated: {datetime.now().strftime('%H:%M:%S')}</small></p>
    """
    
    return table_html


@router.post("/services/rescan")
async def rescan_services(token: str = Depends(verify_service_token)):
    """Trigger full service rescan"""
    if not _registry_manager:
        raise HTTPException(status_code=500, detail="Registry not initialized")
    
    try:
        results = await _registry_manager.sync_discovered_services()
        return {
            "success": True,
            "message": f"Rescan complete. {results['total_discovered']} services discovered.",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rescan failed: {str(e)}")


@router.post("/services/{service_name}/method")
async def update_service_method(
    service_name: str,
    request: Request,
    token: str = Depends(verify_service_token)
):
    """Update service connection method"""
    if not _registry_manager:
        raise HTTPException(status_code=500, detail="Registry not initialized")
    
    form = await request.form()
    value = form.get("value")
    
    try:
        method = ConnectionMethod(value)
        success = await _registry_manager.update_service_config(
            service_name, 
            connection_method=method
        )
        
        if success:
            return {"success": True, "message": f"Updated {service_name} method to {method.value}"}
        else:
            raise HTTPException(status_code=404, detail="Service not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid connection method")


@router.post("/services/{service_name}/active")
async def update_service_active(
    service_name: str,
    request: Request,
    token: str = Depends(verify_service_token)
):
    """Update service active status"""
    if not _registry_manager:
        raise HTTPException(status_code=500, detail="Registry not initialized")
    
    form = await request.form()
    value = form.get("value").lower() == "true"
    
    success = await _registry_manager.update_service_config(
        service_name,
        is_active=value
    )
    
    if success:
        return {"success": True, "message": f"Updated {service_name} active status"}
    else:
        raise HTTPException(status_code=404, detail="Service not found")


@router.post("/services/{service_name}/url")
async def update_service_url(
    service_name: str,
    request: Request,
    token: str = Depends(verify_service_token)
):
    """Update service REST URL"""
    if not _registry_manager:
        raise HTTPException(status_code=500, detail="Registry not initialized")
    
    form = await request.form()
    url = form.get("url", "").strip()
    
    success = await _registry_manager.update_service_config(
        service_name,
        rest_url=url if url else None
    )
    
    if success:
        return {"success": True, "message": f"Updated {service_name} REST URL"}
    else:
        raise HTTPException(status_code=404, detail="Service not found")