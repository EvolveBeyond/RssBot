"""
Database Service Router - APIRouter implementation for local mounting.
Provides database introspection and management endpoints via FastAPI router.
"""
import os
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Dict, List, Optional, Any
from sqlmodel import Session, select

from .db.engine import db_config
from .db.models import ModelRegistry, ModelInfo, TableInfo, User, Channel, Feed


# Security middleware for inter-service authentication
async def verify_service_token(x_service_token: Optional[str] = Header(None)):
    """Verify service-to-service authentication token."""
    expected_token = os.getenv("SERVICE_TOKEN", "dev_service_token_change_in_production")
    if x_service_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid service token")
    return x_service_token


# Create the router
router = APIRouter(
    prefix="",  # No prefix - will be set by controller when mounting
    tags=["database"],
    responses={404: {"description": "Not found"}},
)


# Dependency to get database session
def get_session() -> Session:
    """Get database session dependency."""
    with Session(db_config.engine) as session:
        yield session


# Service initialization function
async def initialize_service():
    """Initialize database service."""
    print("Initializing database...")
    db_config.create_tables()
    print("Database service initialized successfully")


# Service registration function for controller mounting
def register_with_controller(controller_app):
    """Register this service with the controller app."""
    controller_app.include_router(router, prefix="/db", tags=["database"])
    print("Database service router registered with controller at /db")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        with Session(db_config.engine) as session:
            session.exec(select(1))
        return {"status": "healthy", "service": "db_svc"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        # More thorough check - verify tables exist
        table_info = db_config.get_table_info()
        return {
            "status": "ready", 
            "service": "db_svc",
            "tables": len(table_info)
        }
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}


@router.get("/tables", response_model=Dict[str, Any])
async def get_tables(token: str = Depends(verify_service_token)):
    """Get information about all database tables."""
    try:
        table_info = db_config.get_table_info()
        model_info = db_config.get_model_info()
        
        return {
            "tables": table_info,
            "models": list(model_info.keys()),
            "count": len(table_info)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving table info: {str(e)}")


@router.get("/model/{model_name}/schema", response_model=ModelInfo)
async def get_model_schema(
    model_name: str, 
    token: str = Depends(verify_service_token)
):
    """Get schema information for a specific model."""
    try:
        model_info = db_config.get_model_info()
        
        if model_name not in model_info:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
        
        info = model_info[model_name]
        return ModelInfo(
            name=model_name,
            fields=info['fields'],
            relationships=info['relationships'],
            table_name=info['table_name']
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving model schema: {str(e)}")


@router.get("/models")
async def list_models(token: str = Depends(verify_service_token)):
    """List all registered SQLModel classes."""
    try:
        models = ModelRegistry.get_models()
        return {
            "models": [
                {
                    "name": name,
                    "table_name": getattr(model_class, '__tablename__', None),
                    "module": model_class.__module__
                }
                for name, model_class in models.items()
            ],
            "count": len(models)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing models: {str(e)}")


@router.post("/query")
async def execute_query(
    query_data: dict,
    session: Session = Depends(get_session),
    token: str = Depends(verify_service_token)
):
    """
    Execute a simple query. This is a basic implementation.
    TODO: Implement more sophisticated query interface for production.
    """
    try:
        # This is a simplified query endpoint - extend as needed
        model_name = query_data.get("model")
        operation = query_data.get("operation", "select")
        
        if model_name not in ModelRegistry.get_models():
            raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")
        
        # Basic select operation example
        if operation == "select" and model_name == "User":
            users = session.exec(select(User)).all()
            return {"data": [user.dict() for user in users]}
        
        # TODO: Implement other operations (insert, update, delete)
        # TODO: Add proper query building and validation
        
        return {"message": "Query executed", "operation": operation, "model": model_name}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(e)}")


@router.get("/stats")
async def get_database_stats(
    session: Session = Depends(get_session),
    token: str = Depends(verify_service_token)
):
    """Get basic database statistics."""
    try:
        stats = {}
        
        # Count records in main tables
        models_to_count = [User, Channel, Feed]
        for model in models_to_count:
            try:
                count = len(session.exec(select(model)).all())
                stats[model.__name__.lower() + "_count"] = count
            except Exception:
                stats[model.__name__.lower() + "_count"] = 0
        
        return {
            "database_stats": stats,
            "timestamp": "2024-01-01T00:00:00Z"  # TODO: Use actual timestamp
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving stats: {str(e)}")