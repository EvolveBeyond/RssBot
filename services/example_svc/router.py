"""
Example Service Router - Template for creating router-compatible services.
This service demonstrates the new per-service hybrid microservices architecture
where each service can be configured independently for router or REST mode.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import os


# Security middleware for inter-service authentication
async def verify_service_token(x_service_token: str = Header(None)):
    """Verify service-to-service authentication token."""
    expected_token = os.getenv("SERVICE_TOKEN", "dev_service_token_change_in_production")
    if x_service_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid service token")
    return x_service_token


# Pydantic models
class ExampleData(BaseModel):
    """Example data model."""
    message: str
    mode: str
    timestamp: str


# Create the router (no prefix - controller will set it during mounting)
router = APIRouter(
    tags=["example"],
    responses={404: {"description": "Not found"}},
)


# Service state (in-memory for this example)
service_data: Dict[str, Any] = {
    "initialized": False,
    "requests_count": 0
}


# Service initialization function
async def initialize_service():
    """Initialize the example service."""
    service_data["initialized"] = True
    print("Example service initialized successfully")


# Service registration function (optional - for custom mounting logic)
def register_with_controller(controller_app):
    """
    Register this service with the controller app.
    This function is called automatically if LOCAL_ROUTER_MODE=true
    """
    controller_app.include_router(router, prefix="/example", tags=["example"])
    print("Example service router registered with controller at /example")


# Health check endpoint (always required)
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "example_svc",
        "initialized": service_data["initialized"]
    }


# Readiness check endpoint (recommended)
@router.get("/ready") 
async def readiness_check():
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "service": "example_svc", 
        "features": ["example_data", "router_mode_compatible"]
    }


# Protected endpoint requiring service token
@router.get("/data", response_model=ExampleData)
async def get_data(token: str = Depends(verify_service_token)):
    """Get example data from the service."""
    service_data["requests_count"] += 1
    
    return ExampleData(
        message=f"Hello from example service! Request #{service_data['requests_count']}",
        mode="router_mounted" if service_data.get("router_mode") else "standalone",
        timestamp="2024-01-01T00:00:00Z"  # TODO: Use actual timestamp
    )


# Example endpoint with service-to-service communication
@router.post("/process")
async def process_data(
    data: Dict[str, Any],
    token: str = Depends(verify_service_token)
):
    """Process data - example of business logic endpoint."""
    try:
        # TODO: Add actual processing logic
        # In router mode, you can call other services directly
        # In REST mode, you would make HTTP calls
        
        result = {
            "input": data,
            "processed": True,
            "result": f"Processed {len(str(data))} characters",
            "service": "example_svc"
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# Statistics endpoint
@router.get("/stats")
async def get_stats(token: str = Depends(verify_service_token)):
    """Get service statistics."""
    return {
        "service": "example_svc",
        "requests_handled": service_data["requests_count"],
        "initialized": service_data["initialized"],
        "mode": "router" if service_data.get("router_mode") else "standalone"
    }