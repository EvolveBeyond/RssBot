"""
Database Service - SQLModel introspection and database management API.
Provides database connection, model introspection, and basic CRUD operations.

This service can run as:
1. Standalone service with FastAPI app (for remote deployment)
2. Router mounted in controller (for LOCAL_ROUTER_MODE)
"""
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the router implementation
from router import router, initialize_service


# FastAPI application for standalone mode
app = FastAPI(
    title="RSS Bot Database Service",
    description="Database introspection and management API for the RSS Bot platform",
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

# Include the router for standalone operation
app.include_router(router)


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await initialize_service()


# Note: All endpoints are now defined in router.py
# This allows the service to run standalone or be mounted as a router


if __name__ == "__main__":
    port = int(os.getenv("DB_SERVICE_PORT", 8001))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )