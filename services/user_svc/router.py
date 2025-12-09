"""
User Service Router - APIRouter implementation for local mounting.
Handles user registration, preferences, and subscription management via FastAPI router.

This router uses the new hybrid microservices architecture with ServiceProxy
for intelligent routing to other services based on their connection methods.
"""
import os
import sys
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

# Add src to path for ServiceProxy imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from rssbot.discovery.proxy import ServiceProxy

# Initialize ServiceProxy instances for intelligent inter-service communication
payment_service = ServiceProxy("payment_svc")
bot_service = ServiceProxy("bot_svc")
db_service = ServiceProxy("db_svc")
import json


# Security middleware for inter-service authentication
async def verify_service_token(x_service_token: Optional[str] = Header(None)):
    """Verify service-to-service authentication token."""
    expected_token = os.getenv("SERVICE_TOKEN", "dev_service_token_change_in_production")
    if x_service_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid service token")
    return x_service_token


# Pydantic models (copied from main.py)
class UserCreate(BaseModel):
    """User creation request."""
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: str = "en"


class UserUpdate(BaseModel):
    """User update request."""
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    subscription_level: Optional[str] = None
    is_active: Optional[bool] = None


class UserPreferences(BaseModel):
    """User preferences model."""
    notifications_enabled: bool = True
    digest_frequency: str = "daily"  # daily, weekly, never
    timezone: str = "UTC"
    content_filters: List[str] = []
    custom_formatting: Dict[str, Any] = {}


class User(BaseModel):
    """User response model."""
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    language_code: str
    is_active: bool
    subscription_level: str
    preferences: UserPreferences
    created_at: datetime
    updated_at: Optional[datetime]


class ChannelSubscription(BaseModel):
    """Channel subscription model."""
    user_id: int
    channel_id: int
    channel_name: str
    is_active: bool
    subscription_type: str
    notify_new_posts: bool
    custom_filters: Dict[str, Any]
    subscribed_at: datetime


# Create the router
router = APIRouter(
    prefix="",  # No prefix - will be set by controller when mounting
    tags=["users"],
    responses={404: {"description": "Not found"}},
)


# In-memory user storage (use database via db_svc in production)
users_storage: Dict[int, User] = {}
user_id_counter = 1
subscriptions_storage: Dict[int, List[ChannelSubscription]] = {}


# Service initialization function
async def initialize_service():
    """Initialize user service."""
    print("User service initialized successfully")


# Service registration function for controller mounting
def register_with_controller(controller_app):
    """Register this service with the controller app."""
    controller_app.include_router(router, prefix="/users", tags=["users"])
    print("User service router registered with controller at /users")


async def call_db_service(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Helper function to call database service."""
    try:
        db_service_url = os.getenv("DB_SERVICE_URL", "http://localhost:8001")
        service_token = os.getenv("SERVICE_TOKEN", "dev_service_token_change_in_production")
        
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(
                    f"{db_service_url}{endpoint}",
                    headers={"X-Service-Token": service_token}
                )
            elif method == "POST":
                response = await client.post(
                    f"{db_service_url}{endpoint}",
                    json=data,
                    headers={"X-Service-Token": service_token}
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"DB service call failed: {response.status_code} - {response.text}")
                return {}
                
    except Exception as e:
        print(f"DB service call error: {e}")
        return {}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "user_svc",
        "total_users": len(users_storage)
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "service": "user_svc",
        "features": ["user_management", "preferences", "subscriptions", "db_integration"]
    }


@router.post("/", response_model=User)
async def create_user(
    user_data: UserCreate,
    token: str = Depends(verify_service_token)
):
    """Create a new user."""
    global user_id_counter
    
    # Check if user already exists by telegram_id
    existing_user = None
    for user in users_storage.values():
        if user.telegram_id == user_data.telegram_id:
            existing_user = user
            break
    
    if existing_user:
        return existing_user
    
    # Create new user
    user_id = user_id_counter
    user_id_counter += 1
    
    new_user = User(
        id=user_id,
        telegram_id=user_data.telegram_id,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        language_code=user_data.language_code,
        is_active=True,
        subscription_level="free",
        preferences=UserPreferences(),
        created_at=datetime.now(),
        updated_at=None
    )
    
    users_storage[user_id] = new_user
    
    # TODO: Store in database via db_svc
    await call_db_service("POST", "/query", {
        "model": "User",
        "operation": "insert",
        "data": new_user.dict()
    })
    
    return new_user


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    token: str = Depends(verify_service_token)
):
    """Get user by ID."""
    if user_id not in users_storage:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    return users_storage[user_id]


@router.get("/telegram/{telegram_id}", response_model=User)
async def get_user_by_telegram_id(
    telegram_id: int,
    token: str = Depends(verify_service_token)
):
    """Get user by Telegram ID."""
    for user in users_storage.values():
        if user.telegram_id == telegram_id:
            return user
    
    raise HTTPException(status_code=404, detail=f"User with Telegram ID {telegram_id} not found")


@router.patch("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    updates: UserUpdate,
    token: str = Depends(verify_service_token)
):
    """Update user information."""
    if user_id not in users_storage:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    user = users_storage[user_id]
    
    # Apply updates
    if updates.username is not None:
        user.username = updates.username
    if updates.first_name is not None:
        user.first_name = updates.first_name
    if updates.last_name is not None:
        user.last_name = updates.last_name
    if updates.language_code is not None:
        user.language_code = updates.language_code
    if updates.subscription_level is not None:
        user.subscription_level = updates.subscription_level
    if updates.is_active is not None:
        user.is_active = updates.is_active
    
    user.updated_at = datetime.now()
    
    # TODO: Update in database via db_svc
    await call_db_service("POST", "/query", {
        "model": "User",
        "operation": "update",
        "id": user_id,
        "data": updates.dict(exclude_unset=True)
    })
    
    return user


@router.get("/{user_id}/preferences", response_model=UserPreferences)
async def get_user_preferences(
    user_id: int,
    token: str = Depends(verify_service_token)
):
    """Get user preferences."""
    if user_id not in users_storage:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    return users_storage[user_id].preferences


@router.patch("/{user_id}/preferences", response_model=UserPreferences)
async def update_user_preferences(
    user_id: int,
    preferences: UserPreferences,
    token: str = Depends(verify_service_token)
):
    """Update user preferences."""
    if user_id not in users_storage:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    user = users_storage[user_id]
    user.preferences = preferences
    user.updated_at = datetime.now()
    
    # TODO: Update in database via db_svc
    
    return preferences


@router.get("/{user_id}/channels", response_model=List[ChannelSubscription])
async def get_user_channels(
    user_id: int,
    token: str = Depends(verify_service_token)
):
    """Get user's channel subscriptions."""
    if user_id not in users_storage:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    return subscriptions_storage.get(user_id, [])


@router.post("/{user_id}/channels/{channel_id}/subscribe")
async def subscribe_to_channel(
    user_id: int,
    channel_id: int,
    subscription_data: Dict[str, Any],
    token: str = Depends(verify_service_token)
):
    """Subscribe user to a channel."""
    if user_id not in users_storage:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    # Check if already subscribed
    user_subscriptions = subscriptions_storage.get(user_id, [])
    for sub in user_subscriptions:
        if sub.channel_id == channel_id:
            raise HTTPException(status_code=400, detail="Already subscribed to this channel")
    
    # Create subscription
    subscription = ChannelSubscription(
        user_id=user_id,
        channel_id=channel_id,
        channel_name=subscription_data.get("channel_name", f"Channel {channel_id}"),
        is_active=True,
        subscription_type=subscription_data.get("subscription_type", "free"),
        notify_new_posts=subscription_data.get("notify_new_posts", True),
        custom_filters=subscription_data.get("custom_filters", {}),
        subscribed_at=datetime.now()
    )
    
    if user_id not in subscriptions_storage:
        subscriptions_storage[user_id] = []
    
    subscriptions_storage[user_id].append(subscription)
    
    # TODO: Store in database via db_svc
    
    return {"message": "Successfully subscribed to channel", "subscription": subscription}


@router.delete("/{user_id}/channels/{channel_id}/unsubscribe")
async def unsubscribe_from_channel(
    user_id: int,
    channel_id: int,
    token: str = Depends(verify_service_token)
):
    """Unsubscribe user from a channel."""
    if user_id not in users_storage:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    user_subscriptions = subscriptions_storage.get(user_id, [])
    
    # Find and remove subscription
    for i, sub in enumerate(user_subscriptions):
        if sub.channel_id == channel_id:
            del user_subscriptions[i]
            # TODO: Update database via db_svc
            return {"message": "Successfully unsubscribed from channel"}
    
    raise HTTPException(status_code=404, detail="Subscription not found")


@router.get("/")
async def list_users(
    skip: int = 0,
    limit: int = 100,
    subscription_level: Optional[str] = None,
    token: str = Depends(verify_service_token)
):
    """List users with optional filtering."""
    users = list(users_storage.values())
    
    # Apply filters
    if subscription_level:
        users = [u for u in users if u.subscription_level == subscription_level]
    
    # Apply pagination
    total = len(users)
    users = users[skip:skip + limit]
    
    return {
        "users": users,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/stats")
async def get_user_stats(token: str = Depends(verify_service_token)):
    """Get user service statistics."""
    users = list(users_storage.values())
    
    stats = {
        "total_users": len(users),
        "active_users": len([u for u in users if u.is_active]),
        "by_subscription_level": {},
        "total_subscriptions": sum(len(subs) for subs in subscriptions_storage.values())
    }
    
    # Count by subscription level
    for user in users:
        level = user.subscription_level
        stats["by_subscription_level"][level] = stats["by_subscription_level"].get(level, 0) + 1
    
    return stats


@router.post("/{user_id}/upgrade")
async def upgrade_user_subscription(
    user_id: int,
    upgrade_data: Dict[str, Any],
    token: str = Depends(verify_service_token)
):
    """Upgrade user subscription level."""
    if user_id not in users_storage:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    user = users_storage[user_id]
    new_level = upgrade_data.get("subscription_level")
    
    if new_level not in ["free", "premium", "enterprise"]:
        raise HTTPException(status_code=400, detail="Invalid subscription level")
    
    user.subscription_level = new_level
    user.updated_at = datetime.now()
    
    # TODO: Update in database via db_svc
    
    return {
        "message": f"User subscription upgraded to {new_level}",
        "user_id": user_id,
        "new_level": new_level
    }