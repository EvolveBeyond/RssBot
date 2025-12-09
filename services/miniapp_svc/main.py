"""
MiniApp Service - Dashboard and UI backend.
Provides backend API for the RSS Bot dashboard and management interface.

This service uses the new hybrid microservices architecture with ServiceProxy
for intelligent routing to other services based on their connection methods.
"""
import os
import sys
import uvicorn
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

# Add src to path for ServiceProxy imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from rssbot.discovery.proxy import ServiceProxy

# Initialize ServiceProxy instances for intelligent inter-service communication
controller_service = ServiceProxy("controller_svc")
bot_service = ServiceProxy("bot_svc")
channel_mgr_service = ServiceProxy("channel_mgr_svc")
user_service = ServiceProxy("user_svc")
ai_service = ServiceProxy("ai_svc")
formatting_service = ServiceProxy("formatting_svc")


# Security middleware for inter-service authentication
async def verify_service_token(x_service_token: Optional[str] = Header(None)):
    """Verify service-to-service authentication token."""
    expected_token = os.getenv("SERVICE_TOKEN", "dev_service_token_change_in_production")
    if x_service_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid service token")
    return x_service_token


# Pydantic models
class DashboardData(BaseModel):
    """Dashboard overview data."""
    total_users: int
    total_channels: int
    total_feeds: int
    active_feeds: int
    recent_activity: List[Dict[str, Any]]


class SystemStatus(BaseModel):
    """System status information."""
    services: Dict[str, str]  # service_name -> status
    overall_health: str
    uptime: str
    version: str


# FastAPI application
app = FastAPI(
    title="RSS Bot MiniApp Service",
    description="Dashboard and UI backend for the RSS Bot platform",
    version="0.1.0",
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize miniapp service."""
    print("MiniApp service started successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "miniapp_svc",
        "ui_available": True
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "service": "miniapp_svc",
        "features": ["dashboard", "user_management", "system_monitoring", "analytics"]
    }


async def call_service(service_name: str, endpoint: str) -> Dict[str, Any]:
    """
    Helper function to call other services using ServiceProxy.
    
    This function now uses the new hybrid microservices architecture
    with automatic routing based on per-service connection methods.
    ServiceProxy will automatically route to router (in-process) or REST (HTTP)
    based on each service's configured connection method.
    """
    try:
        # Get the appropriate ServiceProxy instance
        service_proxy = None
        if service_name == "controller_svc":
            service_proxy = controller_service
        elif service_name == "bot_svc":
            service_proxy = bot_service
        elif service_name == "channel_mgr_svc":
            service_proxy = channel_mgr_service
        elif service_name == "user_svc":
            service_proxy = user_service
        elif service_name == "ai_svc":
            service_proxy = ai_service
        elif service_name == "formatting_svc":
            service_proxy = formatting_service
        else:
            print(f"Unknown service: {service_name}")
            return {"error": f"Unknown service: {service_name}"}
        
        # Extract method name from endpoint (e.g., "/health" -> "health_check")
        method_name = endpoint.strip('/').replace('-', '_')
        if method_name == "health":
            method_name = "health_check"
        
        # Call service using ServiceProxy (automatically routes based on connection method)
        result = await service_proxy._execute_service_call(method_name)
        
        return result if isinstance(result, dict) else {"result": result}
        
    except Exception as e:
        print(f"Error calling {service_name} via ServiceProxy: {str(e)}")
        return {"error": str(e)}


@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the main dashboard page."""
    # TODO: Replace with actual Mesop or React frontend
    dashboard_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RSS Bot Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #2196F3; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stat-number { font-size: 2em; font-weight: bold; color: #2196F3; }
            .services { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .service { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
            .status-healthy { color: #4CAF50; font-weight: bold; }
            .status-unhealthy { color: #F44336; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 RSS Bot Platform Dashboard</h1>
                <p>Modular Telegram-RSS microservice management</p>
            </div>
            
            <div class="stats" id="stats">
                <div class="stat-card">
                    <div class="stat-number" id="total-users">-</div>
                    <div>Total Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-channels">-</div>
                    <div>Channels</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-feeds">-</div>
                    <div>RSS Feeds</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="active-feeds">-</div>
                    <div>Active Feeds</div>
                </div>
            </div>
            
            <div class="services">
                <h2>Service Status</h2>
                <div id="service-list">
                    <div class="service">
                        <span>Loading services...</span>
                        <span>-</span>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            async function loadDashboard() {
                try {
                    const response = await fetch('/api/dashboard-data');
                    const data = await response.json();
                    
                    document.getElementById('total-users').textContent = data.total_users;
                    document.getElementById('total-channels').textContent = data.total_channels;
                    document.getElementById('total-feeds').textContent = data.total_feeds;
                    document.getElementById('active-feeds').textContent = data.active_feeds;
                } catch (error) {
                    console.error('Failed to load dashboard data:', error);
                }
                
                try {
                    const response = await fetch('/api/system-status');
                    const status = await response.json();
                    
                    const serviceList = document.getElementById('service-list');
                    serviceList.innerHTML = '';
                    
                    for (const [service, health] of Object.entries(status.services)) {
                        const serviceDiv = document.createElement('div');
                        serviceDiv.className = 'service';
                        serviceDiv.innerHTML = `
                            <span>${service}</span>
                            <span class="status-${health === 'healthy' ? 'healthy' : 'unhealthy'}">${health}</span>
                        `;
                        serviceList.appendChild(serviceDiv);
                    }
                } catch (error) {
                    console.error('Failed to load system status:', error);
                }
            }
            
            loadDashboard();
            setInterval(loadDashboard, 30000); // Refresh every 30 seconds
        </script>
    </body>
    </html>
    """
    return dashboard_html


@app.get("/api/dashboard-data", response_model=DashboardData)
async def get_dashboard_data(token: str = Depends(verify_service_token)):
    """Get dashboard overview data."""
    try:
        # Get user stats
        user_stats = await call_service("user_svc", "/stats")
        total_users = user_stats.get("total_users", 0)
        
        # Get channel stats
        channel_stats = await call_service("channel_mgr_svc", "/stats")
        total_channels = channel_stats.get("total_channels", 0)
        total_feeds = channel_stats.get("total_feeds", 0)
        active_feeds = channel_stats.get("active_feeds", 0)
        
        # TODO: Get recent activity from database
        recent_activity = [
            {"type": "feed_check", "message": "Checked RSS feeds", "timestamp": datetime.now().isoformat()},
            {"type": "user_join", "message": "New user registered", "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat()}
        ]
        
        return DashboardData(
            total_users=total_users,
            total_channels=total_channels,
            total_feeds=total_feeds,
            active_feeds=active_feeds,
            recent_activity=recent_activity
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard data: {str(e)}")


@app.get("/api/system-status", response_model=SystemStatus)
async def get_system_status(token: str = Depends(verify_service_token)):
    """Get system status information."""
    try:
        services = {}
        service_names = ["user_svc", "channel_mgr_svc", "bot_svc", "payment_svc", "controller_svc"]
        
        for service_name in service_names:
            health_data = await call_service(service_name, "/health")
            if health_data and health_data.get("status") == "healthy":
                services[service_name] = "healthy"
            else:
                services[service_name] = "unhealthy"
        
        # Determine overall health
        healthy_count = sum(1 for status in services.values() if status == "healthy")
        if healthy_count == len(services):
            overall_health = "healthy"
        elif healthy_count > 0:
            overall_health = "degraded"
        else:
            overall_health = "unhealthy"
        
        return SystemStatus(
            services=services,
            overall_health=overall_health,
            uptime="Unknown",  # TODO: Calculate actual uptime
            version="0.1.0"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")


@app.get("/api/users")
async def get_users_api(
    skip: int = 0,
    limit: int = 50,
    token: str = Depends(verify_service_token)
):
    """Get users list for management interface."""
    try:
        users_data = await call_service("user_svc", f"/users?skip={skip}&limit={limit}")
        return users_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")


@app.get("/api/channels")
async def get_channels_api(token: str = Depends(verify_service_token)):
    """Get channels list for management interface."""
    try:
        # TODO: Implement channels listing in channel_mgr_svc
        return {"channels": [], "message": "Channels listing not yet implemented"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get channels: {str(e)}")


@app.get("/api/analytics")
async def get_analytics_data(
    days: int = 7,
    token: str = Depends(verify_service_token)
):
    """Get analytics data for the specified number of days."""
    try:
        # TODO: Implement analytics collection from database
        # This would involve aggregating data from various services
        
        sample_analytics = {
            "period": f"Last {days} days",
            "metrics": {
                "new_users": 12,
                "messages_sent": 156,
                "feeds_checked": 89,
                "errors": 3
            },
            "timeline": [
                {"date": "2024-01-01", "users": 10, "messages": 25},
                {"date": "2024-01-02", "users": 12, "messages": 31}
            ]
        }
        
        return sample_analytics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@app.post("/api/admin/restart-service")
async def restart_service(
    service_name: str,
    token: str = Depends(verify_service_token)
):
    """Restart a specific service (admin function)."""
    # TODO: Implement service restart functionality
    # This would typically involve container orchestration
    
    return {
        "message": f"Service restart not implemented for {service_name}",
        "note": "This would require container orchestration integration"
    }


@app.get("/mesop")
async def mesop_info():
    """Information about Mesop integration for future development."""
    return {
        "message": "Mesop integration placeholder",
        "description": "This endpoint is reserved for future Mesop-based UI integration",
        "documentation": "https://mesop.dev/",
        "suggestion": "Consider replacing the current HTML dashboard with Mesop components for a more interactive Python-based UI"
    }


if __name__ == "__main__":
    port = int(os.getenv("MINIAPP_SERVICE_PORT", 8009))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )