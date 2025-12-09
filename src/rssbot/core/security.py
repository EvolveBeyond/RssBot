"""
Service security and authentication
"""
from fastapi import HTTPException, Header
from typing import Optional
from .config import get_config


async def verify_service_token(x_service_token: Optional[str] = Header(None)) -> str:
    """
    Verify service-to-service authentication token.
    
    Args:
        x_service_token: Service token from X-Service-Token header
        
    Returns:
        Verified token string
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    config = get_config()
    expected_token = config.service_token
    
    if not x_service_token:
        raise HTTPException(
            status_code=401, 
            detail="Missing X-Service-Token header"
        )
    
    if x_service_token != expected_token:
        raise HTTPException(
            status_code=401, 
            detail="Invalid service token"
        )
    
    return x_service_token


def get_service_token() -> str:
    """
    Get the current service token for outgoing requests.
    
    Returns:
        Service token string
    """
    config = get_config()
    return config.service_token


def get_service_headers() -> dict:
    """
    Get standard headers for service-to-service communication.
    
    Returns:
        Dictionary with authentication headers
    """
    return {
        "X-Service-Token": get_service_token(),
        "Content-Type": "application/json"
    }