"""
Channel Manager Service - Channel and feed management.
Handles RSS feed monitoring, channel configuration, and content distribution.

This service uses the new hybrid microservices architecture with ServiceProxy
for intelligent routing to other services based on their connection methods.
"""
import os
import sys
import uvicorn
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import asyncio
import feedparser
from urllib.parse import urlparse

# Add src to path for ServiceProxy imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from rssbot.discovery.proxy import ServiceProxy

# Initialize ServiceProxy instances for intelligent inter-service communication
formatting_service = ServiceProxy("formatting_svc")
bot_service = ServiceProxy("bot_svc")
user_service = ServiceProxy("user_svc")


# Security middleware for inter-service authentication
async def verify_service_token(x_service_token: Optional[str] = Header(None)):
    """Verify service-to-service authentication token."""
    expected_token = os.getenv("SERVICE_TOKEN", "dev_service_token_change_in_production")
    if x_service_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid service token")
    return x_service_token


# Pydantic models
class ChannelCreate(BaseModel):
    """Channel creation request."""
    telegram_id: int
    title: str
    username: Optional[str] = None
    description: Optional[str] = None
    owner_id: int


class ChannelUpdate(BaseModel):
    """Channel update request."""
    title: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


class FeedCreate(BaseModel):
    """RSS feed creation request."""
    url: str
    title: Optional[str] = None
    channel_id: int
    check_interval: int = 600  # seconds
    custom_style: Optional[str] = None


class FeedUpdate(BaseModel):
    """RSS feed update request."""
    title: Optional[str] = None
    is_active: Optional[bool] = None
    check_interval: Optional[int] = None
    custom_style: Optional[str] = None


class Channel(BaseModel):
    """Channel response model."""
    id: int
    telegram_id: int
    title: str
    username: Optional[str]
    description: Optional[str]
    is_active: bool
    owner_id: int
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]


class Feed(BaseModel):
    """RSS feed response model."""
    id: int
    url: str
    title: Optional[str]
    description: Optional[str]
    channel_id: int
    is_active: bool
    check_interval: int
    last_checked: Optional[datetime]
    last_post_date: Optional[datetime]
    custom_style: Optional[str]
    created_at: datetime


class FeedItem(BaseModel):
    """RSS feed item model."""
    title: str
    description: Optional[str]
    link: str
    published_date: Optional[datetime]
    guid: Optional[str]
    tags: List[str] = []


# FastAPI application
app = FastAPI(
    title="RSS Bot Channel Manager Service",
    description="Channel and feed management service",
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

# In-memory storage (use database via db_svc in production)
channels_storage: Dict[int, Channel] = {}
feeds_storage: Dict[int, Feed] = {}
channel_id_counter = 1
feed_id_counter = 1

# Feed monitoring task
feed_check_task = None


@app.on_event("startup")
async def startup():
    """Initialize channel manager service."""
    global feed_check_task
    
    # Start feed monitoring task
    feed_check_task = asyncio.create_task(feed_monitoring_loop())
    
    print("Channel manager service started successfully")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on service shutdown."""
    global feed_check_task
    
    if feed_check_task:
        feed_check_task.cancel()
        try:
            await feed_check_task
        except asyncio.CancelledError:
            pass


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "channel_mgr_svc",
        "total_channels": len(channels_storage),
        "total_feeds": len(feeds_storage),
        "monitoring_active": feed_check_task is not None and not feed_check_task.done()
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "service": "channel_mgr_svc",
        "features": ["channel_management", "feed_monitoring", "rss_parsing", "content_distribution"]
    }


async def call_service(service_name: str, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
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
        if service_name == "formatting_svc":
            service_proxy = formatting_service
        elif service_name == "bot_svc":
            service_proxy = bot_service
        elif service_name == "user_svc":
            service_proxy = user_service
        else:
            print(f"Unknown service: {service_name}")
            return {}
        
        # Extract method name from endpoint (e.g., "/format" -> "format", "/send" -> "send")
        method_name = endpoint.strip('/').split('/')[-1] or "health_check"
        
        # Call service using ServiceProxy (automatically routes based on connection method)
        if method == "GET":
            if method_name == "health":
                result = await service_proxy.health_check()
            else:
                # For other GET methods, try to call the method directly
                result = await service_proxy._execute_service_call(method_name)
        elif method == "POST":
            # For POST methods, pass data as kwargs
            result = await service_proxy._execute_service_call(method_name, **(data if data else {}))
        else:
            print(f"Unsupported method: {method}")
            return {}
        
        return result if isinstance(result, dict) else {"result": result}
        
    except Exception as e:
        print(f"Error calling {service_name} via ServiceProxy: {str(e)}")
        return {}


@app.post("/channels", response_model=Channel)
async def create_channel(
    channel_data: ChannelCreate,
    token: str = Depends(verify_service_token)
):
    """Create a new channel."""
    global channel_id_counter
    
    # Check if channel already exists
    for channel in channels_storage.values():
        if channel.telegram_id == channel_data.telegram_id:
            raise HTTPException(status_code=400, detail="Channel already exists")
    
    channel_id = channel_id_counter
    channel_id_counter += 1
    
    new_channel = Channel(
        id=channel_id,
        telegram_id=channel_data.telegram_id,
        title=channel_data.title,
        username=channel_data.username,
        description=channel_data.description,
        is_active=True,
        owner_id=channel_data.owner_id,
        settings={},
        created_at=datetime.now(),
        updated_at=None
    )
    
    channels_storage[channel_id] = new_channel
    
    return new_channel


@app.get("/channels/{channel_id}", response_model=Channel)
async def get_channel(
    channel_id: int,
    token: str = Depends(verify_service_token)
):
    """Get channel by ID."""
    if channel_id not in channels_storage:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found")
    
    return channels_storage[channel_id]


@app.patch("/channels/{channel_id}", response_model=Channel)
async def update_channel(
    channel_id: int,
    updates: ChannelUpdate,
    token: str = Depends(verify_service_token)
):
    """Update channel information."""
    if channel_id not in channels_storage:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found")
    
    channel = channels_storage[channel_id]
    
    if updates.title is not None:
        channel.title = updates.title
    if updates.description is not None:
        channel.description = updates.description
    if updates.is_active is not None:
        channel.is_active = updates.is_active
    if updates.settings is not None:
        channel.settings.update(updates.settings)
    
    channel.updated_at = datetime.now()
    
    return channel


@app.get("/channels/{channel_id}/feeds", response_model=List[Feed])
async def get_channel_feeds(
    channel_id: int,
    token: str = Depends(verify_service_token)
):
    """Get all feeds for a channel."""
    if channel_id not in channels_storage:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found")
    
    channel_feeds = [feed for feed in feeds_storage.values() if feed.channel_id == channel_id]
    return channel_feeds


@app.post("/feeds", response_model=Feed)
async def create_feed(
    feed_data: FeedCreate,
    token: str = Depends(verify_service_token)
):
    """Add RSS feed to a channel."""
    global feed_id_counter
    
    # Validate channel exists
    if feed_data.channel_id not in channels_storage:
        raise HTTPException(status_code=404, detail=f"Channel {feed_data.channel_id} not found")
    
    # Validate RSS URL
    try:
        parsed_url = urlparse(feed_data.url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL format")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid RSS URL")
    
    # Test RSS feed
    try:
        feed_info = await test_rss_feed(feed_data.url)
        if not feed_info["valid"]:
            raise HTTPException(status_code=400, detail="Invalid RSS feed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to validate RSS feed: {str(e)}")
    
    feed_id = feed_id_counter
    feed_id_counter += 1
    
    new_feed = Feed(
        id=feed_id,
        url=feed_data.url,
        title=feed_data.title or feed_info.get("title", "Untitled Feed"),
        description=feed_info.get("description"),
        channel_id=feed_data.channel_id,
        is_active=True,
        check_interval=feed_data.check_interval,
        last_checked=None,
        last_post_date=None,
        custom_style=feed_data.custom_style,
        created_at=datetime.now()
    )
    
    feeds_storage[feed_id] = new_feed
    
    return new_feed


@app.patch("/feeds/{feed_id}", response_model=Feed)
async def update_feed(
    feed_id: int,
    updates: FeedUpdate,
    token: str = Depends(verify_service_token)
):
    """Update RSS feed configuration."""
    if feed_id not in feeds_storage:
        raise HTTPException(status_code=404, detail=f"Feed {feed_id} not found")
    
    feed = feeds_storage[feed_id]
    
    if updates.title is not None:
        feed.title = updates.title
    if updates.is_active is not None:
        feed.is_active = updates.is_active
    if updates.check_interval is not None:
        feed.check_interval = updates.check_interval
    if updates.custom_style is not None:
        feed.custom_style = updates.custom_style
    
    return feed


@app.delete("/feeds/{feed_id}")
async def delete_feed(
    feed_id: int,
    token: str = Depends(verify_service_token)
):
    """Delete RSS feed."""
    if feed_id not in feeds_storage:
        raise HTTPException(status_code=404, detail=f"Feed {feed_id} not found")
    
    del feeds_storage[feed_id]
    return {"message": "Feed deleted successfully"}


@app.get("/feeds/{feed_id}/check")
async def check_feed_now(
    feed_id: int,
    token: str = Depends(verify_service_token)
):
    """Manually trigger feed check."""
    if feed_id not in feeds_storage:
        raise HTTPException(status_code=404, detail=f"Feed {feed_id} not found")
    
    feed = feeds_storage[feed_id]
    
    try:
        new_items = await check_feed_for_updates(feed)
        return {
            "message": "Feed checked successfully",
            "new_items": len(new_items),
            "items": new_items[:5]  # Return first 5 items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feed check failed: {str(e)}")


async def test_rss_feed(url: str) -> Dict[str, Any]:
    """
    Test RSS feed validity and get basic info.
    
    This function accesses external RSS URLs, so it uses httpx directly
    rather than ServiceProxy (which is for inter-service communication).
    """
    try:
        import httpx  # Import here since we only need it for external RSS feeds
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
        
        # Parse RSS feed
        feed = feedparser.parse(response.content)
        
        if feed.bozo and not feed.entries:
            return {"valid": False, "error": "Invalid RSS format"}
        
        return {
            "valid": True,
            "title": getattr(feed.feed, 'title', 'Untitled'),
            "description": getattr(feed.feed, 'description', ''),
            "entries_count": len(feed.entries)
        }
        
    except Exception as e:
        return {"valid": False, "error": str(e)}


async def check_feed_for_updates(feed: Feed) -> List[FeedItem]:
    """
    Check RSS feed for new items.
    
    This function fetches external RSS URLs, so it uses httpx directly
    rather than ServiceProxy (which is for inter-service communication).
    """
    try:
        import httpx  # Import here since we only need it for external RSS feeds
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(feed.url)
            response.raise_for_status()
        
        # Parse RSS feed
        parsed_feed = feedparser.parse(response.content)
        
        new_items = []
        
        for entry in parsed_feed.entries[:10]:  # Limit to latest 10 items
            # Parse published date
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_date = datetime(*entry.published_parsed[:6])
            
            # Skip if we've seen this item before (simple check by date)
            if (feed.last_post_date and published_date and 
                published_date <= feed.last_post_date):
                continue
            
            item = FeedItem(
                title=getattr(entry, 'title', 'No Title'),
                description=getattr(entry, 'description', ''),
                link=getattr(entry, 'link', ''),
                published_date=published_date,
                guid=getattr(entry, 'id', None) or getattr(entry, 'guid', None)
            )
            
            new_items.append(item)
        
        # Update feed's last checked time
        feed.last_checked = datetime.now()
        
        # Update last post date if we have new items
        if new_items:
            latest_date = max(
                (item.published_date for item in new_items if item.published_date),
                default=datetime.now()
            )
            feed.last_post_date = latest_date
        
        return new_items
        
    except Exception as e:
        print(f"Error checking feed {feed.id}: {e}")
        return []


async def process_and_send_feed_item(feed: Feed, item: FeedItem):
    """Process and send a feed item to the channel."""
    try:
        channel = channels_storage.get(feed.channel_id)
        if not channel or not channel.is_active:
            return
        
        # Format content via formatting service
        format_response = await call_service(
            "formatting_svc", 
            "/format",
            method="POST",
            data={
                "feed_id": str(feed.id),
                "raw_content": item.description or item.title,
                "channel_profile": {
                    "id": channel.telegram_id,
                    "formatting_style": feed.custom_style
                }
            }
        )
        
        if format_response and "formatted_text" in format_response:
            formatted_text = format_response["formatted_text"]
        else:
            # Fallback formatting
            formatted_text = f"<b>{item.title}</b>\n\n{item.description or ''}\n\n<a href='{item.link}'>Read more</a>"
        
        # Send via bot service
        send_response = await call_service(
            "bot_svc",
            "/send",
            method="POST",
            data={
                "to": channel.telegram_id,
                "type": "text",
                "payload": {
                    "text": formatted_text,
                    "parse_mode": "HTML"
                }
            }
        )
        
        if send_response and send_response.get("success"):
            print(f"Sent item '{item.title}' to channel {channel.telegram_id}")
        
    except Exception as e:
        print(f"Error processing feed item: {e}")


async def feed_monitoring_loop():
    """Background task to monitor RSS feeds."""
    while True:
        try:
            print("Checking RSS feeds for updates...")
            
            for feed in feeds_storage.values():
                if not feed.is_active:
                    continue
                
                # Check if it's time to check this feed
                if (feed.last_checked is None or 
                    datetime.now() - feed.last_checked >= timedelta(seconds=feed.check_interval)):
                    
                    try:
                        new_items = await check_feed_for_updates(feed)
                        
                        # Process each new item
                        for item in new_items:
                            await process_and_send_feed_item(feed, item)
                            await asyncio.sleep(1)  # Rate limiting
                        
                        if new_items:
                            print(f"Processed {len(new_items)} new items from feed {feed.id}")
                    
                    except Exception as e:
                        print(f"Error processing feed {feed.id}: {e}")
            
            # Wait before next check cycle
            await asyncio.sleep(60)  # Check every minute
            
        except asyncio.CancelledError:
            print("Feed monitoring task cancelled")
            break
        except Exception as e:
            print(f"Feed monitoring loop error: {e}")
            await asyncio.sleep(60)


@app.get("/stats")
async def get_service_stats(token: str = Depends(verify_service_token)):
    """Get channel manager service statistics."""
    active_channels = len([c for c in channels_storage.values() if c.is_active])
    active_feeds = len([f for f in feeds_storage.values() if f.is_active])
    
    return {
        "total_channels": len(channels_storage),
        "active_channels": active_channels,
        "total_feeds": len(feeds_storage),
        "active_feeds": active_feeds,
        "monitoring_active": feed_check_task is not None and not feed_check_task.done()
    }


if __name__ == "__main__":
    port = int(os.getenv("CHANNEL_MGR_SERVICE_PORT", 8007))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )