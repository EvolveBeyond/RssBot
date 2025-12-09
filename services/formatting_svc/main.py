"""
Formatting Service - Content transformation and styling.
Transforms raw RSS content into Telegram-formatted messages.
"""
import os
import re
import asyncio
import uvicorn
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import redis
import json
import hashlib


# Security middleware for inter-service authentication
async def verify_service_token(x_service_token: Optional[str] = Header(None)):
    """Verify service-to-service authentication token."""
    expected_token = os.getenv("SERVICE_TOKEN", "dev_service_token_change_in_production")
    if x_service_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid service token")
    return x_service_token


# Pydantic models
class FormatRequest(BaseModel):
    """Content formatting request."""
    feed_id: str
    raw_content: str
    channel_profile: Dict[str, Any]
    custom_style: Optional[str] = None


class FormatResponse(BaseModel):
    """Content formatting response."""
    formatted_text: str
    metadata: Dict[str, Any]
    tags: List[str] = []
    processing_time: float


class JobRequest(BaseModel):
    """Background job request."""
    requests: List[FormatRequest]
    callback_url: Optional[str] = None


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    status: str
    progress: int
    total: int
    results: List[FormatResponse] = []
    error: Optional[str] = None


# FastAPI application
app = FastAPI(
    title="RSS Bot Formatting Service",
    description="Content transformation and styling service",
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

# Redis connection for job queue (optional)
redis_client = None
try:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(redis_url, decode_responses=True)
    redis_client.ping()
    print("Redis connected for job queue")
except Exception as e:
    print(f"Redis not available: {e}")

# In-memory job storage (fallback if Redis not available)
job_storage: Dict[str, JobStatus] = {}


@app.on_event("startup")
async def startup():
    """Initialize formatting service."""
    print("Formatting service started successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "formatting_svc",
        "redis_available": redis_client is not None
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "service": "formatting_svc",
        "features": ["html_cleanup", "tag_extraction", "custom_styling", "background_jobs"]
    }


def clean_html(content: str) -> str:
    """Clean HTML content and convert to safe Telegram HTML."""
    if not content:
        return ""
    
    # Parse HTML
    soup = BeautifulSoup(content, 'html.parser')
    
    # Remove unwanted tags but keep text
    for tag in soup.find_all(['script', 'style', 'iframe', 'object', 'embed']):
        tag.decompose()
    
    # Get text content
    text = soup.get_text()
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Limit length for Telegram (4096 chars max)
    if len(text) > 3800:  # Leave room for formatting
        text = text[:3800] + "..."
    
    return text


def extract_tags(content: str, title: str = "") -> List[str]:
    """Extract tags from content for categorization."""
    tags = set()
    
    # Common RSS/news tags
    tech_keywords = ['ai', 'tech', 'software', 'programming', 'code', 'development', 'api']
    news_keywords = ['breaking', 'update', 'announcement', 'release', 'new']
    
    content_lower = (content + " " + title).lower()
    
    # Extract based on keywords
    for keyword in tech_keywords:
        if keyword in content_lower:
            tags.add(f"#{keyword}")
    
    for keyword in news_keywords:
        if keyword in content_lower:
            tags.add(f"#{keyword}")
    
    # Add generic tag if no specific tags found
    if not tags:
        tags.add("#rss")
    
    # Limit to 5 tags
    return list(tags)[:5]


def apply_formatting_style(content: str, title: str, link: str, tags: List[str], style: Optional[str] = None) -> str:
    """Apply formatting style to content."""
    
    # Default style template
    default_style = (
        "<b>{title}</b>\n\n"
        "{content}\n\n"
        "{tags}\n\n"
        "<a href='{link}'>Read more →</a>"
    )
    
    # Use custom style if provided
    template = style if style else default_style
    
    # Format tags
    tags_str = " ".join(tags) if tags else "#rss"
    
    # Apply template
    try:
        formatted = template.format(
            title=title,
            content=content,
            link=link,
            tags=tags_str
        )
        return formatted
    except KeyError as e:
        # Fallback if custom template has issues
        print(f"Template error: {e}, using default")
        return default_style.format(
            title=title,
            content=content,
            link=link,
            tags=tags_str
        )


def format_content_deterministic(request: FormatRequest) -> FormatResponse:
    """
    Format content with deterministic rules.
    This is the main formatting logic.
    """
    start_time = datetime.now()
    
    # Parse raw content (assume it's RSS-like JSON or HTML)
    try:
        if request.raw_content.startswith('{'):
            # JSON format
            data = json.loads(request.raw_content)
            title = data.get('title', 'Untitled')
            content = data.get('description', '')
            link = data.get('link', '#')
        else:
            # HTML or plain text format
            title = "RSS Update"  # TODO: Extract title from HTML
            content = request.raw_content
            link = "#"
    except:
        # Fallback parsing
        title = "RSS Update"
        content = request.raw_content
        link = "#"
    
    # Clean HTML content
    clean_content = clean_html(content)
    
    # Extract tags
    tags = extract_tags(clean_content, title)
    
    # Apply channel-specific formatting
    channel_style = request.channel_profile.get('formatting_style')
    custom_style = request.custom_style or channel_style
    
    # Format final message
    formatted_text = apply_formatting_style(
        content=clean_content,
        title=title,
        link=link,
        tags=tags,
        style=custom_style
    )
    
    # Calculate processing time
    processing_time = (datetime.now() - start_time).total_seconds()
    
    # Prepare metadata
    metadata = {
        "original_length": len(request.raw_content),
        "formatted_length": len(formatted_text),
        "channel_id": request.channel_profile.get("id"),
        "feed_id": request.feed_id,
        "processing_timestamp": datetime.now().isoformat()
    }
    
    return FormatResponse(
        formatted_text=formatted_text,
        metadata=metadata,
        tags=tags,
        processing_time=processing_time
    )


@app.post("/format", response_model=FormatResponse)
async def format_content(
    request: FormatRequest,
    token: str = Depends(verify_service_token)
):
    """Format a single piece of content."""
    try:
        result = format_content_deterministic(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Formatting failed: {str(e)}")


@app.post("/format/bulk")
async def format_bulk_content(
    requests: List[FormatRequest],
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_service_token)
):
    """Format multiple pieces of content (synchronous for small batches)."""
    if len(requests) > 10:
        raise HTTPException(status_code=400, detail="Use /jobs/submit for large batches")
    
    try:
        results = []
        for request in requests:
            result = format_content_deterministic(request)
            results.append(result)
        
        return {
            "results": results,
            "count": len(results),
            "total_processing_time": sum(r.processing_time for r in results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk formatting failed: {str(e)}")


@app.post("/jobs/submit")
async def submit_formatting_job(
    job_request: JobRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_service_token)
):
    """Submit a large formatting job for background processing."""
    job_id = hashlib.md5(f"{datetime.now()}{len(job_request.requests)}".encode()).hexdigest()
    
    # Initialize job status
    job_status = JobStatus(
        job_id=job_id,
        status="queued",
        progress=0,
        total=len(job_request.requests)
    )
    
    # Store job status
    if redis_client:
        redis_client.set(f"job:{job_id}", json.dumps(job_status.dict()), ex=3600)
    else:
        job_storage[job_id] = job_status
    
    # Start background processing
    background_tasks.add_task(process_formatting_job, job_id, job_request)
    
    return {"job_id": job_id, "status": "queued", "total_items": len(job_request.requests)}


async def process_formatting_job(job_id: str, job_request: JobRequest):
    """Process formatting job in background."""
    try:
        results = []
        total = len(job_request.requests)
        
        for i, request in enumerate(job_request.requests):
            try:
                result = format_content_deterministic(request)
                results.append(result)
                
                # Update progress
                progress = i + 1
                job_status = JobStatus(
                    job_id=job_id,
                    status="processing",
                    progress=progress,
                    total=total,
                    results=results
                )
                
                # Store updated status
                if redis_client:
                    redis_client.set(f"job:{job_id}", json.dumps(job_status.dict()), ex=3600)
                else:
                    job_storage[job_id] = job_status
                
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Error processing item {i}: {e}")
        
        # Mark job as completed
        final_status = JobStatus(
            job_id=job_id,
            status="completed",
            progress=total,
            total=total,
            results=results
        )
        
        if redis_client:
            redis_client.set(f"job:{job_id}", json.dumps(final_status.dict()), ex=3600)
        else:
            job_storage[job_id] = final_status
        
        print(f"Job {job_id} completed with {len(results)} results")
        
    except Exception as e:
        # Mark job as failed
        error_status = JobStatus(
            job_id=job_id,
            status="failed",
            progress=0,
            total=len(job_request.requests),
            error=str(e)
        )
        
        if redis_client:
            redis_client.set(f"job:{job_id}", json.dumps(error_status.dict()), ex=3600)
        else:
            job_storage[job_id] = error_status
        
        print(f"Job {job_id} failed: {e}")


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    token: str = Depends(verify_service_token)
):
    """Get the status of a formatting job."""
    try:
        # Try Redis first
        if redis_client:
            job_data = redis_client.get(f"job:{job_id}")
            if job_data:
                return JobStatus(**json.loads(job_data))
        
        # Fallback to in-memory storage
        if job_id in job_storage:
            return job_storage[job_id]
        
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving job status: {str(e)}")


@app.get("/jobs")
async def list_jobs(token: str = Depends(verify_service_token)):
    """List all formatting jobs."""
    if redis_client:
        # Get jobs from Redis
        keys = redis_client.keys("job:*")
        return {"jobs": [key.replace("job:", "") for key in keys], "count": len(keys)}
    else:
        # Get jobs from memory
        return {"jobs": list(job_storage.keys()), "count": len(job_storage)}


if __name__ == "__main__":
    port = int(os.getenv("FORMATTING_SERVICE_PORT", 8006))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )